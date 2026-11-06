import argparse
import json
import sys
from pathlib import Path
from .indexer import build_index

parser = argparse.ArgumentParser(description='Atlas compiler-derived C++ graph indexer')
parser.add_argument('operation', choices=['index', 'test'])
parser.add_argument('--repo', default='samples/aurora')
parser.add_argument('--output')
args = parser.parse_args()
try:
    if args.operation == 'index':
        result = build_index(args.repo, args.output)
        print(json.dumps({'repository': result['repository'], 'entities': len(result['nodes']), 'relationships': len(result['edges']), 'parse_stats': result['parse_stats'], 'unresolved': len(result['unresolved'])}, indent=2))
    else:
        from .test_runner import run_tests
        result = run_tests(args.repo, args.output)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result['passed'] == result['total'] else 1)
except Exception as error:
    print(json.dumps({'error': type(error).__name__, 'message': str(error)}), file=sys.stderr)
    sys.exit(2)
