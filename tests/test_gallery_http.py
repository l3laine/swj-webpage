"""End-to-end gallery admin checks; never alters the real site's data."""
import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

class GalleryHTTPTests(unittest.TestCase):
    def test_gallery_admin_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'site'
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('.git', '.prototype_backups', '.admin_backups', '__pycache__', 'admin_config.json', '.admin_password_for_local_testing.txt'))
            sys.path.insert(0, str(root))
            spec = importlib.util.spec_from_file_location('gallery_test_admin', root/'admin_server.py')
            admin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(admin)
            salt = b'test-salt'
            digest = hashlib.pbkdf2_hmac('sha256', b'test-password', salt, 1000)
            encoded = 'pbkdf2_sha256$1000$' + base64.urlsafe_b64encode(salt).decode() + '$' + base64.urlsafe_b64encode(digest).decode()
            admin.Handler.state = admin.AdminState({'username': 'test', 'password_hash': encoded, 'session_secret': 'testing'})
            server = admin.ThreadingHTTPServer(('127.0.0.1', 0), admin.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{server.server_port}'
            cookie = ''

            def request(path, fields=None, upload=None):
                headers = {'Cookie': cookie}
                body = None
                if fields is not None:
                    boundary = 'gallery-test-boundary'
                    body = b''
                    for key, value in fields:
                        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
                    if upload is not None:
                        body += f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="test.png"\r\nContent-Type: image/png\r\n\r\n'.encode() + upload + b'\r\n'
                    body += f'--{boundary}--\r\n'.encode()
                    headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
                return urllib.request.urlopen(urllib.request.Request(base+path, data=body, headers=headers))

            def data():
                return json.loads((root/'data/gallery.json').read_text())

            try:
                self.assertIn('Logowanie', request('/dodaj/galeria').read().decode())
                self.assertIn('Logowanie', request('/dodaj/galeria/delete', [('ids', 'legacy-1')]).read().decode())
                login = urllib.request.urlopen(urllib.request.Request(base+'/dodaj/login', data=urllib.parse.urlencode({'username':'test', 'password':'test-password'}).encode()))
                # Login redirects normally; obtain the issued session from server state.
                self.assertEqual(len(admin.Handler.state.sessions), 1)
                sid = next(iter(admin.Handler.state.sessions))
                cookie = 'wizytki_admin=' + admin.Handler.state.sign(sid)
                csrf = admin.Handler.state.sessions[sid]['csrf']
                self.assertIn('Aktualności', request('/dodaj/galeria').read().decode())
                self.assertIn('/dodaj/galeria', request('/dodaj').read().decode())
                count = len(data()['images'])
                for action in ['add', 'edit', 'delete', 'section-add', 'section-delete']:
                    with self.assertRaises(urllib.error.HTTPError) as failure:
                        request('/dodaj/galeria/'+action, [('csrf', 'invalid')])
                    self.assertEqual(failure.exception.code, 403)
                request('/dodaj/galeria/section-add', [('csrf', csrf), ('name', 'Nowa <sekcja>')])
                section = data()['sections'][-1]['id']
                stream = io.BytesIO()
                Image.new('RGB', (80, 60), 'blue').save(stream, format='PNG')
                image_bytes = stream.getvalue()
                invalid = request('/dodaj/galeria/add', [('csrf', csrf), ('title',''), ('section_id',section)], image_bytes).read().decode()
                self.assertIn('Tytuł zdjęcia jest wymagany', invalid)
                self.assertEqual(len(data()['images']), count)
                ids = []
                for name in ['Pierwsze zdjęcie', 'Drugie zdjęcie', 'Trzecie zdjęcie']:
                    request('/dodaj/galeria/add', [('csrf', csrf), ('title',name), ('section_id',section)], image_bytes)
                    ids.append(data()['images'][-1]['id'])
                request('/dodaj/galeria/edit', [('csrf',csrf), ('id',ids[0]), ('title','Nowy <tytuł>'), ('section_id',section)])
                page = '/index.php%3Fid=11&temat=1&str=1&cd=0.html'
                rendered = request(page)
                self.assertEqual(rendered.headers['Cache-Control'], 'no-store')
                self.assertIn('Nowy &lt;tytuł&gt;', rendered.read().decode())
                request('/dodaj/galeria/section-delete', [('csrf',csrf), ('section_id',section)])
                self.assertEqual(len(data()['images']), count+3)
                self.assertTrue(all(i['section_id'] is None for i in data()['images'] if i['id'] in ids))
                self.assertIn('Bez sekcji', request(page).read().decode())
                request('/dodaj/galeria/delete', [('csrf',csrf), ('ids',ids[0])])
                self.assertEqual(len(data()['images']), count+2)
                request('/dodaj/galeria/delete', [('csrf',csrf), ('ids',ids[1]), ('ids',ids[2])])
                self.assertEqual(len(data()['images']), count)
                self.assertNotIn('Nowy &lt;tytuł&gt;', request(page).read().decode())
                # Existing imported images are editable too.
                imported = data()['images'][0]
                request('/dodaj/galeria/edit', [('csrf',csrf), ('id',imported['id']), ('title','Imported edited'), ('section_id',imported['section_id'])])
                self.assertIn('Imported edited', request(page).read().decode())
            finally:
                server.shutdown()
                server.server_close()
                sys.path.remove(str(root))

if __name__ == '__main__': unittest.main()
