#!/usr/bin/env python3
"""Read-only inventory of a pinned F Prime checkout; no inferred verification."""
import argparse, collections, json, pathlib, re, subprocess
p = argparse.ArgumentParser()
p.add_argument('repository', type=pathlib.Path)
p.add_argument('--output', required=True, type=pathlib.Path)
a = p.parse_args()
root = a.repository.resolve()
def git(*args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
files = git('ls-files').splitlines()
counts = collections.defaultdict(lambda: {'files': 0, 'physical_lines': 0})
requirements, claims, declarations = [], [], []
for name in files:
    path = root / name
    if not path.is_file():
        continue
    if path.suffix in {'.cpp', '.hpp', '.h', '.c', '.cc', '.fpp'}:
        group = 'fpp_models' if path.suffix == '.fpp' else ('test_cpp' if any(x in {'test','tests','ut'} for x in path.parts) else 'other_cpp')
        counts[group]['files'] += 1
        counts[group]['physical_lines'] += len(path.read_bytes().splitlines())
    if name.endswith('docs/sdd.md'):
        heading = ''
        for line_number, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
            if line.startswith('#'):
                heading = line.lstrip('# ').strip()
            match = re.match(r'^\s*([A-Z][A-Z0-9_-]*-\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*$', line)
            if match:
                requirements.append(dict(id=match[1], text=match[2], verification_method=match[3], path=name, line=line_number, provenance='upstream-authored requirement'))
            if 'Requirement verified:' in line:
                claims.append(dict(path=name, line=line_number, section=heading, text=line.strip(), status='upstream documentation claim; not execution evidence'))
    if path.name == 'CMakeLists.txt':
        for line_number, line in enumerate(path.read_text(errors='replace').splitlines(),1):
            if re.match(r'^\s*register_fprime_(deployment|executable)\s*\(',line):
                declarations.append(dict(path=name,line=line_number,text=line.strip()))
report = dict(repository='https://github.com/nasa/fprime.git', revision=git('rev-parse','HEAD'), submodules=git('submodule','status').splitlines(), tracked_files=len(files), counts=dict(counts), counting_notes='Physical lines include comments and blanks. Path-based test classification. Excludes untracked generated build products and submodule contents. other_cpp is not a certified production SLOC count.', executable_declarations=declarations, declaration_note='Textual CMake declarations, not resolved applications or configured targets.', requirements=requirements, documentation_verification_claims=claims)
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in {'requirements','documentation_verification_claims','executable_declarations'}},indent=2))
print(f'{len(requirements)} requirement rows; {len(claims)} documentation verification claims; {len(declarations)} executable/deployment declarations')
