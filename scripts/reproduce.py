"""Replay the recorded assistant-authored fix in a disposable copy; no external AI call."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atlas_engine.indexer import build_index
from atlas_engine.test_runner import run_tests

project = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='atlas-replay-') as temporary:
    repo = Path(temporary) / 'aurora'
    shutil.copytree(project/'samples/aurora', repo, ignore=shutil.ignore_patterns('.atlas'))
    target = repo/'src/RenderEngine.cpp'
    target.write_bytes((project/'experiments/RenderEngine.before.cpp').read_bytes())
    before = run_tests(repo)
    assert before['passed'] == 4 and before['total'] == 8
    graph = build_index(repo)
    command = ['node', str(project/'scripts/agent.mjs'), 'context', '--repo', str(repo), '--seed', 'REQ-UI-002', '--budget-chars', '32000']
    context = json.loads(subprocess.check_output(command, text=True))
    assert any(i['name'] == 'aurora::Geometry::clampDimension(int)' for i in context['items'])
    target.write_bytes((project/'samples/aurora/src/RenderEngine.cpp').read_bytes())
    stale = subprocess.run(command, capture_output=True, text=True)
    assert stale.returncode == 2 and json.loads(stale.stderr)['error']['code'] == 'STALE_INDEX'
    refreshed = build_index(repo)
    assert refreshed['parse_stats']['parsed'] == ['src/RenderEngine.cpp']
    assert len(refreshed['parse_stats']['reused']) == 5
    after = run_tests(repo)
    assert after['passed'] == 8 and after['total'] == 8
    final = build_index(repo)
    assert final['test_evidence']['current']
    print(json.dumps({'replay':'recorded assistant-authored change; no model call', 'before':f"{before['passed']}/{before['total']}", 'after':f"{after['passed']}/{after['total']}", 'stale_retrieval':'rejected', 'refresh':refreshed['parse_stats'], 'retrieved_items':len(context['items']), 'context_characters':context['serialized_chars']},indent=2))
