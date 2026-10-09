import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const code = readFileSync(new URL('../static/i18n.js', import.meta.url), 'utf8');
function run(lang = 'de', { pathname = '/de/mara/', saved = null, blocked = false } = {}) {
  const writes = [], redirects = [], handlers = [];
  const link = {
    href: 'https://example.test/mara/',
    getAttribute: () => 'en',
    addEventListener: (_, fn) => handlers.push(fn),
  };
  const window = {
    location: { origin: 'https://example.test', pathname, search: '', hash: '#safari-options', replace: (value) => redirects.push(value) },
    localStorage: {
      getItem: () => { if (blocked) throw new Error('blocked'); return saved; },
      setItem: (...args) => { if (blocked) throw new Error('blocked'); writes.push(args); },
    },
  };
  const document = { documentElement: { lang }, querySelectorAll: () => [link] };
  vm.runInNewContext(code, { window, document, URL });
  return { ...window.KATE_I18N, writes, redirects, handlers, link };
}

test('German UI interpolates values, preserves unknown content and localizes only known routes', () => {
  const i18n = run();
  assert.equal(i18n.t('From {price}', { price: '1.234,00 €' }), 'Ab 1.234,00 €');
  assert.equal(i18n.t('{count} travelers', { count: 2 }), '2 Reisende');
  assert.equal(i18n.t('Unmapped provider title'), 'Unmapped provider title');
  assert.equal(i18n.t('From {price}'), 'Ab {price}');
  assert.equal(i18n.path('/mara/?days=3#safari-options'), '/de/mara/?days=3#safari-options');
  assert.equal(i18n.path('/api/plan'), '/api/plan');
  assert.equal(i18n.path('https://external.test/mara/'), 'https://external.test/mara/');
});

test('English keeps copy and German planner text preserves user origin literally', () => {
  assert.equal(run('en').t('From {price}', { price: '$250' }), 'From $250');
  const i18n = run();
  assert.equal(i18n.t('DAY 03'), 'TAG 03');
  assert.equal(i18n.t('Day 2 · Your main priorities'), 'Tag 2 · Deine wichtigsten Wünsche');
  const original = "From Nairobi <test>, confirm the departure or pickup details, onward transport, first-day inclusions and the provider's exact itinerary for the Maasai Mara.";
  assert.ok(i18n.t(original).startsWith('Ab Nairobi <test>:'));
});

test('Language selection works with blocked storage and keeps the current section', () => {
  const i18n = run('de', { blocked: true });
  assert.doesNotThrow(() => i18n.handlers[0]());
  assert.equal(i18n.link.href, '/mara/#safari-options');
  assert.equal(i18n.redirects.length, 0);
});

test('An explicitly chosen German preference is restored on root only', () => {
  assert.deepEqual(run('en', { pathname: '/', saved: 'de' }).redirects, ['/de/#safari-options']);
  assert.deepEqual(run('en', { pathname: '/mara/', saved: 'de' }).redirects, []);
  assert.deepEqual(run('en', { pathname: '/', saved: 'https://evil.test' }).redirects, []);
  const i18n = run();
  i18n.handlers[0]();
  assert.deepEqual(i18n.writes, [['kate_language', 'en']]);
});
