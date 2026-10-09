import json
from html.parser import HTMLParser
import unittest

from scripts.localization import (
    CHECKLIST_DE, INQUIRY_DE, SITE_URL, language_selector, localize_html,
    localized_path,
)


class Parsed(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.nodes = []
        self.text = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))

    def handle_data(self, value):
        self.text.append(value)


class LocalizationTests(unittest.TestCase):
    def test_mixed_markup_preserves_form_contract_and_escapes_visible_text(self):
        source = '<html lang="en"><head></head><body><h1>Plan the trip around <em>your</em> priorities.</h1><form action="/api/plan"><select name="focus"><option value="undecided">Still deciding</option></select><input id="days" name="days" value="3"><p>Unmapped A &amp; B &lt;script&gt;</p></form></body></html>'
        rendered = localize_html(source, '/planner/')
        parsed = Parsed(rendered)
        self.assertIn(('html', {'lang': 'de'}), parsed.nodes)
        self.assertIn(('em', {}), parsed.nodes)
        self.assertIn(('form', {'action': '/api/plan'}), parsed.nodes)
        self.assertIn(('option', {'value': 'undecided'}), parsed.nodes)
        self.assertIn(('input', {'id': 'days', 'name': 'days', 'value': '3'}), parsed.nodes)
        self.assertIn('Noch unentschieden', ''.join(parsed.text))
        self.assertIn('deinen', ''.join(parsed.text))
        self.assertIn('Unmapped A &amp; B &lt;script&gt;', rendered)

    def test_language_routes_preserve_query_and_fragment_but_not_assets_or_external_links(self):
        source = '<html lang="en"><head></head><body><a href="/mara/?source=guide&amp;days=3#safari-options">See safari options</a><a href="https://www.viator.com/tours/Test?pid=P00323912">Viator</a><a href="/control/">Admin</a><a href="#provider-inquiry">Copy</a><img src="/static/hero.jpg"><a href="/resources/safari-booking-checklist.txt" download>Download</a></body></html>'
        nodes = Parsed(localize_html(source, '/')).nodes
        hrefs = [attrs['href'] for tag, attrs in nodes if tag == 'a']
        self.assertIn('/de/mara/?source=guide&days=3#safari-options', hrefs)
        self.assertIn('https://www.viator.com/tours/Test?pid=P00323912', hrefs)
        self.assertIn('/control/', hrefs)
        self.assertIn('#provider-inquiry', hrefs)
        self.assertIn('/de/resources/safari-booking-checklist.txt', hrefs)
        self.assertIn(('img', {'src': '/static/hero.jpg'}), nodes)

    def test_canonical_hreflang_and_schema_are_reciprocal(self):
        schema = {'@context': 'https://schema.org', '@type': 'WebPage', 'name': 'Kenya Trip Planner', 'url': SITE_URL + '/planner/'}
        source = '<html lang="en"><head><link rel="canonical" href="' + SITE_URL + '/planner/"><meta property="og:url" content="' + SITE_URL + '/planner/"><meta name="robots" content="noindex,follow"><script type="application/ld+json">' + json.dumps(schema) + '</script></head><body></body></html>'
        rendered = localize_html(source, '/planner/')
        nodes = Parsed(rendered).nodes
        self.assertIn(('link', {'rel': 'canonical', 'href': SITE_URL + '/de/planner/'}), nodes)
        self.assertIn(('meta', {'name': 'robots', 'content': 'noindex,follow'}), nodes)
        alternates = {a['hreflang']: a['href'] for tag, a in nodes if tag == 'link' and a.get('rel') == 'alternate'}
        self.assertEqual(alternates, {'en': SITE_URL + '/planner/', 'de': SITE_URL + '/de/planner/', 'x-default': SITE_URL + '/planner/'})
        self.assertIn('"name": "Kenia-Reiseplaner"', rendered)
        self.assertIn('"url": "' + SITE_URL + '/de/planner/"', rendered)

    def test_scripts_and_style_are_not_translated_or_entity_encoded(self):
        code = 'const x = "Home"; if (x < "z" && true) console.log(x);'
        source = '<html lang="en"><head><script>' + code + '</script><style>.x > a { color: red; }</style></head><body>Home</body></html>'
        rendered = localize_html(source, '/')
        self.assertIn('<script>' + code + '</script>', rendered)
        self.assertIn('.x > a { color: red; }', rendered)
        self.assertIn('<body>Startseite</body>', rendered)

    def test_english_and_unknown_content_remain_readable(self):
        source = '<html lang="en"><head></head><body><p>New supplier words remain English.</p><a href="/mara">Home</a></body></html>'
        en = localize_html(source, '/', 'en')
        de = localize_html(source, '/')
        self.assertIn('New supplier words remain English.', de)
        self.assertIn('<body><p>New supplier words remain English.</p><a href="/mara/">Home</a>', en)
        with self.assertRaises(ValueError):
            localize_html(source, '/', 'fr')

    def test_selector_retains_alternate_destinations_and_current_language(self):
        source = '<html lang="en"><head></head><body>' + language_selector('/mara/', 'en') + '</body></html>'
        nodes = Parsed(localize_html(source, '/mara/')).nodes
        links = {a['data-kate-language']: a for tag, a in nodes if tag == 'a'}
        self.assertEqual(links['en']['href'], '/mara/')
        self.assertEqual(links['de']['href'], '/de/mara/')
        self.assertNotIn('aria-current', links['en'])
        self.assertEqual(links['de']['aria-current'], 'true')

    def test_relocalizing_does_not_duplicate_search_language_tags(self):
        source = '<html lang="en"><head><link rel="alternate" hreflang="en" href="/"></head><body></body></html>'
        rendered = localize_html(localize_html(source, '/', 'en'), '/', 'de')
        nodes = Parsed(rendered).nodes
        self.assertEqual(sum(tag == 'link' and a.get('rel') == 'alternate' for tag, a in nodes), 3)
        self.assertEqual(sum(tag == 'meta' and a.get('property') == 'og:locale' for tag, a in nodes), 1)

    def test_german_resource_download_contains_complete_inquiry_and_two_quote_fields(self):
        self.assertIn(INQUIRY_DE, CHECKLIST_DE)
        self.assertEqual(CHECKLIST_DE.count('Angebot A:'), 17)
        self.assertEqual(CHECKLIST_DE.count('Angebot B:'), 17)
        self.assertNotIn('Quote A:', CHECKLIST_DE)
        self.assertEqual(localized_path('/de/mara/#safari-options', 'en'), '/mara/#safari-options')
        self.assertEqual(localized_path('/', 'de'), '/de/')


if __name__ == '__main__':
    unittest.main()
