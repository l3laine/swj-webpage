#!/usr/bin/env python3
import base64
import cgi
import hashlib
import hmac
import html
import http.cookies
import json
import os
import re
import secrets
import shutil
import subprocess
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse


ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
CONFIG = ROOT / "admin_config.json"
DATA = ROOT / "data" / "news.json"
UPLOAD_DIR = PUBLIC / "Aktualnosci"
MAX_IMAGE_BYTES = 4 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_config() -> dict:
    if not CONFIG.exists():
        raise SystemExit("Missing admin_config.json. Run: python3 setup_admin.py")
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, digest = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            base64.urlsafe_b64decode(salt.encode("ascii")),
            int(iterations),
        )
        return hmac.compare_digest(expected, base64.urlsafe_b64decode(digest.encode("ascii")))
    except (TypeError, ValueError):
        return False


def slugify(value: str) -> str:
    value = value.lower()
    value = value.replace("ą", "a").replace("ć", "c").replace("ę", "e").replace("ł", "l")
    value = value.replace("ń", "n").replace("ó", "o").replace("ś", "s").replace("ż", "z").replace("ź", "z")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or secrets.token_hex(4)


def paragraphs_to_html(value: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", value.strip()) if part.strip()]
    return "\n".join(f"<p>{html.escape(part).replace(chr(10), '<br>')}</p>" for part in paragraphs)


class AdminState:
    def __init__(self, config: dict):
        self.config = config
        self.sessions: dict[str, dict] = {}

    @property
    def secret(self) -> bytes:
        return self.config["session_secret"].encode("utf-8")

    def sign(self, value: str) -> str:
        digest = hmac.new(self.secret, value.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{value}.{digest}"

    def unsign(self, value: str) -> str | None:
        if "." not in value:
            return None
        raw, digest = value.rsplit(".", 1)
        expected = hmac.new(self.secret, raw.encode("utf-8"), hashlib.sha256).hexdigest()
        if hmac.compare_digest(digest, expected):
            return raw
        return None

    def create_session(self) -> str:
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {
            "created": time.time(),
            "csrf": secrets.token_urlsafe(32),
        }
        return session_id

    def get_session(self, cookie_header: str | None) -> dict | None:
        if not cookie_header:
            return None
        cookies = http.cookies.SimpleCookie(cookie_header)
        morsel = cookies.get("wizytki_admin")
        if not morsel:
            return None
        session_id = self.unsign(morsel.value)
        if not session_id:
            return None
        session = self.sessions.get(session_id)
        if not session:
            return None
        if time.time() - session["created"] > 12 * 60 * 60:
            self.sessions.pop(session_id, None)
            return None
        return session

    def destroy_session(self, cookie_header: str | None) -> None:
        if not cookie_header:
            return
        cookies = http.cookies.SimpleCookie(cookie_header)
        morsel = cookies.get("wizytki_admin")
        if morsel:
            session_id = self.unsign(morsel.value)
            if session_id:
                self.sessions.pop(session_id, None)


class Handler(SimpleHTTPRequestHandler):
    state: AdminState

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        relative = unquote(parsed.path).lstrip("/") or "index.html"
        return str(PUBLIC / relative)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/dodaj", "/dodaj/"):
            session = self.state.get_session(self.headers.get("Cookie"))
            if session:
                post_id = parse_qs(parsed.query).get("edit", [""])[0]
                posts = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else []
                post = next((item for item in posts if item["id"] == post_id), None)
                if post_id and post is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self.render_panel(session, post=post)
            else:
                self.render_login()
            return
        if parsed.path == "/dodaj/wyloguj":
            self.state.destroy_session(self.headers.get("Cookie"))
            self.redirect("/dodaj", clear_cookie=True)
            return
        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/dodaj/login":
            self.handle_login()
            return
        if parsed.path in ("/dodaj/post", "/dodaj/delete"):
            self.handle_post()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def read_urlencoded(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        return {key: values[0] for key, values in parse_qs(body).items()}

    def handle_login(self) -> None:
        form = self.read_urlencoded()
        if (
            form.get("username") == self.state.config["username"]
            and verify_password(form.get("password", ""), self.state.config["password_hash"])
        ):
            session_id = self.state.create_session()
            self.redirect("/dodaj", session_id=session_id)
            return
        self.render_login("Nieprawidłowy użytkownik lub hasło.")

    def handle_post(self) -> None:
        session = self.state.get_session(self.headers.get("Cookie"))
        if not session:
            self.redirect("/dodaj")
            return

        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
        })
        if form.getfirst("csrf") != session["csrf"]:
            self.send_error(HTTPStatus.FORBIDDEN, "Invalid CSRF token")
            return

        posts = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else []
        post_id = form.getfirst("id", "")
        existing = next((post for post in posts if post["id"] == post_id), None)
        if post_id and existing is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if urlparse(self.path).path == "/dodaj/delete":
            if existing is None:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            posts.remove(existing)
        else:
            title = form.getfirst("title", "").strip()
            date = form.getfirst("date", "").strip()
            body = form.getfirst("body", "").strip()
            published = form.getfirst("action") == "publish"
            submitted = dict(existing or {}, title=title, date=date, body_text=body)
            try:
                datetime.strptime(date, "%Y-%m-%d")
                if published and (not title or not body):
                    raise ValueError("Do publikacji wymagane są tytuł i treść.")
                images = self.save_uploads(form, date, title)
            except ValueError as error:
                self.render_panel(session, str(error), post=submitted)
                return
            now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
            post = dict(existing or {})
            post.update({
                "id": post_id or f"{date}-{slugify(title)}-{secrets.token_hex(4)}",
                "date": date, "title": title, "body_text": body,
                "body": paragraphs_to_html(body),
                "images": list((existing or {}).get("images", [])) + images,
                "published": published,
                "created_at": (existing or {}).get("created_at", now), "updated_at": now,
            })
            if existing is None:
                posts.insert(0, post)
            else:
                posts[posts.index(existing)] = post
        write_json_atomic(DATA, posts)
        try:
            subprocess.run(["python3", str(ROOT / "generate_news.py")], check=True, cwd=ROOT)
        except (subprocess.CalledProcessError, OSError):
            self.render_panel(session, "Zmiany zapisano, ale przebudowanie strony nie powiodło się. Sprawdź generate_news.py.")
            return
        self.redirect("/dodaj")

    def save_uploads(self, form: cgi.FieldStorage, date: str, title: str) -> list[str]:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        items = form["images"] if "images" in form else []
        if not isinstance(items, list):
            items = [items]
        saved = []
        base = f"{date}-{slugify(title)}-{secrets.token_hex(6)}"
        for index, item in enumerate(items, start=1):
            if not getattr(item, "filename", ""):
                continue
            data = item.file.read(MAX_IMAGE_BYTES + 1)
            if len(data) > MAX_IMAGE_BYTES:
                raise ValueError("Przesłany obraz jest za duży. Maksymalny rozmiar to 4 MB.")
            content_type = item.type or ""
            extension = ALLOWED_IMAGE_TYPES.get(content_type)
            if not extension:
                extension = Path(item.filename).suffix.lower()
                if extension not in ALLOWED_IMAGE_TYPES.values():
                    raise ValueError("Nieobsługiwany typ obrazu. Dozwolone są JPG, PNG, GIF i WebP.")
            filename = f"{base}-{index}{extension}"
            target = UPLOAD_DIR / filename
            target.write_bytes(data)
            saved.append(f"Aktualnosci/{filename}")
        return saved

    def render_login(self, error: str = "") -> None:
        message = f'<p class="error">{html.escape(error)}</p>' if error else ""
        self.send_html(f"""<!doctype html>
<html lang="pl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Logowanie</title>{ADMIN_CSS}</head>
<body>
 <main class="admin-card">
  <h1>Dodaj aktualność</h1>
  {message}
  <form method="post" action="/dodaj/login">
   <label>Użytkownik<input name="username" autocomplete="username" required></label>
   <label>Hasło<input name="password" type="password" autocomplete="current-password" required></label>
   <button type="submit">Zaloguj</button>
  </form>
 </main>
</body>
</html>""")

    def render_panel(self, session: dict, message: str = "", post: dict | None = None) -> None:
        posts = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else []
        post = post or {}
        esc = lambda value: html.escape(str(value), quote=True)
        csrf = esc(session["csrf"])
        body = post.get("body_text")
        if body is None:
            body = re.sub(r"<br\s*/?>", "\n", post.get("body", ""), flags=re.I)
            body = re.sub(r"</p>\s*<p>", "\n\n", body, flags=re.I)
            body = html.unescape(re.sub(r"<[^>]*>", "", body))
        rows = []
        for item in posts:
            status = "Opublikowany" if item.get("published", True) else "Szkic"
            rows.append(f'''<li><strong>{esc(item.get('title') or 'Bez tytułu')}</strong>
                — {esc(item.get('date', ''))} — {status}
                <a href="/dodaj?edit={quote(item['id'], safe='')}">Edytuj</a>
                <form method="post" action="/dodaj/delete" enctype="multipart/form-data"
                      onsubmit="return confirm('Usunąć ten wpis? Tej operacji nie można cofnąć w panelu.');">
                 <input type="hidden" name="csrf" value="{csrf}">
                 <input type="hidden" name="id" value="{esc(item['id'])}">
                 <button type="submit">Usuń</button>
                </form></li>''')
        images = "".join(f'<li><a href="/{esc(image)}" target="_blank">{esc(Path(image).name)}</a></li>' for image in post.get("images", []))
        notice = f'<p class="notice">{esc(message)}</p>' if message else ""
        heading = "Edytuj aktualność" if post.get("id") else "Dodaj aktualność"
        self.send_html(f'''<!doctype html>
<html lang="pl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Aktualności — panel</title>{ADMIN_CSS}</head>
<body><main class="admin-shell">
 <header><h1>{heading}</h1><a href="/dodaj/wyloguj">Wyloguj</a></header>
 <p><a href="/dodaj">Nowa aktualność</a></p>
 {notice}
 <form method="post" action="/dodaj/post" enctype="multipart/form-data" class="editor">
  <input type="hidden" name="csrf" value="{csrf}">
  <input type="hidden" name="id" value="{esc(post.get('id', ''))}">
  <label>Tytuł<input name="title" value="{esc(post.get('title', ''))}"></label>
  <label>Data<input name="date" type="date" value="{esc(post.get('date', datetime.now().date().isoformat()))}" required></label>
  <label>Treść<textarea name="body" rows="14">{esc(body)}</textarea></label>
  {('<p>Zapisane zdjęcia (zostaną zachowane):</p><ul>' + images + '</ul>') if images else ''}
  <label>Dodaj zdjęcia<input name="images" type="file" accept="image/*" multiple></label>
  <p>Szkice nie są widoczne na stronie. Zapis opublikowanego wpisu jako szkic wycofuje go z publikacji.</p>
  <button type="submit" name="action" value="draft">Zapisz szkic</button>
  <button type="submit" name="action" value="publish">{'Zapisz i opublikuj' if post.get('id') else 'Opublikuj'}</button>
 </form>
 <section><h2>Wpisy i szkice</h2><ol>{''.join(rows) or '<li>Brak wpisów.</li>'}</ol></section>
</main></body></html>''')

    def send_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, location: str, session_id: str | None = None, clear_cookie: bool = False) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        if session_id:
            cookie = http.cookies.SimpleCookie()
            cookie["wizytki_admin"] = self.state.sign(session_id)
            cookie["wizytki_admin"]["httponly"] = True
            cookie["wizytki_admin"]["samesite"] = "Strict"
            cookie["wizytki_admin"]["path"] = "/dodaj"
            self.send_header("Set-Cookie", cookie.output(header="").strip())
        if clear_cookie:
            self.send_header("Set-Cookie", "wizytki_admin=; Path=/dodaj; Max-Age=0; HttpOnly; SameSite=Strict")
        self.end_headers()


