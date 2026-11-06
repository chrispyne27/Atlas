"""Explain readiness blockers for one target; never publish or approve a snapshot."""
import argparse
import sqlite3
import time
from .freshness import audit
from .inspect import Inspector
from .membership import COMPONENTS
from .store import canonical
from .external_roots import mapping_argument


def assess(database, *, snapshot, target, components, roots, external_roots=()):
    if not isinstance(target, str) or not 0 < len(target) <= 2048:
        raise ValueError('An exact build target is required')
    selected = sorted(set(components))
    if not selected or set(selected) - COMPONENTS:
        raise ValueError('Select explicit supported engineering components')
    reader = Inspector(database)
    try:
        version = reader._version()
        deadline = time.monotonic() + 0.5
        ticks = 0
        def stop():
            nonlocal ticks
            ticks += 1
            return ticks >= 2000 or time.monotonic() > deadline
        reader.db.set_progress_handler(stop, 1000)
        reader.db.execute('BEGIN')
        if not reader.db.execute('SELECT 1 FROM build_target WHERE snapshot_id=? AND id=?', (snapshot, target)).fetchone():
            raise ValueError('Unknown snapshot or target')
        states = dict(reader.db.execute('SELECT state,count(*) FROM compilation WHERE snapshot_id=? AND target_id=? GROUP BY state', (snapshot, target)))
        origins = dict(reader.db.execute('SELECT origin,count(*) FROM artifact WHERE snapshot_id=? GROUP BY origin', (snapshot,)))
        imported = {component: bool(reader.db.execute('SELECT 1 FROM evidence WHERE snapshot_id=? AND id=?',
                        (snapshot, 'engineering:' + component)).fetchone()) for component in selected}
        relationships = dict(reader.db.execute('SELECT resolution,count(*) FROM relation WHERE snapshot_id=? AND (compilation_id IS NULL OR compilation_id IN (SELECT id FROM compilation WHERE snapshot_id=? AND target_id=?)) GROUP BY resolution', (snapshot, snapshot, target)))
        reader.db.execute('COMMIT')
        reader.db.set_progress_handler(None, 0)
        # Do not accept a caller-supplied saved audit as evidence of current files.
        current = audit(database, snapshot=snapshot, roots=roots, external_roots=external_roots)
        if reader._version() != version:
            raise ValueError('Database changed during readiness assessment; retry')
    except sqlite3.OperationalError as error:
        raise ValueError('Readiness query unavailable or SQL work budget exceeded') from error
    finally:
        reader.close()

    checks = []
    def check(code, passed, detail, action):
        checks.append({'code': code, 'status': 'pass' if passed else 'blocked',
                       'detail': detail, 'next_action': None if passed else action})

    check('recorded_inputs', current['status'] == 'recorded_inputs_match',
          {'status': current['status'], 'artifact_counts': current['counts'],
           'more_artifacts': current['more_artifacts'], 'scope': 'whole snapshot, including other targets'},
          'Resolve stale/missing inputs or unchecked scope; reindex changed inputs in a new snapshot.')
    check('selected_target_parses', bool(states.get('parsed')) and sum(states.values()) == states.get('parsed', 0),
          {'target': target, 'compilation_states': states},
          'Parse every selected-target compilation; investigate failures. Exclusions require an explicit scope policy.')
    discovery = {item['component']: item['status'] for item in current['engineering_directory_membership']}
    component_states = {c: discovery.get(c, 'not_imported') if imported[c] else 'not_imported' for c in selected}
    check('engineering_discovery', all(v == 'matched' for v in component_states.values()),
          {'components': component_states, 'selection': 'explicit operator scope; not inferred application membership'},
          'Import selected engineering components with recorded directory membership in a new snapshot.')
    check('toolchain_identity', False,
          {'status': 'not_validated', 'external_artifacts': origins.get('external', 0),
           'external_input_audit': current['external_inputs']},
          'Bind parser/compiler binaries and configuration to a verified toolchain manifest; matching mapped headers and operator labels are insufficient.')
    generated = origins.get('generated', 0)
    if generated:
        check('generator_provenance', False, {'generated_artifacts': generated, 'scope': 'whole snapshot'},
              'Bind generated outputs to generator version, configuration, and declared input hashes; output hashes alone are insufficient.')
    else:
        checks.append({'code': 'generator_provenance', 'status': 'not_applicable',
                       'detail': 'No generated artifacts are recorded; this does not establish discovery completeness.', 'next_action': None})
    check('scope_completeness', False,
          {'status': 'not_established', 'scope': 'scoped compilation inventory and narrow engineering discovery'},
          'Define the target/application boundary, omitted source classes and discovery completeness policy.')
    check('publication_contract', False,
          {'status': 'not_implemented', 'snapshot_state': current['snapshot']['state']},
          'Implement immutable publication and retrieval-time freshness enforcement after input and scope policies are satisfied.')
    return {'assessment_version': 1, 'inspection_only': True, 'context_eligible': False,
            'status': 'blocked', 'snapshot': current['snapshot'], 'target': target,
            'engineering_components': selected, 'checked_at': current['checked_at'],
            'checks': checks, 'blocking_codes': [c['code'] for c in checks if c['status'] == 'blocked'],
            'relationship_resolution_counts': relationships,
            'verification': {'requirement_satisfaction': 'not_assessed',
                             'test_execution': 'not_assessed', 'review_approval': 'not_assessed'},
            'limitations': ['Freshness scans all recorded snapshot inputs conservatively; parse coverage is target-specific.',
                'Resolved relationships identify entities; they do not prove requirements or test satisfaction.',
                'Candidate and unresolved relationships must remain labeled in inspection results.',
                'This assessment neither changes snapshot state nor enables an agent retrieval route.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('database', 'snapshot', 'target'):
        parser.add_argument('--' + key, required=True)
    parser.add_argument('--component', action='append', required=True, choices=sorted(COMPONENTS))
    parser.add_argument('--repo-root'); parser.add_argument('--build-root')
    parser.add_argument('--external-root', action='append', default=[], type=mapping_argument,
                        metavar='RECORDED_PREFIX=LOCAL_DIRECTORY')
    args = parser.parse_args()
    result = assess(args.database, snapshot=args.snapshot, target=args.target, components=args.component,
                    external_roots=args.external_root,
                    roots={k: v for k, v in [('repo', args.repo_root), ('build', args.build_root)] if v})
    print(canonical(result))


if __name__ == '__main__': main()
