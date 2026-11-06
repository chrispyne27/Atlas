import http.client,json,threading,unittest
from urllib.parse import urlencode
import test_storage_details as fixtures
from atlas_engine.storage.http import InspectionServer

class HTTPInspectionTests(unittest.TestCase):
    def setUp(self):
        fixtures.DetailTests.setUp(self)
        self.server=InspectionServer(database=self.path,snapshot='s',target='A',roots={'repo':self.root})
        thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':0.01},daemon=True);thread.start()
        def stop():self.server.shutdown();self.server.server_close();thread.join(timeout=2)
        self.addCleanup(stop)
    def request(self,path,params=None,headers=None,method='GET'):
        connection=http.client.HTTPConnection(*self.server.server_address,timeout=3)
        supplied={'Authorization':'Bearer '+self.server.token};supplied.update(headers or {})
        connection.request(method,path+('?' + urlencode(params) if params else ''),headers=supplied)
        response=connection.getresponse();body=response.read();info=dict(response.getheaders());status=response.status
        connection.close();return status,json.loads(body),info

    def test_real_routes_pagination_and_source(self):
        status,config,headers=self.request('/api/config')
        self.assertEqual(status,200);self.assertTrue(config['inspection_only']);self.assertEqual(headers['Cache-Control'],'no-store')
        status,lookup,_=self.request('/api/lookup',{'value':'root'});self.assertEqual(lookup['items'][0]['id'],'root')
        status,page,_=self.request('/api/neighbors',{'value':'root','limit':1});self.assertTrue(page['truncated'])
        status,next_page,_=self.request('/api/neighbors',{'value':'root','limit':1,'cursor':page['next_cursor']});self.assertEqual(status,200)
        self.assertNotEqual(page['items'][0]['id'],next_page['items'][0]['id'])
        self.assertEqual(self.request('/api/evidence',{'evidence':'ev'})[0],200)
        status,source,_=self.request('/api/source',{'evidence':'ev','start':2,'end':2})
        self.assertEqual(source['text'],'second\n');self.assertTrue(source['hash_verified'])

    def test_auth_host_and_origin(self):
        self.assertEqual(self.request('/api/config',headers={'Authorization':'Bearer wrong'})[0],401)
        self.assertEqual(self.request('/api/config',headers={'Host':'evil.example'})[0],403)
        self.assertEqual(self.request('/api/config',headers={'Origin':'https://example.com'})[0],403)
        self.assertEqual(self.request('/api/config',headers={'Origin':self.server.origin})[0],200)
        self.assertNotIn('Access-Control-Allow-Origin',self.request('/api/config')[2])

    def test_reject_writes_paths_and_bad_queries(self):
        self.assertEqual(self.request('/api/config',method='POST')[0],405)
        self.assertEqual(self.request('/api/source',{'evidence':'ev','repo_root':'/etc'})[0],400)
        self.assertEqual(self.request('/api/lookup',{'value':'root','target':'B'})[0],400)
        self.assertEqual(self.request('/api/neighbors',{'value':'root','limit':201})[0],400)
        self.assertEqual(self.request('/api/lookup?value=root&value=child')[0],400)
        self.assertEqual(self.request('/api/lookup')[0],400)
        self.assertEqual(self.request('/missing')[0],404)

    def test_stale_source_is_data_status_not_current_text(self):
        self.source.write_text('changed')
        status,data,_=self.request('/api/source',{'evidence':'ev'})
        self.assertEqual(status,200);self.assertEqual(data['status'],'stale');self.assertIsNone(data['text'])
        self.assertEqual(self.server.server_address[0],'127.0.0.1')

if __name__=='__main__':unittest.main()
