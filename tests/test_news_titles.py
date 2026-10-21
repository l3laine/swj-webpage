import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('news', Path(__file__).resolve().parents[1] / 'generate_news.py')
news = importlib.util.module_from_spec(spec)
spec.loader.exec_module(news)

class NewsTitleTests(unittest.TestCase):
    def test_untitled_legacy_news_has_no_generated_title(self):
        self.assertEqual(news.legacy_title(3, '<p>Treść bez tytułu.</p>'), '')

    def test_existing_heading_is_preserved(self):
        self.assertEqual(news.legacy_title(3, '<b>Prawdziwy tytuł</b><p>Treść</p>'), 'Prawdziwy tytuł')

    def test_titleless_entry_omits_heading_in_list_and_detail(self):
        post = dict(title='', content='<p>Treść</p>', image='', excerpt='Treść', href='article.html')
        self.assertNotIn('news-list-title', news.render_index([post]))
        self.assertNotIn('<B></B>', news.render_detail(post))

if __name__ == '__main__':
    unittest.main()
