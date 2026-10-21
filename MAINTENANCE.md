# Prototype Maintenance Notes

## Public Site

The public site in `public/` is still mostly imported legacy HTML. Many pages use table layout and old inline attributes. Avoid broad hand refactors across all imported pages unless you can verify the affected pages in a browser afterward.

The prototype visual layer is centralized in:

- `public/responsive-legacy.css`
- `public/responsive-legacy.js`

Those files adapt the legacy tables into the current prototype layout. They intentionally contain some legacy-table selectors because the imported HTML has no semantic layout classes.

## Aktualnosci

`Aktualnosci` is generated. Do not hand-edit these generated files:

- `public/index.php?id=2&temat=0&str=1&cd=0.html`
- `public/index.php?id=2&str=1&temat=0&cd=0.html`
- `public/index.php?id=2&post=*.html`
- `public/index.php?id=2&str=2&temat=0&cd=1.html` through `str=24`
- `public/Aktualnosci/thumbs/*`

The source files are:

- `data/news.json` for posts added through `/dodaj`
- `data/legacy_aktualnosci_pages/page-*.html` for imported legacy posts
- `generate_news.py` for rebuilding the index, detail pages, and thumbnails

Run this after changing news data or the generator:

```sh
python3 generate_news.py
```

## Admin

The local admin panel is served by:

```sh
python3 admin_server.py
```

It exposes `/dodaj`, writes new posts to `data/news.json`, stores uploaded images in `public/Aktualnosci/`, and calls `generate_news.py`.

Secrets are intentionally local and ignored by git:

- `admin_config.json`
- `.admin_password_for_local_testing.txt`

For production, serve the admin over HTTPS only.

## Verification

Minimum checks after changes:

```sh
python3 -m py_compile admin_server.py generate_news.py setup_admin.py
python3 generate_news.py
```

Then verify:

- `Aktualnosci` index has 24 legacy rows plus any admin posts.
- Generated thumbnails are `112x78`.
- Representative pages have balanced table, row, and cell counts.
- `/dodaj` login and post creation still work.

## News editing and drafts

At `/dodaj`, use **Edytuj** to modify a panel-created post, **Zapisz szkic** to
save an incomplete post privately or withdraw a published post, and **Opublikuj**
to publish. All panel-created posts and drafts appear in the list. **Usuń** asks
for confirmation before deleting a post. Existing photos are retained on edit;
new photos are appended. Article URLs remain stable when titles or dates change.
Imported legacy news remains managed through its source HTML, outside this panel.

Drafts and deleted posts have no generated public article page. Uploaded images
are retained on disk, including after withdrawal or deletion; draft attachments
are not private files if their public URL is known.

Run the isolated HTTP lifecycle regression check (uses a temporary site copy):

```sh
python3 tests/test_news_lifecycle.py
```
