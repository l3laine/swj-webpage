"""Polish gallery management panel; authentication is supplied by admin_server."""
import html


def render_panel(data, csrf, css, message=''):
    esc = lambda value: html.escape(str(value), quote=True)
    token = f'<input type="hidden" name="csrf" value="{esc(csrf)}">'

    def options(selected=None):
        values = [(None, 'Bez sekcji')] + [(s['id'], s['name']) for s in data['sections']]
        return ''.join(f'<option value="{esc(key or "")}" {"selected" if key == selected else ""}>{esc(name)}</option>' for key, name in values)

    cards = []
    for image in data['images']:
        image_id = esc(image['id'])
        cards.append(f'''<article class="gallery-admin-card">
 <label class="gallery-choice"><input type="checkbox" name="ids" value="{image_id}" form="bulk-delete"> Zaznacz do usunięcia</label>
 <a href="/{esc(image['path'])}" target="_blank"><img src="/{esc(image['thumbnail'])}" alt="{esc(image['title'])}" loading="lazy"></a>
 <form method="post" action="/dodaj/galeria/edit">
  {token}<input type="hidden" name="id" value="{image_id}">
  <label>Tytuł<input name="title" value="{esc(image['title'])}" required></label>
  <label>Sekcja<select name="section_id">{options(image['section_id'])}</select></label>
  <button type="submit">Zapisz zmiany</button>
 </form>
 <form method="post" action="/dodaj/galeria/delete" onsubmit="return confirm('Usunąć to zdjęcie z galerii?');">
  {token}<input type="hidden" name="ids" value="{image_id}"><button class="danger" type="submit">Usuń zdjęcie</button>
 </form>
</article>''')
    sections = ''.join(f'''<li><span>{esc(s['name'])}</span>
 <form method="post" action="/dodaj/galeria/section-delete" onsubmit="return confirm('Usunąć sekcję? Zdjęcia pozostaną w galerii jako Bez sekcji.');">
  {token}<input type="hidden" name="section_id" value="{esc(s['id'])}"><button class="danger" type="submit">Usuń sekcję</button>
 </form></li>''' for s in data['sections'])
    notice = f'<p class="notice" role="status">{esc(message)}</p>' if message else ''
    return f'''<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Galeria — panel</title>{css}</head>
<body><main class="admin-shell">
 <header><h1>Galeria</h1><a href="/dodaj/wyloguj">Wyloguj</a></header>
 <nav class="admin-tabs" aria-label="Zarządzanie treścią"><a href="/dodaj">Aktualności</a><a href="/dodaj/galeria" aria-current="page">Galeria</a></nav>
 {notice}
 <section><h2>Dodaj zdjęcie</h2>
 <form method="post" action="/dodaj/galeria/add" enctype="multipart/form-data">
  {token}<label>Tytuł<input name="title" required></label>
  <label>Sekcja (opcjonalnie)<select name="section_id">{options()}</select></label>
  <label>Zdjęcie (JPG, PNG, GIF lub WebP, do 4 MB)<input name="image" type="file" accept="image/jpeg,image/png,image/gif,image/webp" required></label>
  <button type="submit">Dodaj zdjęcie</button>
 </form></section>
 <section><h2>Sekcje</h2>
 <form method="post" action="/dodaj/galeria/section-add">{token}<label>Nazwa nowej sekcji<input name="name" required></label><button type="submit">Dodaj sekcję</button></form>
 <ul class="gallery-sections">{sections or '<li>Brak sekcji.</li>'}</ul>
 <p>Usunięcie sekcji zachowuje jej zdjęcia w galerii jako „Bez sekcji”.</p></section>
 <section><h2>Zdjęcia ({len(data['images'])})</h2>
 <form id="bulk-delete" method="post" action="/dodaj/galeria/delete"
       onsubmit="const count=document.querySelectorAll('input[name=ids][form=bulk-delete]:checked').length; if(!count){{alert('Zaznacz zdjęcia do usunięcia.');return false;}} return confirm('Usunąć zaznaczone zdjęcia z galerii ('+count+')?');">
  {token}<button class="danger" type="submit">Usuń zaznaczone zdjęcia</button>
 </form>
 <div class="gallery-admin-grid">{''.join(cards) or '<p>Brak zdjęć w galerii.</p>'}</div>
 </section>
</main></body></html>'''
