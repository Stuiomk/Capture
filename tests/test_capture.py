import json
import os
import struct
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from site_capture.urls import normalize, candidate, origin, filename
from site_capture.capture import new_folder, run_capture

class UrlTests(unittest.TestCase):
    def test_origin_and_queries(self):
        self.assertEqual(normalize('HTTPS://Example.COM:443/a?id=2#x'),'https://example.com/a')
        self.assertEqual(origin('https://example.com:443/'),origin('https://example.com/'))
        for u in ['file:///tmp/a','javascript:alert(1)','https://u:p@example.com','https://example.com:bad/']:
            with self.assertRaises(ValueError): normalize(u)
    def test_external_and_assets(self):
        base='https://example.com/a/'
        for href in ['https://other.com/','//sub.example.com/','/a.pdf','mailto:a@example.com']:
            self.assertIsNone(candidate(base,href,origin(base)))
        self.assertEqual(candidate(base,'../b?q=1#x',origin(base)), 'https://example.com/b')
    def test_output_collision(self):
        with tempfile.TemporaryDirectory() as d:
            a=new_folder(d,'https://example.com');b=new_folder(d,'https://example.com')
            self.assertNotEqual(a,b)
        self.assertEqual(filename('https://example.com/CON'),'_CON')
    def test_invalid_options(self):
        with self.assertRaises(ValueError):run_capture('https://example.com',[],11,'/unused',lambda e:None,threading.Event())

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/bad':self.send_response(500);self.end_headers();return
        if self.path=='/redirect':self.send_response(302);self.send_header('Location','/second');self.end_headers();return
        if self.path=='/outside':self.send_response(302);self.send_header('Location','http://127.0.0.1:1/');self.end_headers();return
        self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers()
        self.wfile.write(b'''<meta name="viewport" content="width=device-width, initial-scale=1"><style>body{margin:0}.long{height:2100px;background:#eef}</style><a href="/second">second</a><a href="/redirect">duplicate</a><a href="/bad">error</a><a href="/outside">outside redirect</a><a href="https://example.org">external</a><a href="/file.pdf">pdf</a><div class="long">SiteCapture test</div><script>setTimeout(()=>{let a=document.createElement('a');a.href='/dynamic';a.textContent='dynamic';document.body.append(a)},100)</script>''')
    def log_message(self,*args):pass

@unittest.skipUnless(os.environ.get('SITECAPTURE_INTEGRATION')=='1','Chrome integration: set SITECAPTURE_INTEGRATION=1')
class BrowserTests(unittest.TestCase):
    def test_real_capture(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as d:
                folder,log=run_capture(f'http://127.0.0.1:{server.server_port}/',['PC','Mobile'],6,d,lambda e:None,threading.Event())
                self.assertEqual(len(log['pages']),6)
                self.assertTrue(any('/dynamic' in r['url'] for r in log['pages']))
                bad=next(r for r in log['pages'] if r['url'].endswith('/bad'))
                self.assertEqual(len(bad['errors']),2)
                outside=next(r for r in log['pages'] if r['url'].endswith('/outside'))
                self.assertFalse(outside['files']);self.assertEqual(len(outside['errors']),2)
                duplicate=next(r for r in log['pages'] if r['url'].endswith('/redirect'))
                self.assertIn('duplicate_of',duplicate)
                self.assertFalse(duplicate['files'])
                for mode,width in [('PC',1440),('Mobile',390)]:
                    data=(folder/log['pages'][0]['files'][mode]).read_bytes()
                    self.assertEqual(data[:8],b'\x89PNG\r\n\x1a\n')
                    w,h=struct.unpack('>II',data[16:24]);self.assertEqual(w,width);self.assertGreater(h,2100)
                self.assertEqual(json.loads((folder/'capture-log.json').read_text())['input_url'],log['input_url'])
        finally:server.shutdown();server.server_close();thread.join()

class StartupTests(unittest.TestCase):
    def test_browser_failure_leaves_log(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            with patch('site_capture.capture.launch_browser',side_effect=RuntimeError('Chrome missing')):
                with self.assertRaisesRegex(RuntimeError,'Chrome missing'):
                    run_capture('https://example.com',['PC'],1,d,lambda e:None,threading.Event())
            logs=list(Path(d).glob('*/capture-log.json'))
            self.assertEqual(len(logs),1)
            self.assertEqual(json.loads(logs[0].read_text())['startup_error'],'Chrome missing')
