import http.client,threading,unittest
import test_storage_details as fixtures
from atlas_engine.storage.http import InspectionServer

class LocalViewTests(unittest.TestCase):
    def setUp(self):
        fixtures.DetailTests.setUp(self)
        self.server=InspectionServer(database=self.path,snapshot='s',target='A',roots={'repo':self.root})
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':0.01},daemon=True);self.thread.start()
        self.addCleanup(self.stop)
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=2)
    def get(self,path,auth=False):
        c=http.client.HTTPConnection(*self.server.server_address,timeout=3)
        c.request('GET',path,headers={'Authorization':'Bearer '+self.server.token} if auth else {})
        r=c.getresponse();result=(r.status,r.read(),dict(r.getheaders()));c.close();return result
    def test_assets_are_same_origin_and_secret_free(self):
        for path in ['/','/local-trace.html','/local-trace.js','/local-trace.css']:
            status,body,headers=self.get(path)
            self.assertEqual(status,200);self.assertNotIn(self.server.token.encode(),body)
            self.assertIn("connect-src 'self'",headers['Content-Security-Policy'])
        self.assertEqual(self.get('/api/config')[0],401)
    def test_static_allowlist_does_not_expose_repository(self):
        for path in ['/../.atlas/fprime-rebuilt.sqlite','/.openai/hosting.json','/local-trace.js?token=test','/README.md','/index.html']:
            self.assertEqual(self.get(path,auth=True)[0],404)

if __name__=='__main__':unittest.main()
