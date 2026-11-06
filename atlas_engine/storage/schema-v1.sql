-- Atlas disk-store contract v1. Scoped inventory importer exists; graph/query service pending.
-- Every connection MUST enable foreign_keys before starting a transaction.
PRAGMA foreign_keys = ON;
PRAGMA user_version = 1;

CREATE TABLE repository (
    id TEXT PRIMARY KEY NOT NULL,
    source_uri TEXT NOT NULL
);
CREATE TABLE snapshot (
    id TEXT PRIMARY KEY NOT NULL,
    repository_id TEXT NOT NULL REFERENCES repository(id),
    revision TEXT NOT NULL,
    configuration_key TEXT NOT NULL,
    input_manifest_hash TEXT NOT NULL,
    toolchain_fingerprint TEXT NOT NULL,
    indexer_version TEXT NOT NULL,
    schema_version INTEGER NOT NULL CHECK (schema_version = 1),
    state TEXT NOT NULL CHECK (state IN ('staging','ready','failed')),
    created_at TEXT NOT NULL
);
CREATE INDEX snapshot_lookup ON snapshot(repository_id, configuration_key, state);

CREATE TABLE artifact (
    snapshot_id TEXT NOT NULL REFERENCES snapshot(id),
    path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    origin TEXT NOT NULL CHECK (origin IN ('authored','generated','external')),
    PRIMARY KEY (snapshot_id, path)
);
CREATE TABLE build_target (
    snapshot_id TEXT NOT NULL REFERENCES snapshot(id),
    id TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('application','library','test','other')),
    PRIMARY KEY (snapshot_id, id)
);
CREATE TABLE evidence (
    snapshot_id TEXT NOT NULL REFERENCES snapshot(id),
    id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('compiler','build','authored','inferred','execution','review')),
    artifact_path TEXT,
    line INTEGER CHECK (line > 0),
    producer TEXT NOT NULL,
    details_json TEXT NOT NULL CHECK (json_valid(details_json)),
    PRIMARY KEY (snapshot_id, id),
    FOREIGN KEY (snapshot_id, artifact_path) REFERENCES artifact(snapshot_id, path),
    CHECK (line IS NULL OR artifact_path IS NOT NULL)
);
CREATE TABLE target_dependency (
    snapshot_id TEXT NOT NULL,
    from_target TEXT NOT NULL,
    to_target TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, from_target, to_target, evidence_id),
    FOREIGN KEY (snapshot_id, from_target) REFERENCES build_target(snapshot_id, id),
    FOREIGN KEY (snapshot_id, to_target) REFERENCES build_target(snapshot_id, id),
    FOREIGN KEY (snapshot_id, evidence_id) REFERENCES evidence(snapshot_id, id)
);
CREATE TABLE compilation (
    snapshot_id TEXT NOT NULL,
    id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    source_path TEXT NOT NULL,
    command_hash TEXT NOT NULL,
    arguments_json TEXT NOT NULL CHECK (json_valid(arguments_json) AND json_type(arguments_json) = 'array'),
    state TEXT NOT NULL CHECK (state IN ('pending','parsed','failed','excluded')),
    PRIMARY KEY (snapshot_id, id),
    UNIQUE (snapshot_id, target_id, source_path, command_hash),
    FOREIGN KEY (snapshot_id, target_id) REFERENCES build_target(snapshot_id, id),
    FOREIGN KEY (snapshot_id, source_path) REFERENCES artifact(snapshot_id, path)
);
CREATE TABLE compilation_input (
    snapshot_id TEXT NOT NULL,
    compilation_id TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, compilation_id, artifact_path),
    FOREIGN KEY (snapshot_id, compilation_id) REFERENCES compilation(snapshot_id, id),
    FOREIGN KEY (snapshot_id, artifact_path) REFERENCES artifact(snapshot_id, path)
);
CREATE INDEX input_dependents ON compilation_input(snapshot_id, artifact_path, compilation_id);

