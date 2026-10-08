import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import growth_workers as workers


class GrowthWorkerTests(unittest.TestCase):
    def sitemap(self, urls):
        return ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join('<url><loc>' + url + '</loc></url>' for url in urls) + '</urlset>').encode()

    def fixture(self, state=None):
        key = (workers.ROOT / 'indexnow-key.txt').read_text().strip()
        urls = [workers.SITE_URL + '/', workers.SITE_URL + '/guides/']
        html = {urls[0]: b'<html>home</html>', urls[1]: b'<html>guide updated</html>'}
        responses = {
            workers.SITE_URL + '/build.json': (200, json.dumps({'commit': 'a' * 40, 'release': 'kate-supplier-preview-v1'}).encode()),
            workers.SITE_URL + '/' + key + '.txt': (200, key.encode()),
            workers.SITE_URL + '/sitemap.xml': (200, self.sitemap(urls)),
            workers.SITE_URL + '/robots.txt': (200, ('Sitemap: ' + workers.SITE_URL + '/sitemap.xml\n').encode()),
            **{url: (200, body) for url, body in html.items()},
            'https://api.indexnow.org/indexnow': (202, b''),
        }
        return urls, html, responses

    def test_sitemap_rejects_external_private_duplicate_and_http_urls(self):
        for urls in ([workers.SITE_URL + '/control/'], [workers.SITE_URL + '/planner/'], ['https://example.com/'], [workers.SITE_URL.replace('https:', 'http:') + '/'], [workers.SITE_URL + '/', workers.SITE_URL + '/']):
            with self.subTest(urls=urls), self.assertRaises(ValueError):
                workers.sitemap_urls(self.sitemap(urls))

    def test_only_changed_content_is_notified_and_accepted_state_is_saved(self):
        urls, html, responses = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'state.json'
            state.write_text(json.dumps({'site': workers.SITE_URL, 'notified_fingerprints': {urls[0]: hashlib.sha256(html[urls[0]]).hexdigest(), urls[1]: 'previous-content'}}))
            with patch.object(workers, 'request', side_effect=lambda url, **kw: responses[url]) as req:
                result = workers.search_discovery('a' * 40, submit=True, state_file=state)
            self.assertEqual(result['changed_since_last_accepted_notification'], [urls[1]])
            post = [call for call in req.call_args_list if call.kwargs.get('payload')]
            self.assertEqual(post[0].kwargs['payload']['urlList'], [urls[1]])
            self.assertFalse(result['indexing_verified'])
            self.assertEqual(json.loads(state.read_text())['http_status'], 202)

    def test_daily_readonly_check_never_posts_or_creates_notification_state(self):
        _, _, responses = self.fixture()
        with tempfile.TemporaryDirectory() as directory, patch.object(workers, 'request', side_effect=lambda url, **kw: responses[url]) as req:
            state = Path(directory) / 'state.json'
            result = workers.search_discovery('a' * 40, state_file=state)
            self.assertFalse(state.exists())
            self.assertFalse(result['submitted'])
            self.assertTrue(all('payload' not in call.kwargs for call in req.call_args_list))

    def test_unchanged_pages_skip_submission_even_on_deployment(self):
        urls, html, responses = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'state.json'
            state.write_text(json.dumps({'site': workers.SITE_URL, 'notified_fingerprints': {url: hashlib.sha256(html[url]).hexdigest() for url in urls}}))
            with patch.object(workers, 'request', side_effect=lambda url, **kw: responses[url]) as req:
                result = workers.search_discovery('a' * 40, submit=True, state_file=state)
            self.assertFalse(result['submitted'])
            self.assertTrue(all('payload' not in call.kwargs for call in req.call_args_list))

    def test_rejected_notification_does_not_update_state(self):
        _, _, responses = self.fixture()
        responses['https://api.indexnow.org/indexnow'] = (403, b'rejected')
        with tempfile.TemporaryDirectory() as directory, patch.object(workers, 'request', side_effect=lambda url, **kw: responses[url]):
            state = Path(directory) / 'state.json'
            with self.assertRaises(ValueError):
                workers.search_discovery('a' * 40, submit=True, state_file=state)
            self.assertFalse(state.exists())

    def test_wrong_deployment_or_ownership_prevents_notification(self):
        _, _, responses = self.fixture()
        with patch.object(workers, 'request', side_effect=lambda url, **kw: responses[url]):
            with self.assertRaises(ValueError):
                workers.search_discovery('b' * 40, submit=True, state_file='unused.json')
        key = (workers.ROOT / 'indexnow-key.txt').read_text().strip()
        responses[workers.SITE_URL + '/' + key + '.txt'] = (200, b'wrong-key')
        with patch.object(workers, 'request', side_effect=lambda url, **kw: responses[url]), self.assertRaises(ValueError):
            workers.search_discovery('a' * 40, submit=True, state_file='unused.json')

    def test_public_control_exposure_fails_health_without_any_write(self):
        def response(url, **kw):
            self.assertNotIn('payload', kw)
            if url.endswith('/build.json'):
                return 200, json.dumps({'commit': 'a' * 40, 'release': 'kate-supplier-preview-v1'}).encode()
            if url.endswith('/api/health'):
                return 200, json.dumps({'ok': True, 'viator_configured': True, 'admin_configured': True, 'release': 'kate-supplier-preview-v1'}).encode()
            if url.endswith('/api/control'):
                return 200, b'unsafe'
            return 200, b'<html>page</html>'
        with patch.object(workers, 'request', side_effect=response), self.assertRaisesRegex(ValueError, 'Unauthenticated control'):
            workers.health_monitor('a' * 40)

    def test_snapshot_keeps_historical_time_and_does_not_turn_clicks_into_customers(self):
        evidence = {'verified_at': '2026-10-08T17:18:08Z', 'affiliate_clicks': 5, 'known_test_clicks': 3, 'recorded_conversions': 0, 'recorded_revenue': [], 'customer_revenue_claimed': False}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'evidence.json'
            path.write_text(json.dumps(evidence))
            result = workers.evidence_auditor(path)
            self.assertEqual(result['snapshot_verified_at'], evidence['verified_at'])
            self.assertEqual(result['remaining_clicks_are_not_proven_customers'], 2)
            self.assertFalse(result['customer_activity_verified'])
            self.assertTrue(result['snapshot_is_historical_not_a_live_finance_query'])
            for bad in ({'customer_revenue_claimed': True}, {'known_test_clicks': 6}, {'paid_campaign_started': True}):
                path.write_text(json.dumps({**evidence, **bad}))
                with self.assertRaises(ValueError):
                    workers.evidence_auditor(path)

    def test_resource_requires_owned_path_and_booking_options_link(self):
        with self.assertRaises(ValueError):
            workers.resource_auditor('/control/')
        with patch.object(workers, 'request', return_value=(200, b'<html>missing CTA</html>')), self.assertRaises(ValueError):
            workers.resource_auditor('/resources/safari-booking-checklist/')

    def test_resource_waits_for_expected_deployment_before_checking_new_page(self):
        calls = []
        def response(url, **kw):
            calls.append(url)
            if url.endswith('/build.json'):
                commit = 'b' * 40 if calls.count(url) == 1 else 'a' * 40
                return 200, json.dumps({'commit': commit, 'release': 'kate-supplier-preview-v1'}).encode()
            return 200, b'<html><a href="/mara/#safari-options">Options</a></html>'
        with patch.object(workers, 'request', side_effect=response), patch.object(workers.time, 'sleep') as sleep:
            result = workers.resource_auditor('/resources/safari-booking-checklist/', 'a' * 40, wait_attempts=3)
        self.assertEqual(calls, [workers.SITE_URL + '/build.json', workers.SITE_URL + '/build.json', workers.SITE_URL + '/resources/safari-booking-checklist/'])
        sleep.assert_called_once_with(20)
        self.assertEqual(result['http_status'], 200)


if __name__ == '__main__':
    unittest.main()
