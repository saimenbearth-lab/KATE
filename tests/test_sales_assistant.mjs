import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

const app = readFileSync(new URL('../static/app.js', import.meta.url), 'utf8');
const flush = () => new Promise(setImmediate);

class Element {
  constructor(tagName = 'div') {
    this.tagName = tagName;
    this.children = [];
    this.listeners = {};
    this.attributes = {};
    this.value = '';
    this.disabled = false;
    this.textContent = '';
  }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = [...nodes]; }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  querySelector(selector) { return this.selectors?.[selector] || null; }
}

function setup({ hash = '', assistant = true } = {}) {
  const names = ['data-offer-currency', 'data-offers-load', 'data-offers-status', 'data-offers-results'];
  if (assistant) names.push('data-offer-days', 'data-offer-priority', 'data-sales-assistant',
    'data-assistant-checklist', 'data-offers-title');
  const controls = Object.fromEntries(names.map((name) => [name, new Element()]));
  controls['data-offer-currency'].value = 'USD';
  controls['data-offers-load'].textContent = assistant ? 'Show safari options' : 'Load product previews';
  if (assistant) {
    controls['data-offer-days'].value = '3';
    controls['data-offer-priority'].value = 'cost';
    controls['data-offers-title'].textContent = '3-day Maasai Mara safari options';
  }
  const section = new Element('section');
  section.selectors = Object.fromEntries(Object.entries(controls).map(([name, control]) => [`[${name}]`, control]));
  const calls = [];
  const timers = [];
  const listeners = {};
  const window = { location: { pathname: '/mara/', hash },
    addEventListener(name, callback) { listeners[name] = callback; } };
  const offers = [
    { product_id: 'higher', title: 'Higher price', from_price: 500, currency: 'USD' },
    { product_id: 'unknown', title: 'Unspecified price', from_price: null, currency: 'USD' },
    { product_id: 'lower', title: 'Lower price', from_price: 100, currency: 'USD' },
  ];
  let response = async () => ({ ok: true, json: async () => ({ offers }) });
  runInNewContext(app, {
    document: {
      querySelector: () => null,
      querySelectorAll: (selector) => selector === '[data-offers]' ? [section] : [],
      createElement: (tagName) => new Element(tagName),
      createTextNode: (textContent) => ({ textContent }),
    }, window, URLSearchParams, Intl, Date, Number, JSON,
    setTimeout(callback, delay) { timers.push({ callback, delay }); },
    fetch: async (url, options) => {
      calls.push({ url, options });
      return url === '/api/event' ? { ok: true } : response();
    },
  });
  return {
    controls, calls, window, listeners, timers,
    setResponse(value) { response = value; },
    offerCalls() { return calls.filter(({ url }) => url.startsWith('/api/offers')); },
    async submit() {
      let prevented = false;
      controls['data-sales-assistant'].listeners.submit({ preventDefault() { prevented = true; } });
      await flush();
      assert.equal(prevented, true, 'The assistant must load inline rather than submit a browser form.');
    },
  };
}

test('canonical safari hash loads once and preserves native tracked product handoffs', async () => {
  const s = setup({ hash: '#safari-options' });
  await flush();
  assert.equal(s.offerCalls().length, 1);
  assert.equal(s.offerCalls()[0].url, '/api/offers?currency=USD&days=3');
  const cards = s.controls['data-offers-results'].children;
  assert.deepEqual(cards.map((card) => card.children[0].textContent),
    ['Lower price', 'Higher price', 'Unspecified price']);
  const handoff = cards[0].children.at(-1);
  assert.equal(handoff.tagName, 'form');
  assert.equal(handoff.method, 'post');
  assert.equal(handoff.action, '/api/affiliate-click');
  assert.equal(handoff.children.find((input) => input.name === 'product_id').value, 'lower');
  assert.equal(handoff.children.find((input) => input.name === 'page').value, '/mara');
  assert.equal(handoff.children.at(-1).type, 'submit');
  s.listeners.hashchange();
  await flush();
  assert.equal(s.offerCalls().length, 1, 'Repeated hash events must not request duplicate previews.');
});

test('two- and four-day requests update the title and never retain a three-day button or status', async () => {
  const s = setup();
  for (const [days, currency] of [['2', 'EUR'], ['4', 'CHF']]) {
    s.controls['data-offer-days'].value = days;
    s.controls['data-offer-currency'].value = currency;
    await s.submit();
    assert.equal(s.offerCalls().at(-1).url, `/api/offers?currency=${currency}&days=${days}`);
    assert.equal(s.controls['data-offers-title'].textContent, `${days}-day Maasai Mara safari options`);
    assert.doesNotMatch(s.controls['data-offers-load'].textContent, /3.day/i);
    assert.doesNotMatch(s.controls['data-offers-status'].textContent, /3.day/i);
    assert.match(s.controls['data-offers-status'].textContent, /availability.*not been checked/i);
  }
});

