import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gallery', ROOT / 'gallery.py')
gallery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gallery)

class GalleryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'public', self.root / 'public')
        self.store = gallery.Gallery(self.root)
        self.data = self.store.load()

    def tearDown(self):
        self.temp.cleanup()

    def image(self):
        stream = io.BytesIO()
        Image.new('RGB', (640, 480), 'green').save(stream, format='PNG')
        return stream.getvalue()

    def test_import_preserves_existing_images_and_sections(self):
        self.assertEqual(len(self.data['images']), 59)
        self.assertEqual([s['name'] for s in self.data['sections']], ['Kościół', 'Klasztor', 'Wspólnota'])
        self.assertTrue(all(i['title'] and (self.root/'public'/i['path']).exists() for i in self.data['images']))
        self.assertEqual(self.data, self.store.load())

    def test_upload_requires_title_and_valid_image_and_section(self):
        for title, image, section in [('', self.image(), ''), ('Title', b'not an image', ''), ('Title', self.image(), 'missing')]:
            with self.assertRaises(ValueError):
                self.store.add_image(title, section, image)
        self.assertEqual(len(self.store.load()['images']), 59)

    def test_upload_edit_and_render_all_variants(self):
        image = self.store.add_image('Title <hello>', '', self.image())
        self.assertTrue((self.root/'public'/image['thumbnail']).exists())
        self.store.edit_image(image['id'], 'New & title', self.data['sections'][0]['id'])
        self.store.generate()
        for page in (self.root/'public').glob('index.php?id=11*.html'):
            text = page.read_text()
            self.assertIn('New &amp; title', text)
            self.assertNotIn('Title &lt;hello&gt;', text)
            self.assertEqual(text.count('CLASS="prototype-gallery-card"'), 60)

    def test_section_deletion_preserves_images_as_uncategorized(self):
        section = self.data['sections'][0]['id']
        ids = {i['id'] for i in self.data['images'] if i['section_id'] == section}
        self.store.delete_section(section)
        data = self.store.load()
        self.assertEqual(len(data['images']), 59)
        self.assertTrue(all(i['section_id'] is None for i in data['images'] if i['id'] in ids))
        self.store.generate()
        self.assertIn('Bez sekcji', self.store.page.read_text())

    def test_add_section_and_single_and_bulk_delete(self):
        section = self.store.add_section('Nowa sekcja')
        with self.assertRaises(ValueError): self.store.add_section(' nowa SEKCJA ')
        with self.assertRaises(ValueError): self.store.add_section(' ')
        images = [self.store.add_image(str(i), section['id'], self.image()) for i in range(3)]
        self.store.delete_images([images[0]['id']])
        self.store.delete_images([i['id'] for i in images[1:]])
        self.assertEqual(len(self.store.load()['images']), 59)
        self.assertTrue((self.root/'public'/images[0]['path']).exists())
        with self.assertRaises(ValueError): self.store.edit_image('missing', 'Title', '')

if __name__ == '__main__': unittest.main()
