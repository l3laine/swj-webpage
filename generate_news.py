#!/usr/bin/env python3
import html
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
DATA = ROOT / "data" / "news.json"
LEGACY_PAGE = ROOT / "data" / "legacy_aktualnosci_page1.html"
LEGACY_PAGES = ROOT / "data" / "legacy_aktualnosci_pages"
BACKUPS = ROOT / ".admin_backups"
THUMBS = PUBLIC / "Aktualnosci" / "thumbs"
THUMB_SIZE = (112, 78)
LEGACY_POST_COUNT = 24
GENERATED_PREFIX = "index.php?id=2&post="
INDEX_VARIANTS = [
    PUBLIC / "index.php?id=2&temat=0&str=1&cd=0.html",
    PUBLIC / "index.php?id=2&str=1&temat=0&cd=0.html",
]
LEGACY_SOURCE_FILES = [LEGACY_PAGES / f"page-{page}.html" for page in range(1, LEGACY_POST_COUNT + 1)]


def write_text_atomic(path: Path, content: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def backup_targets() -> None:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUPS / f"news_generate_{stamp}"
    dest.mkdir(parents=True, exist_ok=True)
    for target in PUBLIC.glob("index.php?id=2*"):
        if target.exists():
            shutil.copy2(target, dest / target.name)


def strip_tags(value: str) -> str:
    value = re.sub(r"<script\b.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def remove_legacy_continuation(content: str) -> str:
    return re.sub(r'<FONT[^>]*>\s*<P>\s*<B>\s*ciąg dalszy\s*\.\.\.\s*</B>\s*</P>\s*</FONT>\s*<BR>\s*', "", content, flags=re.I)


def extract_content(page_html: str) -> str:
    title = re.search(r'<P ALIGN="?center"?><B>AKTUALNOŚCI</B></P>', page_html, flags=re.I)
    if not title:
        raise RuntimeError("Could not find Aktualności heading.")
    font = re.search(r'<FONT COLOR="#202020" SIZE="2">\s*(.*?)\s*</FONT>', page_html[title.end():], flags=re.I | re.S)
    if not font:
        raise RuntimeError("Could not find Aktualności content block.")
    return remove_legacy_continuation(font.group(1)).strip()


def first_image(content: str) -> str:
    match = re.search(r'<IMG[^>]+SRC="([^"]+)"', content, flags=re.I)
    return html.unescape(match.group(1)) if match else ""


def thumbnail_name(image: str, post_id: str) -> str:
    suffix = Path(image).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        suffix = ".jpg"
    if suffix == ".jpeg":
        suffix = ".jpg"
    return f"{re.sub(r'[^a-zA-Z0-9_-]+', '-', post_id).strip('-')}{suffix}"


def generate_thumbnail(image: str, post_id: str) -> str:
    if not image:
        return ""
    source = PUBLIC / html.unescape(image)
    if not source.exists() or not source.is_file():
        return image
    THUMBS.mkdir(parents=True, exist_ok=True)
    target = THUMBS / thumbnail_name(image, post_id)
    with Image.open(source) as original:
        converted = ImageOps.exif_transpose(original).convert("RGB")
        thumb = ImageOps.fit(converted, THUMB_SIZE, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        thumb.save(target, quality=82, optimize=True)
    return str(target.relative_to(PUBLIC))


def excerpt(content: str) -> str:
    text = strip_tags(content)
    words = text.split()
    return " ".join(words[:44]) + (" ..." if len(words) > 44 else "")


def legacy_title(index: int, content: str) -> str:
    text = strip_tags(content)
    date_match = re.search(r"\b\d{1,2}\s+[a-ząćęłńóśżź]+\s+\d{4}\s*r?\.?", text, flags=re.I)
    if date_match:
        return date_match.group(0)
    bold = re.search(r"<B>(.*?)</B>", content, flags=re.I | re.S)
    if bold:
        return strip_tags(bold.group(1))[:80]
    return ""


def admin_posts() -> list[dict]:
    if not DATA.exists():
        return []
    posts = json.loads(DATA.read_text(encoding="utf-8"))
    posts = [post for post in posts if post.get("published", True)]
    return sorted(posts, key=lambda item: (item.get("date", ""), item.get("created_at", "")), reverse=True)


def load_posts() -> list[dict]:
    posts = []
    for post in admin_posts():
        title = post.get("title", "").strip() or post.get("date", "").strip() or "Aktualność"
        body = post.get("body", "")
        images = post.get("images", [])
        content = "\n".join([
            *(f'<P ALIGN="center"><A HREF="{html.escape(image, quote=True)}" TARGET="_blank"><IMG WIDTH="364" BORDER="0" SRC="{html.escape(image, quote=True)}"></A></P>' for image in images),
            f'<P ALIGN="justify"><B>{html.escape(post.get("date", ""))}</B> - <B>{html.escape(title)}</B></P>',
            f'<DIV CLASS="news-post-body">{body}</DIV>',
        ])
        posts.append({
            "id": post.get("id", title),
            "title": title,
            "content": content,
            "image": images[0] if images else first_image(body),
            "excerpt": excerpt(content),
            "href": f"index.php%3Fid=2&amp;post={html.escape(post.get('id', title), quote=True)}.html",
            "target": PUBLIC / f"index.php?id=2&post={post.get('id', title)}.html",
        })

    for index, source in enumerate(LEGACY_SOURCE_FILES, start=1):
        if not source.exists():
            continue
        content = extract_content(source.read_text(encoding="utf-8"))
        posts.append({
            "id": f"legacy-{index}",
            "title": legacy_title(index, content),
            "content": content,
            "image": first_image(content),
            "excerpt": excerpt(content),
            "href": f"index.php%3Fid=2&amp;post=legacy-{index}.html",
            "target": PUBLIC / f"index.php?id=2&post=legacy-{index}.html",
        })
    for post in posts:
        try:
            post["thumbnail"] = generate_thumbnail(post.get("image", ""), post["id"])
        except OSError:
            post["thumbnail"] = post.get("image", "")
    return posts


def replace_news_table(template: str, table: str) -> str:
    marker = re.search(r'<TABLE WIDTH="100%" HEIGHT="100%" CELLSPACING="0" CELLPADDING="0" border="0">', template)
    if not marker:
        raise RuntimeError("Could not find Aktualności table start.")
    table_tag = re.compile(r"</?TABLE\b[^>]*>", flags=re.I)
    depth = 0
    for match in table_tag.finditer(template, marker.start()):
        tag = match.group(0).lower()
        if tag.startswith("<table"):
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return template[:marker.start()] + table + template[match.end():]
    raise RuntimeError("Could not find matching Aktualności table end.")


def render_index(posts: list[dict]) -> str:
    rows = []
    for post in posts:
        thumb = post.get("thumbnail") or post["image"]
        thumb_html = f'<IMG SRC="{html.escape(thumb, quote=True)}" ALT="">' if thumb else '<SPAN></SPAN>'
        title_html = f'<SPAN CLASS="news-list-title">{html.escape(post["title"])}</SPAN>' if post["title"] else ""
        rows.append(f"""       <A CLASS="news-list-row" HREF="{post['href']}">
        <SPAN CLASS="news-list-thumb">{thumb_html}</SPAN>
        <SPAN CLASS="news-list-text">
         {title_html}
         <SPAN CLASS="news-list-excerpt">{html.escape(post['excerpt'])}</SPAN>
        </SPAN>
       </A>""")
    body = "\n".join(rows) if rows else '       <P ALIGN="center">Brak aktualności.</P>'
    return f"""<TABLE WIDTH="100%" HEIGHT="100%" CELLSPACING="0" CELLPADDING="0" border="0">
  <TR height="620">
   <TD VALIGN="top">
     <P ALIGN="center"><B>AKTUALNOŚCI</B></P>
     <DIV CLASS="news-list">
{body}
     </DIV>
   </TD>
  </TR>
 </TABLE>"""


def render_detail(post: dict) -> str:
    heading = f'<P ALIGN="center"><B>{html.escape(post["title"])}</B></P>' if post["title"] else ""
    return f"""<TABLE WIDTH="100%" HEIGHT="100%" CELLSPACING="0" CELLPADDING="0" border="0">
  <TR height="620">
   <TD VALIGN="top">
     {heading}
     <P ALIGN="center"><A CLASS="news-back-link" HREF="index.php%3Fid=2&amp;temat=0&amp;str=1&amp;cd=0.html">Powrót do aktualności</A></P>
     <FONT COLOR="#202020" SIZE="2">
{post['content']}
     </FONT>
   </TD>
  </TR>
 </TABLE>"""


def generate() -> None:
    if not LEGACY_PAGE.exists():
        raise RuntimeError("Missing data/legacy_aktualnosci_page1.html")
    template = LEGACY_PAGE.read_text(encoding="utf-8")
    posts = load_posts()
    backup_targets()
    index_html = replace_news_table(template, render_index(posts))
    for target in INDEX_VARIANTS:
        write_text_atomic(target, index_html)
    for post in posts:
        write_text_atomic(post["target"], replace_news_table(template, render_detail(post)))
    for page in range(2, LEGACY_POST_COUNT + 1):
        source = PUBLIC / f"index.php?id=2&post=legacy-{page}.html"
        target = PUBLIC / f"index.php?id=2&str={page}&temat=0&cd=1.html"
        if source.exists():
            shutil.copy2(source, target)
    keep = {post["target"].name for post in posts}
    for generated in PUBLIC.iterdir():
        if generated.name.startswith(GENERATED_PREFIX) and generated.name.endswith(".html") and generated.name not in keep:
            generated.unlink()


if __name__ == "__main__":
    generate()
