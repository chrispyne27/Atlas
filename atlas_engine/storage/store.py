"""Atomic, scoped compilation inventory; compiler commands are data, never run."""
import hashlib
import json
import re
import shlex
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

VERSION = 'manifest-1'
MAX_MANIFEST_BYTES = 32 * 1024 * 1024
SCHEMA = Path(__file__).with_name('schema-v1.sql')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def connect(path):
    """Create an empty v1 store or open v1. Unknown schemas are never migrated."""
    db = sqlite3.connect(str(path), timeout=10, isolation_level=None)
    try:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('BEGIN IMMEDIATE')
        version = db.execute('PRAGMA user_version').fetchone()[0]
        tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if not tables and version == 0:
            # executescript implicitly commits: execute complete statements instead.
            statement = ''
            for line in SCHEMA.read_text().splitlines(keepends=True):
                statement += line
                if sqlite3.complete_statement(statement):
                    db.execute(statement)
                    statement = ''
            if statement.strip():
                raise ValueError('Incomplete schema statement')
        elif version != 1:
            raise ValueError(f'Unsupported database schema version: {version}')
        required = {'repository','snapshot','artifact','build_target','evidence','compilation','compilation_input'}
        actual = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required <= actual:
            raise ValueError('Incomplete Atlas database schema')
        db.execute('COMMIT')
        return db
    except BaseException:
        if db.in_transaction:
            db.execute('ROLLBACK')
        db.close()
        raise


