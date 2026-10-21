"""Gallery data, one-time legacy import, uploads and static page generation."""
import html
import io
import json
from pathlib import Path
import re
import secrets
import threading
from PIL import Image, ImageOps, UnidentifiedImageError

LOCK = threading.RLock()
MAX_IMAGE_BYTES = 4 * 1024 * 1024
GALLERY_BLOCK = re.compile(r'<DIV CLASS="prototype-gallery">.*?</SECTION>\s*</DIV>', re.S | re.I)


def write_text(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(value, encoding='utf-8')
    temporary.replace(path)


class Gallery:
    def __init__(self, root):
        self.root = Path(root)
        self.public = self.root / 'public'
        self.data = self.root / 'data' / 'gallery.json'
        self.template = self.root / 'data' / 'gallery_template.html'
        self.page = self.public / 'index.php?id=11&temat=1&str=1&cd=0.html'

    def load(self):
        with LOCK:
            if not self.data.exists():
                source = self.page.read_text(encoding='utf-8')
                sections, images = [], []
                for section in re.finditer(r'<SECTION CLASS="prototype-gallery-section" ID="([^"]+)">\s*<H2>(.*?)</H2>(.*?)</SECTION>', source, re.S | re.I):
                    section_id, name, cards = section.groups()
                    sections.append({'id': section_id, 'name': html.unescape(name)})
                    for card in re.finditer(r'<A CLASS="prototype-gallery-card" HREF="([^"]+)"[^>]*>\s*<IMG SRC="([^"]+)"[^>]*>\s*<SPAN>(.*?)</SPAN>', cards, re.S | re.I):
                        path, thumbnail, title = map(html.unescape, card.groups())
                        images.append({'id': 'legacy-' + str(len(images) + 1), 'path': path, 'thumbnail': thumbnail, 'title': title, 'section_id': section_id})
                if not sections or not images or not GALLERY_BLOCK.search(source):
                    raise ValueError('Nie można odczytać istniejącej galerii.')
                write_text(self.template, source)
                self.save({'sections': sections, 'images': images})
            return json.loads(self.data.read_text(encoding='utf-8'))

    def save(self, data):
        write_text(self.data, json.dumps(data, ensure_ascii=False, indent=2) + '\n')

    def section_id(self, data, section_id):
        if not section_id:
            return None
        if not any(s['id'] == section_id for s in data['sections']):
            raise ValueError('Wybrana sekcja nie istnieje.')
        return section_id

    def add_section(self, name):
        with LOCK:
            data = self.load()
            name = name.strip()
            if not name or name.casefold() == 'bez sekcji' or any(s['name'].casefold() == name.casefold() for s in data['sections']):
                raise ValueError('Podaj unikalną nazwę sekcji (inną niż Bez sekcji).')
            section = {'id': 'galeria-' + secrets.token_hex(8), 'name': name}
            data['sections'].append(section)
            self.save(data)
            return section

    def delete_section(self, section_id):
        with LOCK:
            data = self.load()
            self.section_id(data, section_id)
            if not section_id:
                raise ValueError('Wybierz sekcję.')
            data['sections'] = [s for s in data['sections'] if s['id'] != section_id]
            for image in data['images']:
                if image['section_id'] == section_id:
                    image['section_id'] = None
            self.save(data)

    def add_image(self, title, section_id, content):
        with LOCK:
            data = self.load()
            title = title.strip()
            if not title:
                raise ValueError('Tytuł zdjęcia jest wymagany.')
            section_id = self.section_id(data, section_id)
            if not content or len(content) > MAX_IMAGE_BYTES:
                raise ValueError('Wybierz zdjęcie o rozmiarze do 4 MB.')
            try:
                with Image.open(io.BytesIO(content)) as source:
                    if source.format not in {'JPEG', 'PNG', 'GIF', 'WEBP'}:
                        raise ValueError('Dozwolone są JPG, PNG, GIF i WebP.')
                    if source.width * source.height > 25_000_000:
                        raise ValueError('Zdjęcie jest za duże (maksymalnie 25 mln pikseli).')
                    original = ImageOps.exif_transpose(source).convert('RGB')
                    original.load()
            except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as error:
                raise ValueError('Plik nie jest prawidłowym zdjęciem.') from error
            image_id = secrets.token_hex(16)
            path = f'Galeria/uploads/{image_id}.jpg'
            thumbnail = f'Galeria/Miniatury/{image_id}.jpg'
            (self.public / path).parent.mkdir(parents=True, exist_ok=True)
            (self.public / thumbnail).parent.mkdir(parents=True, exist_ok=True)
            original.save(self.public / path, quality=90)
            ImageOps.fit(original, (320, 220), method=Image.Resampling.LANCZOS).save(self.public / thumbnail, quality=85)
            image = {'id': image_id, 'title': title, 'path': path, 'thumbnail': thumbnail, 'section_id': section_id}
            data['images'].append(image)
            self.save(data)
            return image

    def edit_image(self, image_id, title, section_id):
        with LOCK:
            data = self.load()
            title = title.strip()
            if not title:
                raise ValueError('Tytuł zdjęcia jest wymagany.')
            section_id = self.section_id(data, section_id)
            image = next((i for i in data['images'] if i['id'] == image_id), None)
            if image is None:
                raise ValueError('Zdjęcie nie istnieje.')
            image.update(title=title, section_id=section_id)
            self.save(data)

    def delete_images(self, ids):
        with LOCK:
            data = self.load()
            ids = set(ids)
            if not ids or not ids.issubset({i['id'] for i in data['images']}):
                raise ValueError('Wybierz istniejące zdjęcia do usunięcia.')
            data['images'] = [i for i in data['images'] if i['id'] not in ids]
            self.save(data)

    def generate(self):
        with LOCK:
            data = self.load()
            esc = html.escape
            sections = list(data['sections'])
            if any(i['section_id'] is None for i in data['images']):
                sections.append({'id': 'galeria-bez-sekcji', 'name': 'Bez sekcji', 'uncategorized': True})
            result = ['<DIV CLASS="prototype-gallery"><H1>Galeria</H1>', '<NAV CLASS="prototype-gallery-tabs" aria-label="Kategorie galerii">']
            result += [f'<A HREF="#{esc(s["id"])}">{esc(s["name"])}</A>' for s in sections]
            result.append('</NAV>')
            for section in sections:
                result.append(f'<SECTION CLASS="prototype-gallery-section" ID="{esc(section["id"])}"><H2>{esc(section["name"])}</H2><DIV CLASS="prototype-gallery-grid">')
                for image in data['images']:
                    if image['section_id'] != (None if section.get('uncategorized') else section['id']):
                        continue
                    result.append(f'<A CLASS="prototype-gallery-card" HREF="{esc(image["path"])}" TARGET="_blank"><IMG SRC="{esc(image["thumbnail"])}" ALT="{esc(image["title"])}" loading="lazy"><SPAN>{esc(image["title"])}</SPAN></A>')
                result.append('</DIV></SECTION>')
            if not data['images']:
                result.append('<P>Brak zdjęć w galerii.</P>')
            result.append('</DIV>')
            source = self.template.read_text(encoding='utf-8')
            # A lambda prevents captions containing backslashes from becoming regex escapes.
            page, count = GALLERY_BLOCK.subn(lambda _: '\n'.join(result), source, count=1)
            if count != 1:
                raise ValueError('Nie znaleziono galerii w szablonie.')
            for target in self.public.glob('index.php?id=11*.html'):
                write_text(target, page)


if __name__ == '__main__':
    Gallery(Path(__file__).resolve().parent).generate()
