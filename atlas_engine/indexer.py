"""Index one explicitly configured C++ repository. No shell commands are executed from the compilation database."""
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from . import SCHEMA_VERSION, INDEXER_VERSION

SOURCE_EXTENSIONS = {'.cpp', '.cc', '.cxx', '.c', '.h', '.hpp', '.hh', '.hxx'}
MANIFESTS = {'compile_commands.json', 'requirements.json', 'test_manifest.json'}
IGNORED = {'.git', '.atlas', 'build', 'dist', 'node_modules', '__pycache__'}


def digest(value):
    return hashlib.sha256(value).hexdigest()


def inventory(root):
    root = Path(root).resolve()
    result = {}
    for p in sorted(root.rglob('*')):
        relative = p.relative_to(root)
        if any(part in IGNORED for part in relative.parts):
            continue
        if p.is_file() and (p.suffix in SOURCE_EXTENSIONS or p.name in MANIFESTS):
            if not p.resolve().is_relative_to(root):
                raise ValueError('Indexed source must remain within repository: ' + str(relative))
            result[relative.as_posix()] = digest(p.read_bytes())
    return result


def fingerprint(inputs):
    return digest(json.dumps(inputs, sort_keys=True, separators=(',', ':')).encode())


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def git_revision(root):
    try:
        commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain', '--', '.'], text=True).strip())
        return {'commit': commit, 'dirty': dirty}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {'commit': None, 'dirty': None}


def component(path):
    lower = path.lower()
    if 'render' in lower:
        return 'render'
    if 'uilayer' in lower or 'layout' in lower:
        return 'ui'
    if 'asset' in lower:
        return 'resources'
    return 'core'


def relative_path(root, file):
    if file is None:
        return None
    path = Path(str(file)).resolve()
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else None


def qualified(cursor, display=False):
    names = [cursor.displayname if display else cursor.spelling]
    parent = cursor.semantic_parent
    while parent and parent.kind.name != 'TRANSLATION_UNIT':
        if parent.spelling:
            names.append(parent.spelling)
        parent = parent.semantic_parent
    return '::'.join(reversed(names))


def compiler_arguments(entry, root):
    # Command strings have platform-specific quoting. Require the unambiguous arguments form.
    if not isinstance(entry.get('arguments'), list) or not entry['arguments']:
        raise ValueError('Compilation entries must contain an arguments array, not a command string.')
    directory = (root / entry.get('directory', '.')).resolve()
    if not directory.is_relative_to(root):
        raise ValueError('Compilation working directory must be inside the repository.')
    source = (directory / entry['file']).resolve()
    if not source.is_relative_to(root):
        raise ValueError('Compilation source must be inside the repository.')
    original = entry['arguments'][1:]
    args = []
    i = 0
    while i < len(original):
        arg = original[i]
        if arg in ['-o', '-MF', '-MT', '-MQ']:
            i += 2
            continue
        if arg in ['-c', '-MD', '-MMD', '-MP']:
            i += 1
            continue
        if arg.startswith('@') or arg in ['-Xclang', '-load', '-fplugin'] or arg.startswith('-fplugin='):
            raise ValueError('Response files and compiler plugins are not supported in this indexer.')
        if arg in ['-I', '-isystem', '-iquote', '-include']:
            if i + 1 >= len(original):
                raise ValueError('Missing value for ' + arg)
            args += [arg, str((directory / original[i + 1]).resolve())]
            i += 2
            continue
        if arg.startswith('-I') and len(arg) > 2:
            args.append('-I' + str((directory / arg[2:]).resolve()))
        elif not arg.startswith('-') and (directory / arg).resolve() == source:
            pass
        else:
            args.append(arg)
        i += 1
    return source, args


