import json
from pathlib import Path
import subprocess
import sys
import unittest


class TraceAcceptanceTests(unittest.TestCase):
    def test_reproducible_synthetic_cli_workflow(self):
        project = Path(__file__).resolve().parents[2]
        result = subprocess.run([sys.executable, str(project/'scripts/check-trace-packet.py')],
            cwd=project, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        synthetic = report['synthetic']
        self.assertEqual(synthetic['status'], 'passed')
        self.assertTrue(synthetic['stable_repeat'])
        self.assertTrue(synthetic['db_bytes_unchanged'])
        self.assertFalse(synthetic['context_eligible'])
        self.assertEqual(report['fprime']['status'], 'not_run')
        self.assertTrue(all(r['provenance']=='authored' for r in synthetic['relationships']))
        self.assertTrue(any(r['resolution']=='unresolved' for r in synthetic['relationships']))
        self.assertTrue(any(r['resolution']=='candidate' for r in synthetic['relationships']))
        self.assertEqual(len(synthetic['source_statuses']), 4)


if __name__=='__main__':unittest.main()
