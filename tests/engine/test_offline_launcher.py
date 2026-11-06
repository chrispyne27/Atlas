"""Exercise the shipped shell launcher as a process, outside its package directory."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import time
import unittest
from urllib.parse import urlencode, urlsplit

import test_storage_details as fixtures

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(sys.platform.startswith('linux') and shutil.which('sh'), 'Linux shell launcher')
class OfflineLauncherTests(unittest.TestCase):
    def setUp(self):
        fixtures.DetailTests.setUp(self)
        # Copy only shipped runtime inputs, without git, installed parser or build tools.
        self.package = self.path.parent / 'extracted package with spaces'
        self.package.mkdir()
        shutil.copytree(ROOT / 'atlas_engine', self.package / 'atlas_engine',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (self.package / 'public').mkdir()
        for name in ('local-trace.html', 'local-trace.css', 'local-trace.js'):
            shutil.copyfile(ROOT / 'public' / name, self.package / 'public' / name)
        (self.package / 'scripts').mkdir()
        shutil.copyfile(ROOT / 'scripts/start-local.sh', self.package / 'scripts/start-local.sh')
        self.before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.start()

    def start(self):
        env = {key: value for key, value in os.environ.items() if not key.startswith('PYTHON')}
        env['ATLAS_PYTHON'] = sys.executable
        self.process = subprocess.Popen(
            ['sh', str(self.package / 'scripts/start-local.sh'),
             '--database', str(self.path), '--snapshot', 's', '--target', 'A',
             '--repo-root', str(self.root), '--port', '0'],
            cwd=self.path.parent, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(self.stop)
        selector = selectors.DefaultSelector()
        selector.register(self.process.stdout, selectors.EVENT_READ)
        output = b''
        try:
            deadline = time.monotonic() + 8
            while output.count(b'\n') < 2 and time.monotonic() < deadline:
                if selector.select(timeout=0.1):
                    chunk = os.read(self.process.stdout.fileno(), 4096)
                    if not chunk:
                        break
                    output += chunk
                    if len(output) > 8192:
                        break
        finally:
            selector.close()
        # Never include raw startup output (which contains the session token) in failures.
        lines = output.decode('utf-8').splitlines()
        if len(lines) != 2 or not lines[0].startswith('Atlas local inspection: ') or not lines[1].startswith('Authorization: Bearer '):
            self.fail('Launcher did not provide expected startup lines within deadline')
        self.origin = lines[0].split(': ', 1)[1]
        self.token = lines[1].split('Bearer ', 1)[1]
        parsed = urlsplit(self.origin)
        self.assertEqual(parsed.hostname, '127.0.0.1')
        self.port = parsed.port

    def stop(self):
        process = self.process
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=3)
        process.stdout.close(); process.stderr.close()

    def request(self, route, params=None, headers=None, method='GET', authenticated=True):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        supplied = {'Authorization': 'Bearer ' + self.token} if authenticated else {}
        supplied.update(headers or {})
        try:
            connection.request(method, route + ('?' + urlencode(params) if params else ''), headers=supplied)
            response = connection.getresponse()
            return response.status, response.read(), dict(response.getheaders())
        finally:
            connection.close()

    def test_launcher_trace_and_security_boundaries(self):
        status, body, _ = self.request('/', authenticated=False)
        self.assertEqual(status, 200); self.assertIn(b'local-trace.js', body)
        for route in ('/local-trace.js', '/local-trace.css'):
            self.assertEqual(self.request(route, authenticated=False)[0], 200)
        self.assertEqual(self.request('/api/config', authenticated=False)[0], 401)
        self.assertEqual(self.request('/api/config', headers={'Host': 'example.invalid'})[0], 403)
        self.assertEqual(self.request('/api/config', headers={'Origin': 'https://example.invalid'})[0], 403)
        self.assertEqual(self.request('/api/config', method='POST')[0], 405)
        status, body, headers = self.request('/api/config')
        self.assertEqual(status, 200); self.assertTrue(json.loads(body)['inspection_only'])
        self.assertEqual(headers['Cache-Control'], 'no-store')
        status, body, _ = self.request('/api/lookup', {'value': 'root'})
        self.assertEqual(status, 200); self.assertEqual(json.loads(body)['items'][0]['id'], 'root')
        first = json.loads(self.request('/api/neighbors', {'value': 'root', 'limit': 1})[1])
        second = json.loads(self.request('/api/neighbors', {'value': 'root', 'limit': 1, 'cursor': first['next_cursor']})[1])
        self.assertNotEqual(first['items'][0]['id'], second['items'][0]['id'])
        self.assertEqual(self.request('/api/evidence', {'evidence': 'ev'})[0], 200)
        excerpt = json.loads(self.request('/api/source', {'evidence': 'ev', 'start': 2, 'end': 2})[1])
        self.assertTrue(excerpt['hash_verified']); self.assertEqual(excerpt['text'], 'second\n')
        self.source.write_text('changed')
        stale = json.loads(self.request('/api/source', {'evidence': 'ev'})[1])
        self.assertEqual(stale['status'], 'stale'); self.assertIsNone(stale['text'])
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), self.before)

    def test_restart_rotates_token(self):
        old_token = self.token
        self.stop()
        self.start()
        self.assertTrue(self.token != old_token, 'Restart must rotate session token')
        self.assertEqual(self.request('/api/config', headers={'Authorization': 'Bearer ' + old_token})[0], 401)
        self.assertEqual(self.request('/api/config')[0], 200)


if __name__ == '__main__':
    unittest.main()