test('comfort and transfer priorities provide checks without claiming verified matching or changing supplier order', async () => {
  const s = setup();
  for (const [priority, check] of [['comfort', /named accommodation/], ['travel_time', /departure and return times/]]) {
    s.controls['data-offer-priority'].value = priority;
    s.controls['data-offer-priority'].listeners.change();
    const checklist = s.controls['data-assistant-checklist'].children;
    assert.match(checklist[1].children.map((node) => node.textContent).join(' '), check);
    assert.match(checklist.at(-1).textContent, /not verified matches/);
    await s.submit();
    assert.deepEqual(s.controls['data-offers-results'].children.map((card) => card.children[0].textContent),
      ['Higher price', 'Unspecified price', 'Lower price']);
  }
});

test('requests disable controls, prevent concurrent calls and recover honestly from unavailable or empty supplier data', async () => {
  const s = setup();
  let finish;
  s.setResponse(() => new Promise((resolve) => { finish = resolve; }));
  s.controls['data-sales-assistant'].listeners.submit({ preventDefault() {} });
  for (const key of ['data-offers-load', 'data-offer-currency', 'data-offer-days', 'data-offer-priority']) {
    assert.equal(s.controls[key].disabled, true);
  }
  s.controls['data-sales-assistant'].listeners.submit({ preventDefault() {} });
  assert.equal(s.offerCalls().length, 1);
  finish({ ok: false, status: 503, json: async () => ({}) });
  await flush();
  assert.equal(s.controls['data-offers-results'].children.length, 0);
  assert.match(s.controls['data-offers-status'].textContent, /currently unavailable/);
  for (const key of ['data-offers-load', 'data-offer-currency', 'data-offer-days', 'data-offer-priority']) {
    assert.equal(s.controls[key].disabled, false);
  }
  s.setResponse(async () => ({ ok: true, json: async () => ({ offers: [] }) }));
  await s.submit();
  assert.match(s.controls['data-offers-status'].textContent, /No supplier previews found/);
  assert.match(s.controls['data-offers-status'].textContent, /availability has not been checked/);
  s.setResponse(async () => { throw new Error('Supplier connection failed'); });
  await s.submit();
  assert.match(s.controls['data-offers-status'].textContent, /Supplier connection failed/);
  assert.equal(s.controls['data-offers-load'].disabled, false);
});

test('existing offer sections without an assistant retain their button and default duration behavior', async () => {
  const s = setup({ assistant: false });
  assert.equal(s.offerCalls().length, 0);
  s.controls['data-offer-currency'].value = 'GBP';
  await s.controls['data-offers-load'].listeners.click();
  assert.equal(s.offerCalls()[0].url, '/api/offers?currency=GBP&days=3');
  assert.equal(s.controls['data-offers-results'].children.length, 3);
  assert.equal(s.controls['data-offers-load'].disabled, false);
});

test('rate limiting waits six seconds and retries the identical request once while controls stay locked', async () => {
  const s = setup();
  s.controls['data-offer-days'].value = '4';
  s.controls['data-offer-currency'].value = 'CHF';
  let requests = 0;
  s.setResponse(async () => ++requests === 1
    ? { ok: false, status: 429, json: async () => ({ error: 'Search refresh in progress' }) }
    : { ok: true, status: 200, json: async () => ({ offers: [
      { product_id: 'four-days', title: 'Four-day supplier preview', from_price: 400, currency: 'CHF' },
    ] }) });
  await s.submit();
  assert.equal(s.offerCalls().length, 1);
  assert.equal(s.timers.length, 1);
  assert.equal(s.timers[0].delay, 6000);
  assert.match(s.controls['data-offers-status'].textContent, /Waiting.*trying once more/);
  for (const key of ['data-offers-load', 'data-offer-currency', 'data-offer-days', 'data-offer-priority']) {
    assert.equal(s.controls[key].disabled, true);
  }
  await s.submit();
  assert.equal(s.offerCalls().length, 1, 'A second submission must not bypass the waiting request.');
  s.timers.shift().callback();
  await flush();
  assert.equal(s.offerCalls().length, 2);
  assert.equal(s.offerCalls()[0].url, '/api/offers?currency=CHF&days=4');
  assert.equal(s.offerCalls()[1].url, s.offerCalls()[0].url);
  assert.equal(s.controls['data-offers-results'].children.length, 1);
  assert.equal(s.controls['data-offers-title'].textContent, '4-day Maasai Mara safari options');
  assert.equal(s.controls['data-offers-load'].disabled, false);
  assert.equal(s.timers.length, 0);
});

test('a second rate-limit response stops retries, clears results and restores controls', async () => {
  const s = setup();
  s.setResponse(async () => ({ ok: false, status: 429, json: async () => ({ error: 'Supplier still busy' }) }));
  await s.submit();
  assert.equal(s.offerCalls().length, 1);
  s.timers.shift().callback();
  await flush();
  assert.equal(s.offerCalls().length, 2);
  assert.equal(s.timers.length, 0, 'Repeated rate limiting must never create an endless retry loop.');
  assert.equal(s.controls['data-offers-results'].children.length, 0);
  assert.match(s.controls['data-offers-status'].textContent, /still busy.*try again shortly/i);
  for (const key of ['data-offers-load', 'data-offer-currency', 'data-offer-days', 'data-offer-priority']) {
    assert.equal(s.controls[key].disabled, false);
  }
});
