"""Loopback endpoints expose only the rendered dashboard and aggregate data."""
import json
import sys
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from smallgalaxy import dashboard_server


class ServerTests(unittest.TestCase):
    def test_routes(self):
        with tempfile.TemporaryDirectory(prefix='galaxy-server-test-') as tmp:
            page=Path(tmp)/'dashboard.html'
            page.write_text('<script>\nlet DATA = {"days": []};\n</script>')
            with patch.object(dashboard_server,'PAGE',page):
                server=ThreadingHTTPServer(('127.0.0.1',0),dashboard_server.Handler)
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                try:
                    def get(path,host=None):
                        conn=HTTPConnection('127.0.0.1',server.server_port,timeout=2)
                        conn.request('GET',path,headers={'Host':host} if host else {})
                        response=conn.getresponse();body=response.read();status=response.status
                        conn.close();return status,body
                    self.assertEqual(get('/health'),(200,dashboard_server.IDENTITY))
                    status,data=get('/data');self.assertEqual(status,200);self.assertEqual(json.loads(data),{'days':[]})
                    self.assertEqual(get('/')[0],200)
                    self.assertEqual(get('/logs/2026-09-08.csv')[0],404)
                    self.assertEqual(get('/../../etc/passwd')[0],404)
                    self.assertEqual(get('/data','untrusted.example')[0],403)
                finally:
                    server.shutdown();server.server_close();thread.join()

    def test_music_library_serves_only_its_own_audio(self):
        with tempfile.TemporaryDirectory(prefix='galaxy-music-test-') as tmp:
            music=Path(tmp)/'music';music.mkdir()
            (music/'quiet song.mp3').write_bytes(b'ID3fake-audio')
            (music/'notes.txt').write_bytes(b'not audio')
            (Path(tmp)/'secret.mp3').write_bytes(b'outside the library')
            with patch.object(dashboard_server,'MUSIC_DIR',music):
                names=[track['name'] for track in dashboard_server.list_music()]
                self.assertEqual(names,['quiet song.mp3'])  # non-audio is skipped
                self.assertEqual(dashboard_server.resolve_track('quiet song.mp3').read_bytes(),b'ID3fake-audio')
                for attack in ('../secret.mp3','..','','/etc/passwd','sub/song.mp3','notes.txt','song.mp3'):
                    with self.assertRaises(ValueError,msg=attack):
                        dashboard_server.resolve_track(attack)

    def test_music_endpoints(self):
        with tempfile.TemporaryDirectory(prefix='galaxy-music-http-') as tmp:
            music=Path(tmp)/'music';music.mkdir()
            (music/'a song.mp3').write_bytes(b'ID3payload')
            page=Path(tmp)/'dashboard.html';page.write_text('<script>\nlet DATA = {"days": []};\n</script>')
            with patch.object(dashboard_server,'PAGE',page),patch.object(dashboard_server,'MUSIC_DIR',music):
                server=ThreadingHTTPServer(('127.0.0.1',0),dashboard_server.Handler)
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                try:
                    def get(path):
                        conn=HTTPConnection('127.0.0.1',server.server_port,timeout=2)
                        conn.request('GET',path);response=conn.getresponse()
                        result=(response.status,response.read(),response.getheader('Content-Type'))
                        conn.close();return result
                    status,body,_=get('/music')
                    self.assertEqual(status,200)
                    self.assertEqual([t['name'] for t in json.loads(body)],['a song.mp3'])
                    status,body,mime=get('/music/a%20song.mp3')
                    self.assertEqual((status,body,mime),(200,b'ID3payload','audio/mpeg'))
                    self.assertEqual(get('/music/../dashboard.html')[0],404)
                    self.assertEqual(get('/music/%2e%2e%2fdashboard.html')[0],404)
                    self.assertEqual(get('/music/missing.mp3')[0],404)
                finally:
                    server.shutdown();server.server_close();thread.join()