ADMIN_CSS = """<style>
body { margin: 0; min-height: 100vh; display: grid; place-items: center; font: 16px/1.45 system-ui, sans-serif; background: #f6f2ec; color: #211b12; }
.admin-card, .admin-shell { width: min(920px, calc(100vw - 32px)); background: white; border: 1px solid #e4d8c8; border-radius: 8px; box-shadow: 0 20px 55px rgb(40 31 18 / 12%); padding: 28px; }
.admin-shell { margin: 32px 0; }
header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
h1, h2 { margin: 0 0 18px; font-weight: 500; }
form { display: grid; gap: 16px; }
label { display: grid; gap: 6px; font-weight: 600; }
input, textarea { font: inherit; border: 1px solid #cdbfae; border-radius: 6px; padding: 10px 12px; }
textarea { resize: vertical; }
button { justify-self: start; border: 0; border-radius: 999px; background: #1f5f8d; color: white; padding: 10px 20px; font: inherit; cursor: pointer; }
a { color: #1f5f8d; }
.notice { border: 1px solid #b8d5bf; background: #eef8f0; padding: 10px 12px; border-radius: 6px; }
.error { border: 1px solid #dfb3a8; background: #fff0ed; padding: 10px 12px; border-radius: 6px; }
ol { padding-left: 22px; }
</style>"""


def main() -> None:
    config = load_config()
    Handler.state = AdminState(config)
    server = ThreadingHTTPServer((config.get("host", "127.0.0.1"), int(config.get("port", 8021))), Handler)
    print(f"Serving public site and /dodaj admin at http://{config.get('host', '127.0.0.1')}:{config.get('port', 8021)}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
