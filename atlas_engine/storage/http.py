"""Loopback-only, read-only local development adapter for bounded inspection."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import secrets
import sqlite3
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit
from .details import DetailInspector
from .inspect import MAX_BYTES
from .store import canonical


class InspectionServer(HTTPServer):
    request_queue_size=8
    allow_reuse_address=True

    def __init__(self,*,database,snapshot,target,roots=None,port=0):
        if type(port)!=int or not 0<=port<=65535:raise ValueError('Invalid port')
        self.database=Path(database).resolve(strict=True)
        self.snapshot=snapshot;self.target=target
        self.roots={}
        for key,value in (roots or {}).items():
            if key not in ('repo','build'):raise ValueError('Unsupported source root')
            root=Path(value).resolve(strict=True)
            if not root.is_dir():raise ValueError('Source root must be a directory')
            self.roots[key]=root
        reader=DetailInspector(self.database)
        try:
            row=reader.db.execute('SELECT id,revision,configuration_key,state FROM snapshot WHERE id=?',(snapshot,)).fetchone()
            if not row or not reader.db.execute('SELECT 1 FROM build_target WHERE snapshot_id=? AND id=?',(snapshot,target)).fetchone():
                raise ValueError('Unknown configured snapshot or target')
            self.description={'api_version':1,'inspection_only':True,'snapshot':dict(row),'target':target,
                'freshness':'not validated for current task context','scope':'partial graph; shared evidence is not target verification',
                'source_enabled':bool(self.roots),'limits':{'page_items':200,'query_bytes':MAX_BYTES,'detail_bytes':65536}}
            if len(canonical(self.description).encode())>MAX_BYTES:raise ValueError('Configured scope metadata exceeds budget')
        finally:reader.close()
        self.token=secrets.token_urlsafe(32)
        super().__init__(('127.0.0.1',port),InspectionHandler)
        self.authority='127.0.0.1:'+str(self.server_address[1])
        self.origin='http://'+self.authority

    def get_request(self):
        sock,address=super().get_request();sock.settimeout(5);return sock,address


class InspectionHandler(BaseHTTPRequestHandler):
    server_version='AtlasLocal/1'
    sys_version=''
    protocol_version='HTTP/1.0'

    def log_message(self,*args):
        # No request URL, token, query or source text logging.
        pass

    def send_error(self,code,message=None,explain=None):
        self.reply(code,{'error':'http_error','status':code})

    def reply(self,status,result):
        body=canonical(result).encode()
        if len(body)>MAX_BYTES:
            status=413;body=b'{"error":"response_budget_exceeded"}'
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        if self.command!='HEAD':
            try:self.wfile.write(body)
            except (BrokenPipeError,ConnectionResetError):pass
        self.close_connection=True

    def do_GET(self):
        if self.headers.get_all('Host')!=[self.server.authority]:
            return self.reply(403,{'error':'invalid_host'})
        origins=self.headers.get_all('Origin')
        if origins is not None and origins!=[self.server.origin]:
            return self.reply(403,{'error':'cross_origin_denied'})
        if self.headers.get('Sec-Fetch-Site')=='cross-site':
            return self.reply(403,{'error':'cross_site_denied'})
        assets={'/':'local-trace.html','/local-trace.html':'local-trace.html',
                '/local-trace.js':'local-trace.js','/local-trace.css':'local-trace.css'}
        if self.path in assets:
            root=Path(__file__).resolve().parents[2]/'public'
            path=(root/assets[self.path]).resolve()
            if not path.is_relative_to(root.resolve()):return self.reply(404,{'error':'asset_unavailable'})
            try:
                with path.open('rb') as stream:body=stream.read(512*1024+1)
            except OSError:return self.reply(404,{'error':'asset_unavailable'})
            if len(body)>512*1024:return self.reply(413,{'error':'asset_budget_exceeded'})
            mime={'.html':'text/html','.js':'text/javascript','.css':'text/css'}[path.suffix]
            self.send_response(200);self.send_header('Content-Type',mime+'; charset=utf-8')
            self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers();self.wfile.write(body);self.close_connection=True;return
        auth=self.headers.get_all('Authorization') or []
        if len(auth)!=1 or not secrets.compare_digest(auth[0],'Bearer '+self.server.token):
            return self.reply(401,{'error':'authorization_required'})
        lengths=self.headers.get_all('Content-Length')
        if self.headers.get('Transfer-Encoding') is not None or (lengths is not None and lengths!=['0']):
            return self.reply(400,{'error':'request_body_not_supported'})
        if len(self.path)>16384:return self.reply(414,{'error':'uri_too_long'})
        try:parsed=urlsplit(self.path)
        except ValueError:return self.reply(400,{'error':'invalid_request_target'})
        if parsed.scheme or parsed.netloc or parsed.fragment:
            return self.reply(400,{'error':'invalid_request_target'})
        routes={
            '/api/config':set(),
            '/api/lookup':{'value','field','kind','limit','cursor'},
            '/api/neighbors':{'value','direction','kind','limit','cursor'},
            '/api/evidence':{'evidence'},
            '/api/source':{'evidence','start','end'},
        }
        if parsed.path not in routes:return self.reply(404,{'error':'unknown_route'})
        try:
            pairs=parse_qsl(parsed.query,keep_blank_values=True,strict_parsing=True,max_num_fields=10)
            params=dict(pairs)
            if len(params)!=len(pairs) or set(params)-routes[parsed.path]:
                raise ValueError('Unknown or repeated query parameter')
            for name in ('limit','start','end'):
                if name in params:params[name]=int(params[name])
            if parsed.path=='/api/config':return self.reply(200,self.server.description)
            required='value' if parsed.path in ('/api/lookup','/api/neighbors') else 'evidence'
            if not params.get(required):raise ValueError('Missing required parameter: '+required)
            reader=DetailInspector(self.server.database)
            try:
                scope=dict(snapshot=self.server.snapshot,target=self.server.target)
                if parsed.path in ('/api/lookup','/api/neighbors'):
                    result=reader.page(**scope,operation=parsed.path[5:],**params)
                elif parsed.path=='/api/evidence':result=reader.evidence(**scope,**params)
                else:result=reader.source(**scope,roots=self.server.roots,**params)
            finally:reader.close()
            self.reply(200,result)
        except ValueError as error:
            self.reply(400,{'error':'invalid_query','message':str(error)[:300]})
        except (OSError,sqlite3.Error):
            self.reply(503,{'error':'inspection_unavailable','message':'Database/source unavailable or query work budget exceeded'})

    def do_POST(self):self.reply(405,{'error':'read_only'})
    do_PUT=do_POST
    do_PATCH=do_POST
    do_DELETE=do_POST
    do_HEAD=do_POST
    do_OPTIONS=do_POST


def main():
    p=argparse.ArgumentParser(description='Local read-only Atlas inspection API (127.0.0.1 only)')
    for key in ['database','snapshot','target']:p.add_argument('--'+key,required=True)
    p.add_argument('--repo-root');p.add_argument('--build-root');p.add_argument('--port',type=int,default=8765)
    a=p.parse_args()
    server=InspectionServer(database=a.database,snapshot=a.snapshot,target=a.target,port=a.port,
        roots={k:v for k,v in [('repo',a.repo_root),('build',a.build_root)] if v})
    # Local terminal only; never persist this per-process token or put it in URLs.
    print('Atlas local inspection: '+server.origin,flush=True)
    print('Authorization: Bearer '+server.token,flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