def parse_unit(root, source, arguments):
    from clang.cindex import Index, CursorKind, Diagnostic
    index = Index.create()
    tu = index.parse(str(source), args=arguments)
    errors = [str(d) for d in tu.diagnostics if d.severity >= Diagnostic.Error]
    if errors:
        raise ValueError('Compiler errors prevent an authoritative index:\n' + '\n'.join(errors))
    nodes, declarations, calls, includes, unresolved = {}, [], [], [], []
    kinds = {CursorKind.FUNCTION_DECL, CursorKind.CXX_METHOD, CursorKind.CONSTRUCTOR, CursorKind.DESTRUCTOR, CursorKind.FUNCTION_TEMPLATE}
    for inclusion in tu.get_includes():
        a, b = relative_path(root, inclusion.source), relative_path(root, inclusion.include)
        if a and b:
            includes.append({'from': 'file:' + a, 'to': 'file:' + b, 'type': 'includes', 'provenance': 'libclang include directive', 'path': a, 'line': inclusion.location.line})
    dependencies = {relative_path(root, source)} | {relative_path(root, inc.include) for inc in tu.get_includes()}
    dependencies.discard(None)

    def walk(cursor, owner=None):
        path = relative_path(root, cursor.location.file)
        if cursor.kind != CursorKind.TRANSLATION_UNIT and path is None:
            return
        if cursor.kind in kinds:
            usr = cursor.get_usr()
            if not usr:
                return
            if not cursor.is_definition():
                declarations.append({'symbol': usr, 'file': 'file:' + path})
                return
            start, end = cursor.extent.start, cursor.extent.end
            if str(start.file) != str(end.file):
                unresolved.append({'owner': usr, 'path': path, 'line': cursor.location.line, 'reason': 'Multi-file/macro definition extent'})
                return
            code = (root / path).read_bytes()[start.offset:end.offset].decode('utf-8')
            # Implicit constructors have no authored body and must not masquerade as source definitions.
            if not any(c.kind == CursorKind.COMPOUND_STMT for c in cursor.get_children()):
                return
            nodes[usr] = {'id': usr, 'kind': 'method', 'name': qualified(cursor), 'signature': qualified(cursor, True),
                          'path': path, 'line': start.line, 'end_line': end.line, 'code': code,
                          'content_hash': digest(code.encode()), 'component': component(path),
                          'description': 'Definition extracted from the authored C++ fixture.',
                          'metadata': {'language': 'C++', 'provenance': 'libclang definition', 'criticality': 'Unclassified'},
                          'harness': cursor.spelling == 'main' and path.startswith('tests/')}
            owner = usr
        elif cursor.kind == CursorKind.CALL_EXPR and owner:
            ref = cursor.referenced
            target = ref.get_usr() if ref else ''
            dynamic = ref and ref.kind == CursorKind.CXX_METHOD and ref.is_virtual_method()
            if ref and ref.kind in kinds and target and not dynamic:
                calls.append({'from': owner, 'to': target, 'type': 'calls', 'provenance': 'libclang direct call', 'path': path, 'line': cursor.location.line, 'confidence': 'resolved'})
            else:
                unresolved.append({'owner': owner, 'path': path, 'line': cursor.location.line, 'spelling': cursor.spelling, 'reason': 'Dynamic dispatch' if dynamic else 'Unresolved or indirect call'})
        for child in cursor.get_children():
            walk(child, owner)
    walk(tu.cursor)
    return {'nodes': list(nodes.values()), 'declarations': declarations, 'calls': calls, 'includes': includes,
            'unresolved': unresolved, 'dependencies': sorted(dependencies),
            'diagnostics': [str(d) for d in tu.diagnostics]}


def resolve_symbol(nodes, query):
    exact = [n for n in nodes if n['id'] == query or n['signature'] == query]
    candidates = exact or [n for n in nodes if n['name'] == query]
    if len(candidates) != 1:
        raise ValueError('Unknown or ambiguous symbol in engineering manifest: ' + query + ' (candidates: ' + ', '.join(n['signature'] for n in candidates) + ')')
    return candidates[0]['id']


