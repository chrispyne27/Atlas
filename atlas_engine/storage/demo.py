"""Create a synthetic offline trace fixture; no compiler or test execution claims."""
import argparse
import json
from pathlib import Path
from .store import connect, digest, canonical

SNAPSHOT = 'synthetic-demo-v1'
TARGET = 'synthetic-demo-target'
SOURCE = '''// SYNTHETIC ATLAS DEMO: illustrative source; not compiled or executed.
int value() { return 1; }
int helper() { return value(); }
void nominal_test() { helper(); }
// DEMO-001: illustrative requirement: value returns one.
// DEMO-ALIAS-001: an unapproved alternative identifier.
// Unknown callback target is deliberately unresolved in the fixture.
'''


def create(destination):
    destination = Path(destination).absolute()
    destination.mkdir()  # exclusive: never modify an existing directory or symlink
    repo = destination / 'repo'; repo.mkdir()
    source = repo / 'demo.cpp'; source.write_bytes(SOURCE.encode())
    db = connect(destination / 'demo.sqlite')
    try:
        db.execute('BEGIN IMMEDIATE')
        db.execute('INSERT INTO repository VALUES (?,?)', ('synthetic-demo', 'synthetic:atlas-offline-demo'))
        db.execute('INSERT INTO snapshot VALUES (?,?,?,?,?,?,?,?,?,?)',
                   (SNAPSHOT, 'synthetic-demo', 'synthetic-not-compiled', 'illustrative-only',
                    digest(SOURCE.encode()), 'not-assessed', 'synthetic-demo-v1', 1, 'staging', 'synthetic-fixed-date'))
        db.execute('INSERT INTO artifact VALUES (?,?,?,?)', (SNAPSHOT, 'repo/demo.cpp', digest(SOURCE.encode()), 'authored'))
        db.execute('INSERT INTO build_target VALUES (?,?,?,?)', (SNAPSHOT, TARGET, 'Synthetic demonstration only', 'test'))
        # Pending preserves visibility/scope without claiming a compiler has parsed it.
        db.execute('INSERT INTO compilation VALUES (?,?,?,?,?,?,?)',
                   (SNAPSHOT, 'synthetic-compilation', TARGET, 'repo/demo.cpp', 'synthetic-no-command', '[]', 'pending'))
        entities = [('test', 'test', 'Demo.Nominal', 4), ('helper', 'symbol', 'Demo.Helper', 3),
                    ('value', 'symbol', 'Demo.Value', 2), ('requirement', 'requirement', 'DEMO-001', 5),
                    ('alias', 'requirement', 'DEMO-ALIAS-001', 6)]
        for eid, kind, name, line in entities:
            evidence = 'demo-evidence-' + eid
            details = canonical({'synthetic': True, 'not_compiler_derived': True,
                                 'not_executed': True, 'not_requirement_verification': True,
                                 'description': 'Hand-authored illustrative fixture for offline navigation only.'})
            db.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?,?)',
                       (SNAPSHOT, evidence, 'authored', 'repo/demo.cpp', line, 'SYNTHETIC demo generator v1', details))
            db.execute('INSERT INTO entity VALUES (?,?,?,?,?,?)', (SNAPSHOT, eid, kind, 'synthetic', eid, name))
            db.execute('INSERT INTO occurrence VALUES (?,?,?,?,?,?,?,?,?)',
                       (SNAPSHOT, 'occurrence-'+eid, eid, 'synthetic-compilation', 'repo/demo.cpp', line, line, 'description', evidence))
        rows = [('01-test-helper', 'test', 'helper', 'helper', 'illustrative_call', 'resolved'),
                ('02-helper-value', 'helper', 'value', 'value', 'illustrative_call', 'resolved'),
                ('03-value-requirement', 'value', 'requirement', 'DEMO-001', 'candidate_implementation', 'candidate'),
                ('04-requirement-alias', 'requirement', 'alias', 'DEMO-ALIAS-001', 'candidate_alias', 'candidate'),
                ('05-helper-unresolved', 'helper', None, 'unknown_callback', 'illustrative_call', 'unresolved')]
        for rid, start, end, spelling, kind, resolution in rows:
            db.execute('INSERT INTO relation VALUES (?,?,?,?,?,?,?,?,?)',
                       (SNAPSHOT, rid, start, end, spelling, kind, resolution, 'synthetic-compilation', 'demo-evidence-'+start))
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Synthetic fixture foreign-key check failed')
        db.execute('COMMIT')
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Synthetic fixture integrity check failed')
    finally:
        db.close()
    report = {'status': 'synthetic_fixture_created', 'snapshot': SNAPSHOT, 'target': TARGET,
              'database': str(destination / 'demo.sqlite'), 'repo_root': str(repo),
              'search': 'Demo.Nominal', 'synthetic': True, 'compilations_parsed': 0,
              'test_executions': 0, 'review_approvals': 0, 'qualified': False}
    (destination / 'DEMO.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='New directory; parent must exist')
    args = parser.parse_args()
    print(json.dumps(create(args.output), indent=2))


if __name__ == '__main__':
    main()
