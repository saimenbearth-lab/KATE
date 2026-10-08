from html.parser import HTMLParser
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from scripts.build_static import SITE_URL, production_shell, write_search_files
from scripts.travel_guides import GUIDES


class Tags(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class SearchTests(unittest.TestCase):
    def test_each_guide_has_correct_canonical_description_and_article(self):
        with patch.dict(os.environ, {'CONTEXT': 'production'}):
            for guide in GUIDES:
                html = production_shell(guide['title'], guide['body'], 'guide', path=guide['path'], description=guide['description'], article=True).decode()
                tags = Tags(html).tags
                self.assertIn(('link', {'rel': 'canonical', 'href': SITE_URL + guide['path']}), tags)
                self.assertIn(('meta', {'name': 'description', 'content': guide['description']}), tags)
                self.assertNotIn('noindex', html)
                self.assertIn('/mara/#safari-options', html)
                data = json.loads(html.split('<script type="application/ld+json">')[1].split('</script>')[0])
                self.assertEqual(data['@type'], 'Article')
                self.assertEqual(data['url'], SITE_URL + guide['path'])

    def test_private_pages_and_preview_pages_are_noindex(self):
        with patch.dict(os.environ, {'CONTEXT': 'production'}):
            for current in ('planner', 'control'):
                self.assertIn('content="noindex,follow"', production_shell('Page', '<h1>Page</h1>', current).decode())
        with patch.dict(os.environ, {'CONTEXT': 'deploy-preview'}):
            self.assertIn('content="noindex,follow"', production_shell('Home', '<h1>Home</h1>', 'home').decode())

    def test_sitemap_only_lists_public_pages_and_robots_points_to_it(self):
        paths = ['/', '/mara/', '/guides/', *(guide['path'] for guide in GUIDES)]
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'CONTEXT': 'production'}):
            output = Path(directory)
            write_search_files(output, paths)
            urls = [node.text for node in ET.parse(output / 'sitemap.xml').iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
            self.assertEqual(urls, [SITE_URL + path for path in paths])
            self.assertIn('Sitemap: ' + SITE_URL + '/sitemap.xml', (output / 'robots.txt').read_text())
            self.assertNotIn(SITE_URL + '/control/', urls)

    def test_preview_robots_disallows_crawling(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'CONTEXT': 'branch-deploy'}):
            write_search_files(Path(directory), ['/'])
            self.assertIn('Disallow: /\n', (Path(directory) / 'robots.txt').read_text())
