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
  getAttribute(name) { return this.attributes[name] ?? null; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  querySelector(selector) { return this.selectors?.[selector] || null; }
}

function setup({ hash = '', assistant = true, storage = new Map(), storageBlocked = false,
  planner = false, i18n = null, extraSection = false, category = null } = {}) {
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
  if (category) section.setAttribute('data-offer-category', category);
  section.selectors = Object.fromEntries(Object.entries(controls).map(([name, control]) => [`[${name}]`, control]));
  const extraControls = extraSection ? Object.fromEntries(names.slice(0, 4).map((name) => [name, new Element()])) : null;
  const secondary = extraSection ? new Element('section') : null;
  if (secondary) {
    extraControls['data-offer-currency'].value = 'USD';
    secondary.setAttribute('data-offer-category', 'nairobi');
    secondary.setAttribute('id', 'nairobi-extras');
    secondary.selectors = Object.fromEntries(Object.entries(extraControls).map(([name, control]) => [`[${name}]`, control]));
  }
  const plannerForm = planner ? new Element('form') : null;
  if (plannerForm) {
    plannerForm.elements = { currency: new Element('select'), budget: new Element('input') };
    plannerForm.elements.currency.value = 'CHF';
    plannerForm.elements.budget.value = '1200.50';
  }
  const calls = [];
  const timers = [];
  const listeners = {};
  const window = { location: { pathname: '/mara/', hash }, KATE_I18N: i18n,
    localStorage: {
      getItem(key) { if (storageBlocked) throw new Error('Storage blocked'); return storage.get(key) ?? null; },
      setItem(key, value) { if (storageBlocked) throw new Error('Storage blocked'); storage.set(key, value); },
    },
    addEventListener(name, callback) {
      const previous = listeners[name];
      listeners[name] = previous ? () => { previous(); callback(); } : callback;
    } };
  const offers = [
    { product_id: 'higher', title: 'Higher price', from_price: 500, currency: 'USD' },
    { product_id: 'unknown', title: 'Unspecified price', from_price: null, currency: 'USD' },
    { product_id: 'lower', title: 'Lower price', from_price: 100, currency: 'USD' },
  ];
  let response = async (url) => ({ ok: true, json: async () => ({
    offers: offers.map((offer) => ({ ...offer, currency: new URL(url, 'https://kate.test').searchParams.get('currency') })),
  }) });
  runInNewContext(app, {
    document: {
      querySelector: (selector) => selector === '[data-planner-form]' ? plannerForm : null,
      querySelectorAll: (selector) => selector === '[data-offers]' ? [section, ...(secondary ? [secondary] : [])] : [],
      createElement: (tagName) => new Element(tagName),
      createTextNode: (textContent) => ({ textContent }),
    }, window, URLSearchParams, Intl, Date, Number, JSON, AbortController,
    setTimeout(callback, delay) { timers.push({ callback, delay }); },
    fetch: async (url, options) => {
      calls.push({ url, options });
      return url === '/api/event' ? { ok: true } : response(url, options);
    },
  });
  return {
    controls, calls, window, listeners, timers, storage, plannerForm, extraControls,
    setResponse(value) { response = value; },
    offerCalls() { return calls.filter(({ url }) => url.startsWith('/api/offers')); },
    changeCurrency(value) {
      controls['data-offer-currency'].value = value;
      controls['data-offer-currency'].listeners.change();
    },
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

test('currency selected before loading persists for navigation without fetching previews', async () => {
  const storage = new Map();
  const s = setup({ storage });
  s.changeCurrency('EUR');
  await flush();
  assert.equal(s.offerCalls().length, 0);
  assert.equal(storage.get('kate_currency'), 'EUR');
  await s.submit();
  assert.equal(s.offerCalls()[0].url, '/api/offers?currency=EUR&days=3');
  const nextPage = setup({ storage, hash: '#safari-options' });
  await flush();
  assert.equal(nextPage.controls['data-offer-currency'].value, 'EUR');
  assert.equal(nextPage.offerCalls()[0].url, '/api/offers?currency=EUR&days=3');
});

test('changing currency clears visible old prices immediately and renders the new supplier result', async () => {
  const s = setup({ hash: '#safari-options' });
  await flush();
  assert.equal(s.controls['data-offers-results'].children.length, 3);
  let finish;
  s.setResponse(() => new Promise((resolve) => { finish = resolve; }));
  s.changeCurrency('CHF');
  assert.equal(s.controls['data-offers-results'].children.length, 0);
  assert.equal(s.offerCalls().at(-1).url, '/api/offers?currency=CHF&days=3');
  finish({ ok: true, json: async () => ({ offers: [
    { product_id: 'chf', title: 'Swiss franc preview', from_price: 123.45, currency: 'CHF' },
  ] }) });
  await flush();
  const cards = s.controls['data-offers-results'].children;
  assert.equal(cards.length, 1);
  assert.match(cards[0].children[1].textContent, /CHF/);
  const count = s.offerCalls().length;
  s.changeCurrency('CHF');
  await flush();
  assert.equal(s.offerCalls().length, count, 'Selecting the same currency must not refresh again.');
});

test('failed currency reload never restores old prices and permits a later load', async () => {
  const s = setup({ hash: '#safari-options' });
  await flush();
  s.setResponse(async () => ({ ok: false, status: 503, json: async () => ({}) }));
  s.changeCurrency('GBP');
  assert.equal(s.controls['data-offers-results'].children.length, 0);
  await flush();
  assert.equal(s.controls['data-offers-results'].children.length, 0);
  assert.match(s.controls['data-offers-status'].textContent, /currently unavailable/);
  assert.equal(s.controls['data-offer-currency'].disabled, false);
  s.setResponse(async () => ({ ok: true, json: async () => ({ offers: [] }) }));
  await s.submit();
  assert.equal(s.offerCalls().at(-1).url, '/api/offers?currency=GBP&days=3');
  assert.match(s.controls['data-offers-status'].textContent, /No supplier previews/);
});

test('planner and offer currency stay synchronized without converting the typed budget', async () => {
  const s = setup({ planner: true, storage: new Map([['kate_currency', 'EUR']]) });
  assert.equal(s.plannerForm.elements.currency.value, 'EUR');
  assert.equal(s.controls['data-offer-currency'].value, 'EUR');
  s.changeCurrency('GBP');
  assert.equal(s.plannerForm.elements.currency.value, 'GBP');
  assert.equal(s.plannerForm.elements.budget.value, '1200.50');
  s.plannerForm.elements.currency.value = 'CHF';
  s.plannerForm.elements.currency.listeners.change();
  assert.equal(s.controls['data-offer-currency'].value, 'CHF');
  assert.equal(s.storage.get('kate_currency'), 'CHF');
  assert.equal(s.plannerForm.elements.budget.value, '1200.50');
  assert.equal(s.offerCalls().length, 0);
});

test('stale requests cannot render prices, errors or unlock a newer currency request', async () => {
  const s = setup();
  const pending = [];
  s.setResponse(() => new Promise((resolve, reject) => pending.push({ resolve, reject })));
  await s.submit();
  s.changeCurrency('EUR');
  assert.equal(s.offerCalls().length, 2);
  assert.equal(s.offerCalls()[0].options.signal.aborted, true);
  pending[0].resolve({ ok: true, json: async () => ({ offers: [
    { product_id: 'stale', title: 'Old USD offer', from_price: 20, currency: 'USD' },
  ] }) });
  await flush();
  assert.equal(s.controls['data-offers-results'].children.length, 0);
  assert.equal(s.controls['data-offers-load'].disabled, true);
  assert.match(s.controls['data-offers-status'].textContent, /Loading/);
  s.changeCurrency('CHF');
  pending[1].reject(new Error('Obsolete request failed'));
  await flush();
  assert.doesNotMatch(s.controls['data-offers-status'].textContent, /Obsolete/);
  assert.equal(s.controls['data-offers-load'].disabled, true);
  pending[2].resolve({ ok: true, json: async () => ({ offers: [
    { product_id: 'current', title: 'Current CHF offer', from_price: 30, currency: 'CHF' },
  ] }) });
  await flush();
  assert.equal(s.controls['data-offers-results'].children[0].children[0].textContent, 'Current CHF offer');
  assert.equal(s.controls['data-offers-load'].disabled, false);
});

test('currency changes during the 429 wait cancel the old retry and retain exactly one retry for the new request', async () => {
  const s = setup();
  s.setResponse(async () => ({ ok: false, status: 429, json: async () => ({}) }));
  await s.submit();
  const oldTimer = s.timers.shift();
  s.changeCurrency('EUR');
  await flush();
  assert.equal(s.offerCalls().length, 2);
  oldTimer.callback();
  await flush();
  assert.equal(s.offerCalls().length, 2, 'An obsolete currency must never be retried.');
  assert.equal(s.controls['data-offers-load'].disabled, true);
  s.timers.shift().callback();
  await flush();
  assert.equal(s.offerCalls().length, 3);
  assert.equal(s.offerCalls()[2].url, '/api/offers?currency=EUR&days=3');
  assert.equal(s.timers.length, 0);
  assert.equal(s.controls['data-offers-load'].disabled, false);
});

test('invalid or inaccessible stored preferences do not break default currency loading', async () => {
  for (const options of [{ storage: new Map([['kate_currency', 'INVALID']]) }, { storageBlocked: true }]) {
    const s = setup(options);
    assert.equal(s.controls['data-offer-currency'].value, 'USD');
    s.changeCurrency('EUR');
    await s.submit();
    assert.equal(s.offerCalls()[0].url, '/api/offers?currency=EUR&days=3');
    assert.equal(s.controls['data-offers-results'].children.length, 3);
  }
});

test('public dynamic price and duration use the active German locale and translation wrapper', async () => {
  const calls = [];
  const i18n = { locale: 'de', t(text, params = {}) {
    calls.push(text);
    const labels = { 'From {price}': 'Ab {price}', 'Supplier duration: {duration}': 'Dauer: {duration}',
      '{count} days': '{count} Tage' };
    return (labels[text] || text).replace(/\{(\w+)\}/g, (match, key) => params[key] ?? match);
  } };
  const s = setup({ i18n });
  s.setResponse(async () => ({ ok: true, json: async () => ({ offers: [
    { product_id: 'de', title: 'Supplier title', from_price: 1234.56, currency: 'EUR', duration_minutes: 3600 },
  ] }) }));
  await s.submit();
  const card = s.controls['data-offers-results'].children[0];
  assert.match(card.children[1].textContent, /^Ab .*1\.234,56/);
  assert.equal(card.children[2].textContent, 'Dauer: 2,5 Tage');
  assert.ok(calls.includes('Loading supplier product previews…'));
});

test('all loaded offer sections refresh together while unrequested sections stay idle', async () => {
  const s = setup({ extraSection: true });
  await s.submit();
  s.changeCurrency('EUR');
  await flush();
  assert.equal(s.extraControls['data-offer-currency'].value, 'EUR');
  assert.equal(s.offerCalls().length, 2, 'The unrequested section must not create an extra call.');
  await s.extraControls['data-offers-load'].listeners.click();
  assert.equal(s.offerCalls().at(-1).url, '/api/offers?currency=EUR&category=nairobi');
  s.changeCurrency('CHF');
  assert.equal(s.controls['data-offers-results'].children.length, 0);
  assert.equal(s.extraControls['data-offers-results'].children.length, 0);
  await flush();
  assert.equal(s.offerCalls().length, 5);
  assert.ok(s.offerCalls().slice(-2).every(({ url }) => url.includes('currency=CHF')));
  assert.equal(s.offerCalls().at(-1).url, '/api/offers?currency=CHF&category=nairobi');
  for (const controls of [s.controls, s.extraControls]) {
    assert.equal(controls['data-offer-currency'].value, 'CHF');
    assert.match(controls['data-offers-results'].children[0].children[1].textContent, /CHF/);
  }
});

test('a late JSON body from a superseded currency cannot replace current prices', async () => {
  const s = setup();
  let finishOldBody;
  s.setResponse(async () => ({ ok: true, json: () => new Promise((resolve) => { finishOldBody = resolve; }) }));
  await s.submit();
  s.setResponse(async () => ({ ok: true, json: async () => ({ offers: [
    { product_id: 'eur', title: 'Current EUR offer', from_price: 40, currency: 'EUR' },
  ] }) }));
  s.changeCurrency('EUR');
  await flush();
  finishOldBody({ offers: [{ product_id: 'old', title: 'Old USD offer', from_price: 50, currency: 'USD' }] });
  await flush();
  assert.equal(s.controls['data-offers-results'].children[0].children[0].textContent, 'Current EUR offer');
  assert.equal(s.controls['data-offers-load'].disabled, false);
});

test('Nairobi and Mara fragment links only load their corresponding section once', async () => {
  const idle = setup({ extraSection: true });
  await flush();
  assert.equal(idle.offerCalls().length, 0);
  const s = setup({ extraSection: true, hash: '#nairobi-extras' });
  await flush();
  assert.equal(s.offerCalls().length, 1);
  assert.equal(s.offerCalls()[0].url, '/api/offers?currency=USD&category=nairobi');
  assert.equal(s.controls['data-offers-results'].children.length, 0);
  assert.equal(s.extraControls['data-offers-results'].children.length, 3);
  const handoff = s.extraControls['data-offers-results'].children[0].children.at(-1);
  assert.equal(handoff.action, '/api/affiliate-click');
  assert.equal(handoff.children.find((input) => input.name === 'page').value, '/mara');
  s.listeners.hashchange();
  await flush();
  assert.equal(s.offerCalls().length, 1);
  s.window.location.hash = '#safari-options';
  s.listeners.hashchange();
  await flush();
  assert.equal(s.offerCalls().length, 2);
  assert.equal(s.offerCalls()[1].url, '/api/offers?currency=USD&days=3');
  s.window.location.hash = '#nairobi-extras';
  s.listeners.hashchange();
  await flush();
  assert.equal(s.offerCalls().length, 2);
});

test('Nairobi extras use their category through currency reload and one rate-limit retry', async () => {
  const s = setup({ extraSection: true });
  await s.extraControls['data-offers-load'].listeners.click();
  s.setResponse(async () => ({ ok: false, status: 429, json: async () => ({}) }));
  s.changeCurrency('GBP');
  assert.equal(s.extraControls['data-offers-results'].children.length, 0);
  await flush();
  assert.equal(s.offerCalls().at(-1).url, '/api/offers?currency=GBP&category=nairobi');
  assert.match(s.extraControls['data-offers-status'].textContent, /Nairobi activities are busy/);
  s.timers.shift().callback();
  await flush();
  assert.equal(s.offerCalls().length, 3);
  assert.equal(s.offerCalls().at(-1).url, '/api/offers?currency=GBP&category=nairobi');
  assert.equal(s.timers.length, 0);
  assert.match(s.extraControls['data-offers-status'].textContent, /Nairobi activities are still busy/);
  assert.equal(s.extraControls['data-offers-load'].disabled, false);
  assert.equal(s.controls['data-offers-results'].children.length, 0);
});

test('unknown template categories cannot introduce arbitrary offer queries', async () => {
  const s = setup({ category: 'unexpected&currency=OTHER' });
  await s.submit();
  assert.equal(s.offerCalls()[0].url, '/api/offers?currency=USD&days=3');
});
