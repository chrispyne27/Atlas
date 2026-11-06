import argparse
import json
import sys
from .store import connect, import_manifest

p = argparse.ArgumentParser(description='Atlas local SQLite staging inventory')
p.add_argument('operation', choices=['init','import-manifest','parse-compilation','import-engineering','link-annotations','map-test-cases'])
p.add_argument('--database', required=True)
p.add_argument('--repository')
p.add_argument('--build-root')
p.add_argument('--compilation-database')
p.add_argument('--repository-id')
p.add_argument('--source-uri')
p.add_argument('--revision')
p.add_argument('--configuration-key')
p.add_argument('--toolchain-fingerprint')
p.add_argument('--target', action='append', dest='targets')
p.add_argument('--snapshot')
p.add_argument('--compilation')
p.add_argument('--system-include', action='append', default=[])
p.add_argument('--component', action='append', default=[])
a = p.parse_args()
try:
    if a.operation == 'import-manifest':
        fields = ['repository','build_root','compilation_database','repository_id','source_uri',
                  'revision','configuration_key','toolchain_fingerprint','targets']
        missing = [f for f in fields if not getattr(a,f)]
        if missing:
            p.error('Missing import options: ' + ', '.join(missing))
    if a.operation in ('parse-compilation','link-annotations','map-test-cases') and (not a.snapshot or not a.compilation):
        p.error(a.operation+' requires --snapshot and --compilation')
    if a.operation == 'import-engineering' and (not a.snapshot or not a.component):
        p.error('import-engineering requires --snapshot and --component')
    db = connect(a.database)
    try:
        if a.operation == 'map-test-cases':
            from .test_cases import map_test_cases
            result = map_test_cases(db, a.snapshot, a.compilation)
        elif a.operation == 'link-annotations':
            from .annotation_links import link_annotations
            result = link_annotations(db, a.snapshot, a.compilation)
        elif a.operation == 'import-engineering':
            from .engineering import import_engineering
            result = import_engineering(db, a.snapshot, a.component)
        elif a.operation == 'parse-compilation':
            from .compiler import parse_compilation
            result = parse_compilation(db, a.snapshot, a.compilation, a.system_include)
        else:
            result = {'schema_version':1} if a.operation == 'init' else import_manifest(db, **{f:getattr(a,f) for f in fields})
        print(json.dumps(result,indent=2))
    finally:
        db.close()
except Exception as error:
    print(json.dumps({'error':type(error).__name__,'message':str(error)}),file=sys.stderr)
    sys.exit(2)
