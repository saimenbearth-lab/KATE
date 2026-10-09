from html.parser import HTMLParser
import json
import os
import unittest
from unittest.mock import patch

from scripts.build_static import SITE_URL, guide_hub_html, production_mara_html, production_shell
from scripts.localization import PUBLIC_PATHS
from scripts.nairobi_guide import GUIDE, BRIEF_EN, BRIEF_DE, TITLE_DE, DESCRIPTION_DE


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.nodes = []
        self.text = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)


class NairobiGuideTests(unittest.TestCase):
    def render(self, language):
        return production_shell(GUIDE['title'], GUIDE['body_de' if language == 'de' else 'body'], 'guide', path=GUIDE['path'], description=GUIDE['description'], article=True, language=language).decode()

    def test_both_language_pages_have_reciprocal_metadata_and_real_supplier_path(self):
        with patch.dict(os.environ, {'CONTEXT': 'production'}):
            for language in ('en', 'de'):
                source = self.render(language)
                doc = Document(source)
                prefix = '/de' if language == 'de' else ''
                self.assertIn(('html', {'lang': language}), doc.nodes)
                self.assertIn(('link', {'rel': 'canonical', 'href': SITE_URL + prefix + GUIDE['path']}), doc.nodes)
                alternates = {attrs['hreflang']: attrs['href'] for tag, attrs in doc.nodes if tag == 'link' and attrs.get('rel') == 'alternate'}
                self.assertEqual(alternates['en'], SITE_URL + GUIDE['path'])
                self.assertEqual(alternates['de'], SITE_URL + '/de' + GUIDE['path'])
                self.assertIn(prefix + '/mara/#nairobi-extras', source)
                self.assertIn(prefix + '/mara/#safari-options', source)
                article = json.loads(source.split('<script type="application/ld+json">')[1].split('</script>')[0])
                self.assertEqual(article['url'], SITE_URL + prefix + GUIDE['path'])
                self.assertEqual(article['@type'], 'Article')
                if language == 'de':
                    self.assertEqual(article['name'], TITLE_DE)
                    self.assertEqual(article['description'], DESCRIPTION_DE)
                    self.assertIn('Plane vom Flug oder der Safari-Abfahrt aus', source)
                    self.assertNotIn('Build the schedule around the flight', source)

    def test_copy_template_has_matching_control_and_no_personal_data_form(self):
        for language, brief in (('en', BRIEF_EN), ('de', BRIEF_DE)):
            source = self.render(language)
            doc = Document(source)
            buttons = [attrs for tag, attrs in doc.nodes if tag == 'button' and 'data-copy-template-button' in attrs]
            templates = [attrs for tag, attrs in doc.nodes if tag == 'textarea']
            self.assertEqual(len(buttons), 1)
            self.assertEqual(len(templates), 1)
            self.assertEqual(buttons[0]['aria-controls'], templates[0]['id'])
            self.assertIn('readonly', templates[0])
            self.assertIn(brief, ''.join(doc.text))
            self.assertIn('/static/resources.js', source)
            self.assertFalse(any(tag in {'form', 'input'} for tag, attrs in doc.nodes))

    def test_new_guide_is_discoverable_without_loading_supplier_prices(self):
        self.assertIn(GUIDE['path'], PUBLIC_PATHS)
        self.assertIn(GUIDE['path'], guide_hub_html())
        self.assertIn(GUIDE['path'], production_mara_html())
        self.assertIn('id="nairobi-extras"', production_mara_html())
        for language in ('en', 'de'):
            source = self.render(language)
            self.assertNotIn('data-offers', source)
            self.assertNotIn('www.viator.com/tours/', source)
            self.assertIn('https://kws.ecitizen.go.ke/', source)
            self.assertIn('Viator', source)


if __name__ == '__main__':
    unittest.main()
