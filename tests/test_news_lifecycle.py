import importlib.util, tempfile, shutil, threading, urllib.request, urllib.error, json, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
    target=Path(tmp)/'site'
    shutil.copytree(root,target,ignore=shutil.ignore_patterns('.git','.prototype_backups','.admin_backups','admin_config.json','.admin_password_for_local_testing.txt','__pycache__'))
    sys.path.insert(0, str(target))
    spec=importlib.util.spec_from_file_location('admin',target/'admin_server.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    m.DATA.write_text('[]')
    m.Handler.state=m.AdminState({'session_secret':'test-only'})
    sid=m.Handler.state.create_session(); csrf=m.Handler.state.sessions[sid]['csrf']
    server=m.ThreadingHTTPServer(('127.0.0.1',0),m.Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    cookie=f'wizytki_admin={m.Handler.state.sign(sid)}'
    def get(path):
        return urllib.request.urlopen(urllib.request.Request(base+path,headers={'Cookie':cookie})).read().decode()
    def post(fields,path='/dodaj/post',token=csrf):
        boundary='testboundary'
        fields=dict(fields,csrf=token)
        data=''.join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k,v in fields.items())+f'--{boundary}--\r\n'
        req=urllib.request.Request(base+path,data=data.encode(),headers={'Cookie':cookie,'Content-Type':f'multipart/form-data; boundary={boundary}'})
        return urllib.request.urlopen(req).read().decode()
    try:
        response=post({'title':'Draft test','date':'2026-10-21','body':'First paragraph\n\nSecond <text>','action':'draft'})
        item=json.loads(m.DATA.read_text())[0]; pid=item['id']; page=target/'public'/f'index.php?id=2&post={pid}.html'
        assert not item['published'] and not page.exists() and 'Szkic' in response
        assert 'Second &lt;text&gt;' in get('/dodaj?edit='+pid)
        post({'id':pid,'title':'Published test','date':'2026-10-21','body':'Published body','action':'publish'})
        assert page.exists() and 'Published body' in page.read_text()
        post({'id':pid,'title':'Edited title','date':'2026-10-20','body':'Edited body','action':'publish'})
        assert json.loads(m.DATA.read_text())[0]['id']==pid and 'Edited body' in page.read_text()
        index=target/'public'/'index.php?id=2&temat=0&str=1&cd=0.html'
        assert 'Edited title' in index.read_text()
        post({'id':pid,'title':'Edited title','date':'2026-10-20','body':'Edited body','action':'draft'})
        assert not page.exists() and 'Edited title' not in index.read_text()
        post({'id':pid,'title':'Again','date':'2026-10-20','body':'Body','action':'publish'})
        try: post({'id':pid},'/dodaj/delete',token='wrong')
        except urllib.error.HTTPError as e: assert e.code==403
        else: raise AssertionError('CSRF accepted')
        assert page.exists()
        post({'id':pid},'/dodaj/delete')
        assert not page.exists() and json.loads(m.DATA.read_text())==[]
        assert index.read_text().count('CLASS="news-list-row"')==24
        post({'title':'','date':'2026-10-21','body':'','action':'draft'})
        assert not json.loads(m.DATA.read_text())[0]['published']
        print('PASS: draft, editor, publish, edit with stable URL, unpublish, republish, CSRF rejection, delete, incomplete draft, 24 legacy items preserved')
    finally:
        server.shutdown();server.server_close()