def build_index(repo, output=None, cache_dir=None):
    start = time.perf_counter()
    root = Path(repo).resolve()
    inputs = inventory(root)
    for name in MANIFESTS:
        if name not in inputs:
            raise ValueError('Missing repository manifest: ' + name)
    cache_dir = Path(cache_dir or root / '.atlas' / 'units')
    entries = json.loads((root / 'compile_commands.json').read_text())
    if not entries:
        raise ValueError('Compilation database is empty.')
    from importlib.metadata import version
    toolchain = version('libclang')
    source_inventory = sorted(p for p in inputs if Path(p).suffix in SOURCE_EXTENSIONS)
    cache_salt = {'version': INDEXER_VERSION, 'libclang': toolchain, 'members': source_inventory,
                  'compile_db_hash': inputs['compile_commands.json']}
    units, parsed, reused, unit_names = [], [], [], set()
    for entry in entries:
        source, args = compiler_arguments(entry, root)
        rel = source.relative_to(root).as_posix()
        if rel in unit_names:
            raise ValueError('Multiple build configurations for one translation unit are not supported: ' + rel)
        unit_names.add(rel)
        identity = digest(json.dumps([cache_salt, rel, args], sort_keys=True).encode())
        cache_path = cache_dir / (identity + '.json')
        cached = None
        if cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text())
                if any(inputs.get(p) != h for p, h in cached['dependency_hashes'].items()):
                    cached = None
            except (ValueError, KeyError):
                cached = None
        if cached:
            unit = cached['unit']
            reused.append(rel)
        else:
            unit = parse_unit(root, source, args)
            atomic_json(cache_path, {'dependency_hashes': {p: inputs[p] for p in unit['dependencies']}, 'unit': unit})
            parsed.append(rel)
        units.append(unit)
    node_map, raw_edges, unresolved = {}, [], []
    for unit in units:
        for n in unit['nodes']:
            previous = node_map.get(n['id'])
            if previous and previous['content_hash'] != n['content_hash']:
                raise ValueError('Conflicting definitions/configurations for: ' + n['signature'])
            node_map[n['id']] = n
        raw_edges.extend(unit['calls'] + unit['includes'])
        unresolved.extend(unit['unresolved'])
    methods = list(node_map.values())
    for unit in units:
        for d in unit['declarations']:
            if d['symbol'] in node_map:
                raw_edges.append({'from': d['symbol'], 'to': d['file'], 'type': 'declared in', 'provenance': 'libclang declaration'})
    for p in source_inventory:
        code = (root / p).read_text(encoding='utf-8')
        node_map['file:' + p] = {'id': 'file:' + p, 'kind': 'file', 'name': p, 'path': p, 'line': 1, 'end_line': len(code.splitlines()), 'code': code, 'content_hash': inputs[p], 'component': component(p), 'description': 'Indexed source file.', 'metadata': {'provenance': 'repository source', 'language': 'C++'}}
    for method in methods:
        raw_edges.append({'from': method['id'], 'to': 'file:' + method['path'], 'type': 'defined in', 'provenance': 'libclang definition'})
    requirements = json.loads((root / 'requirements.json').read_text())
    seen_requirements = set()
    for r in requirements:
        if r['id'] in seen_requirements or r['id'] in node_map:
            raise ValueError('Duplicate requirement ID: ' + r['id'])
        seen_requirements.add(r['id'])
        linked = [resolve_symbol(methods, name) for name in r['symbols']]
        node_map[r['id']] = {'id': r['id'], 'kind': 'requirement', 'name': r['name'], 'description': r['text'], 'path': 'requirements.json', 'component': 'ui' if 'UI' in r['id'] else 'resources' if 'RES' in r['id'] else 'core', 'parent': r['parent'], 'category': 'Functional', 'methods': linked, 'test': None, 'tests': [], 'constraints': r['constraints'], 'metadata': {k: r[k] for k in ['owner', 'criticality', 'verification', 'parent']}, 'provenance': 'explicit requirements.json mapping'}
        node_map[r['id']]['metadata']['design'] = r.get('design', 'No recorded design decision')
        for mid in linked:
            raw_edges.append({'from': mid, 'to': r['id'], 'type': 'implements', 'provenance': 'explicit requirements.json mapping'})
    fixtures = json.loads((root / 'test_manifest.json').read_text())
    seen_tests = set()
    for fixture in fixtures:
        if fixture['id'] in seen_tests:
            raise ValueError('Duplicate test fixture: ' + fixture['id'])
        seen_tests.add(fixture['id'])
        mid = resolve_symbol(methods, fixture['symbol'])
        node_map[mid].update({'kind': 'test', 'fixture_id': fixture['id'], 'test_role': fixture['role']})
        node_map[mid]['metadata']['result'] = 'Not executed for this snapshot'
        for rid in fixture['requirements']:
            if rid not in seen_requirements:
                raise ValueError('Test refers to missing requirement: ' + rid)
            raw_edges.append({'from': mid, 'to': rid, 'type': 'verifies', 'provenance': 'explicit test_manifest.json mapping'})
            node_map[rid]['tests'].append(mid)
    for r in requirements:
        node = node_map[r['id']]
        node['test'] = next(iter(node['tests']), None)
        node['status'] = 'Unlinked' if not node['methods'] else 'Covered' if node['tests'] else 'Partial'
    for cid, label in [('render', 'Rendering'), ('ui', 'User interface'), ('resources', 'Resources'), ('core', 'Core & platform')]:
        node_map['component-' + cid] = {'id': 'component-' + cid, 'kind': 'component', 'name': label, 'component': cid, 'description': 'Display grouping derived from source paths; not a compiler-defined architectural boundary.', 'metadata': {'provenance': 'documented source-path grouping'}}
    for method in methods:
        raw_edges.append({'from': method['id'], 'to': 'component-' + method['component'], 'type': 'belongs to', 'provenance': 'source-path display grouping'})
    unique = {}
    for edge in raw_edges:
        if edge['from'] not in node_map or edge['to'] not in node_map:
            if edge['type'] == 'calls':
                unresolved.append({'owner': edge['from'], 'target': edge['to'], 'path': edge['path'], 'line': edge['line'], 'reason': 'Referenced declaration has no indexed authored definition (may be external or implicit)'})
            continue
        key = (edge['from'], edge['to'], edge['type'])
        if key not in unique:
            unique[key] = edge
        if edge['type'] == 'calls':
            a, b = node_map[edge['from']]['component'], node_map[edge['to']]['component']
            if a != b:
                unique[('component-' + a, 'component-' + b, 'depends on')] = {'from': 'component-' + a, 'to': 'component-' + b, 'type': 'depends on', 'provenance': 'aggregation of resolved cross-component calls'}
    # Never publish a snapshot if inputs changed during parsing.
    if inventory(root) != inputs:
        raise ValueError('Repository changed during indexing; retry with stable inputs.')
    fp = fingerprint(inputs)
    evidence_path = root / '.atlas' / 'test-results.json'
    evidence = json.loads(evidence_path.read_text()) if evidence_path.exists() else None
    evidence_current = evidence is not None and evidence.get('source_fingerprint') == fp
    if evidence_current:
        test_lookup = {t['id']: t for t in evidence['tests']}
        for node in node_map.values():
            if node.get('fixture_id') in test_lookup:
                test = test_lookup[node['fixture_id']]
                node['evidence'] = {**test, 'executed_at': evidence['executed_at'], 'source_fingerprint': fp, 'compiler': evidence['compiler']}
                node['metadata']['result'] = test['status'] + ' · executed native test'
    for node in node_map.values():
        node.setdefault('metadata', {})['baseline'] = fp[:12]
    result = {'schema_version': SCHEMA_VERSION, 'indexer_version': INDEXER_VERSION, 'dataset': 'indexed-fixture',
              'repository': {**git_revision(root), 'fingerprint': fp, 'name': 'aurora-cpp-fixture'},
              'test_evidence': {'current': evidence_current, 'results': evidence if evidence_current else None},
              'inputs': inputs, 'nodes': sorted(node_map.values(), key=lambda n: n['id']),
              'edges': sorted(unique.values(), key=lambda e: (e['from'], e['type'], e['to'])),
              'unresolved': list({json.dumps(u, sort_keys=True): u for u in unresolved}.values()),
              'parse_stats': {'parsed': parsed, 'reused': reused, 'translation_units': len(entries), 'elapsed_seconds': round(time.perf_counter() - start, 4), 'libclang_version': toolchain},
              'limitations': ['Direct calls only; virtual/indirect targets are not expanded.', 'One build configuration; source-level graph, not runtime behavior.', 'Requirements/test links are explicit assertions, not proof of compliance.', 'Display components are source-path groupings.']}
    atomic_json(output or root / '.atlas' / 'index.json', result)
    return result