def import_manifest(db, *, repository, build_root, compilation_database,
                    repository_id, source_uri, revision, configuration_key,
                    toolchain_fingerprint, targets):
    """Import exact CMake target names into an unpublished staging snapshot.

    Only POSIX command quoting is accepted. Every selected source must exist.
    Scope must be explicit, preventing accidental import of unbuilt generated TUs.
    The caller supplies revision/configuration/toolchain identity; these are
    recorded assertions, not auto-discovered verification of the checkout.
    """
    if db.in_transaction:
        raise ValueError('Import requires a connection without an active transaction')
    if db.execute('PRAGMA foreign_keys').fetchone()[0] != 1:
        raise ValueError('Foreign keys must be enabled')
    for name, value in [('repository_id',repository_id),('source_uri',source_uri),
                        ('revision',revision),('configuration_key',configuration_key),
                        ('toolchain_fingerprint',toolchain_fingerprint)]:
        if not isinstance(value,str) or not value.strip():
            raise ValueError(f'{name} must be a nonempty string')
    requested = set(targets)
    if not requested or any(not isinstance(t,str) or not t for t in requested):
        raise ValueError('Select at least one exact CMake target name')
    root, build = Path(repository).resolve(strict=True), Path(build_root).resolve(strict=True)
    if root == build or not root.is_dir() or not build.is_dir():
        raise ValueError('Repository and build roots must be distinct directories')
    roots = sorted([('repo',root),('build',build)],key=lambda item:len(item[1].parts),reverse=True)

    def location(path):
        resolved = path.resolve(strict=True)
        for label, base in roots:
            if resolved.is_relative_to(base):
                return label + '/' + resolved.relative_to(base).as_posix(), resolved, label
        raise ValueError(f'Path outside declared repository/build roots: {path}')

    manifest_path = Path(compilation_database).resolve(strict=True)
    manifest_name, _, _ = location(manifest_path)
    with manifest_path.open('rb') as stream:
        raw = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError('Compilation database exceeds the 32 MiB importer limit')
    entries = json.loads(raw)
    if not isinstance(entries,list) or not entries:
        raise ValueError('Compilation database must be a nonempty array')
    manifest_digest = digest(raw)
    snapshot_id = uuid.uuid4().hex
    seen_targets, artifacts = set(), {}
    imported = duplicates = 0
    db.execute('BEGIN IMMEDIATE')
    try:
        existing = db.execute('SELECT source_uri FROM repository WHERE id=?',(repository_id,)).fetchone()
        if existing and existing[0] != source_uri:
            raise ValueError('Repository identity already has a different source URI')
        db.execute('INSERT OR IGNORE INTO repository VALUES (?,?)',(repository_id,source_uri))
        db.execute('INSERT INTO snapshot VALUES (?,?,?,?,?,?,?,?,?,?)',
                   (snapshot_id,repository_id,revision,configuration_key,'pending',toolchain_fingerprint,VERSION,1,'staging',datetime.now(timezone.utc).isoformat()))

        def artifact(path):
            key, absolute, label = location(path)
            if not absolute.is_file():
                raise ValueError(f'Expected a file: {absolute}')
            if key not in artifacts:
                hashed = file_hash(absolute)
                artifacts[key] = (absolute,hashed)
                db.execute('INSERT INTO artifact VALUES (?,?,?,?)',
                           (snapshot_id,key,hashed,'generated' if label == 'build' else 'authored'))
            return key

        artifact(manifest_path)
        if artifacts[manifest_name][1] != manifest_digest:
            raise ValueError('Compilation database changed during import')
        for ordinal, entry in enumerate(entries):
            if not isinstance(entry,dict):
                raise ValueError(f'Entry {ordinal} is not an object')
            # CMake object paths establish object-target identity, not application membership.
            output = entry.get('output','')
            if not isinstance(output,str):
                raise ValueError(f'Entry {ordinal} has a non-string output')
            match = re.search(r'(?:^|/)CMakeFiles/([^/]+)\.dir/',output)
            if not match or match[1] not in requested:
                continue
            target_name = match[1]
            directory = Path(entry['directory'])
            if not directory.is_absolute():
                raise ValueError('Compilation working directory must be absolute')
            cwd_name, cwd, _ = location(directory)
            if not cwd.is_dir():
                raise ValueError('Compilation working directory must be a directory')
            # Preserve directory scope in case CMake target names are reused.
            target_path = (cwd / output[:match.end()-1]).resolve()
            target_key = target_path.as_posix()
            for label, base in roots:
                if target_path.is_relative_to(base):
                    target_key = label + '/' + target_path.relative_to(base).as_posix()
                    break
            else:
                raise ValueError('Object target outside declared roots')
            if 'arguments' in entry:
                argv = entry['arguments']
            else:
                command = entry.get('command')
                if not isinstance(command,str):
                    raise ValueError('Entry requires arguments or a POSIX command string')
                argv = shlex.split(command,posix=True)
            if not isinstance(argv,list) or not argv or any(not isinstance(a,str) or '\0' in a for a in argv):
                raise ValueError('Compilation arguments must be a nonempty string array')
            # Response file contents cannot yet participate in the fingerprint.
            if any(a.startswith('@') for a in argv):
                raise ValueError('Response files are not supported by this importer')
            source_name = artifact(cwd / entry['file'])
            command_hash = digest(canonical([cwd_name,argv]).encode())
            compilation_id = digest(canonical([target_key,source_name,command_hash]).encode())
            db.execute('INSERT OR IGNORE INTO build_target VALUES (?,?,?,?)',
                       (snapshot_id,target_key,target_name,'other'))
            cursor = db.execute('INSERT OR IGNORE INTO compilation VALUES (?,?,?,?,?,?,?)',
                                (snapshot_id,compilation_id,target_key,source_name,command_hash,canonical(argv),'pending'))
            seen_targets.add(target_name)
            duplicates += 1 if cursor.rowcount == 0 else 0
            imported += cursor.rowcount
            db.execute('INSERT OR IGNORE INTO compilation_input VALUES (?,?,?)',
                       (snapshot_id,compilation_id,source_name))
            db.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?,?)',
                       (snapshot_id,f'command:{ordinal}','build',manifest_name,None,VERSION,
                        canonical({'entry':ordinal,'compilation_id':compilation_id,'directory':cwd_name,
                                   'output':output,'original_entry':entry})))
        missing = requested - seen_targets
        if missing:
            raise ValueError('Selected CMake targets not found: ' + ', '.join(sorted(missing)))
        for absolute, hashed in artifacts.values():
            if file_hash(absolute) != hashed:
                raise ValueError(f'Input changed during import: {absolute}')
        manifest_hash = digest(canonical({'scope':sorted(requested),'database':manifest_digest,
                            'artifacts':sorted((k,v[1]) for k,v in artifacts.items())}).encode())
        db.execute('UPDATE snapshot SET input_manifest_hash=? WHERE id=?',(manifest_hash,snapshot_id))
        db.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?,?)',
                   (snapshot_id,'import-scope','build',manifest_name,None,VERSION,
                    canonical({'targets':sorted(requested),'entries_total':len(entries),'imported':imported,
                               'duplicate_entries':duplicates,'roots':{'repo':str(root),'build':str(build)},
                               'scope':'compilation inventory only; headers and graph not yet indexed'})))
        db.execute('COMMIT')
        return {'snapshot_id':snapshot_id,'state':'staging','compilations':imported,
                'duplicate_entries':duplicates,'artifacts':len(artifacts),'targets':sorted(seen_targets),
                'input_manifest_hash':manifest_hash}
    except BaseException:
        db.execute('ROLLBACK')
        raise