-- Logical identity only. Definition bodies/spans are separate occurrences.
CREATE TABLE entity (
    snapshot_id TEXT NOT NULL REFERENCES snapshot(id),
    id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('symbol','requirement','test','component','type')),
    scope TEXT NOT NULL,
    external_key TEXT NOT NULL,
    name TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, id),
    UNIQUE (snapshot_id, kind, scope, external_key)
);
CREATE INDEX entity_name ON entity(snapshot_id, name, id);
CREATE TABLE occurrence (
    snapshot_id TEXT NOT NULL,
    id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    compilation_id TEXT,
    artifact_path TEXT NOT NULL,
    start_line INTEGER NOT NULL CHECK (start_line > 0),
    end_line INTEGER NOT NULL CHECK (end_line >= start_line),
    role TEXT NOT NULL CHECK (role IN ('definition','declaration','annotation','description')),
    evidence_id TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, id),
    FOREIGN KEY (snapshot_id, entity_id) REFERENCES entity(snapshot_id, id),
    FOREIGN KEY (snapshot_id, compilation_id) REFERENCES compilation(snapshot_id, id),
    FOREIGN KEY (snapshot_id, artifact_path) REFERENCES artifact(snapshot_id, path),
    FOREIGN KEY (snapshot_id, evidence_id) REFERENCES evidence(snapshot_id, id)
);
CREATE INDEX occurrence_entity ON occurrence(snapshot_id, entity_id, compilation_id);
CREATE TABLE relation (
    snapshot_id TEXT NOT NULL,
    id TEXT NOT NULL,
    from_entity TEXT NOT NULL,
    to_entity TEXT,
    target_spelling TEXT,
    kind TEXT NOT NULL,
    resolution TEXT NOT NULL CHECK (resolution IN ('resolved','unresolved','candidate')),
    compilation_id TEXT,
    evidence_id TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, id),
    FOREIGN KEY (snapshot_id, from_entity) REFERENCES entity(snapshot_id, id),
    FOREIGN KEY (snapshot_id, to_entity) REFERENCES entity(snapshot_id, id),
    FOREIGN KEY (snapshot_id, compilation_id) REFERENCES compilation(snapshot_id, id),
    FOREIGN KEY (snapshot_id, evidence_id) REFERENCES evidence(snapshot_id, id),
    CHECK ((resolution = 'resolved' AND to_entity IS NOT NULL)
        OR (resolution = 'unresolved' AND to_entity IS NULL AND target_spelling IS NOT NULL)
        OR (resolution = 'candidate' AND (to_entity IS NOT NULL OR target_spelling IS NOT NULL)))
);
CREATE INDEX relation_out ON relation(snapshot_id, from_entity, kind, id);
CREATE INDEX relation_in ON relation(snapshot_id, to_entity, kind, id);
CREATE TABLE relation_review (
    snapshot_id TEXT NOT NULL,
    id TEXT NOT NULL,
    relation_id TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('approved','rejected','needs_review')),
    reviewer TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, id),
    FOREIGN KEY (snapshot_id, relation_id) REFERENCES relation(snapshot_id, id),
    FOREIGN KEY (snapshot_id, evidence_id) REFERENCES evidence(snapshot_id, id)
);
CREATE TABLE test_run (
    snapshot_id TEXT NOT NULL,
    id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    executable_hash TEXT NOT NULL,
    environment_json TEXT NOT NULL CHECK (json_valid(environment_json)),
    status TEXT NOT NULL CHECK (status IN ('passed','failed','error','not_run')),
    evidence_id TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, id),
    FOREIGN KEY (snapshot_id, target_id) REFERENCES build_target(snapshot_id, id),
    FOREIGN KEY (snapshot_id, evidence_id) REFERENCES evidence(snapshot_id, id)
);
CREATE TABLE test_result (
    snapshot_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    test_entity TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('passed','failed','skipped','error','unknown')),
    evidence_id TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, run_id, test_entity),
    FOREIGN KEY (snapshot_id, run_id) REFERENCES test_run(snapshot_id, id),
    FOREIGN KEY (snapshot_id, test_entity) REFERENCES entity(snapshot_id, id),
    FOREIGN KEY (snapshot_id, evidence_id) REFERENCES evidence(snapshot_id, id)
);
CREATE TABLE metadata (
    snapshot_id TEXT NOT NULL,
    id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    field TEXT NOT NULL,
    value_json TEXT NOT NULL CHECK (json_valid(value_json)),
    evidence_id TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, id),
    FOREIGN KEY (snapshot_id, entity_id) REFERENCES entity(snapshot_id, id),
    FOREIGN KEY (snapshot_id, evidence_id) REFERENCES evidence(snapshot_id, id)
);
CREATE INDEX metadata_entity ON metadata(snapshot_id, entity_id, field);
