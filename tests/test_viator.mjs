import test from 'node:test';
import assert from 'node:assert/strict';
import { searchMaraOffers, searchNairobiOffers } from '../supabase/functions/kate-api/viator.js';

const fixture = (code = '427094P4') => ({ productCode: code, title: '3 Days Maasai Mara Safari',
  productUrl: `https://www.viator.com/tours/Nairobi/Mara/d5280-${code}?pid=P00323912&mcid=42383`,
  duration: { fixedDurationInMinutes: 4320 }, pricing: { summary: { fromPrice: 350 }, currency: 'USD' },
  reviews: { combinedAverageRating: 4.8, totalReviews: 20 } });
const respond = (products) => async () => new Response(JSON.stringify({ products }), { status: 200 });

test('basic supplier search uses fixed server endpoint, correct headers and date filters', async () => {
  let request;
  const offers = await searchMaraOffers({ apiKey: 'key-fixture', targetDate: '2026-12-01',
    fetchImpl: async (url, init) => { request = { url, init }; return respond([fixture()])(); } });
  assert.equal(request.url, 'https://api.viator.com/partner/products/search?campaign-value=kate-mara');
  assert.equal(request.init.headers['exp-api-key'], 'key-fixture');
  assert.equal(request.init.headers.Accept, 'application/json;version=2.0');
  assert.equal(request.init.redirect, 'error');
  const body = JSON.parse(request.init.body);
  assert.equal(body.filtering.destination, '5280');
  assert.equal(body.filtering.startDate, '2026-12-01');
  assert.equal(body.filtering.endDate, '2026-12-01');
  assert.deepEqual(body.filtering.durationInMinutes, { from: 4320, to: 4320 });
  assert.equal(offers[0].from_price, 350);
  assert.equal(offers[0].availability_checked, false);
  assert.equal(JSON.stringify(offers).includes('key-fixture'), false);
});

test('requested trip length excludes longer catalog itineraries', async () => {
  let filtering;
  const longer = { ...fixture('88888P1'), duration: { fixedDurationInMinutes: 5760 } };
  const offers = await searchMaraOffers({ apiKey: 'fixture', days: 3,
    fetchImpl: async (url, init) => { filtering = JSON.parse(init.body).filtering; return respond([longer, fixture()])(); } });
  assert.deepEqual(filtering.durationInMinutes, { from: 4320, to: 4320 });
  assert.deepEqual(offers.map((offer) => offer.product_id), ['427094P4']);
});

test('irrelevant, inactive, duplicate and unsafe affiliate entries are excluded', async () => {
  const bad = ['http://www.viator.com/tours/a/d5280-427094P4?pid=P00323912',
    'https://evil.example/tours/a/d5280-427094P4?pid=P00323912',
    'https://user:pass@www.viator.com/tours/a/d5280-427094P4?pid=P00323912',
    'https://www.viator.com/tours/a/d5280-427094P4',
    'https://www.viator.com/tours/a/d5280-OTHER?pid=P00323912',
    'https://www.viator.com/tours/a/d5280-427094P4?pid=P00323912&pid=P999',
  ].map((productUrl) => ({ ...fixture(), productUrl }));
  const offers = await searchMaraOffers({ apiKey: 'key-fixture', fetchImpl: respond([
    ...bad, { ...fixture(), title: 'Nairobi walking tour' }, { ...fixture(), status: 'INACTIVE' },
    { ...fixture(), duration: { fixedDurationInMinutes: 60 } }, fixture(), fixture(), fixture('107758P7'),
    fixture('260078P150'), fixture('88888P1'),
  ]) });
  assert.deepEqual(offers.map((offer) => offer.product_id), ['427094P4', '107758P7', '260078P150']);
});

test('unverified price/rating types are never coerced into supplier facts', async () => {
  const item = fixture();
  item.pricing.summary.fromPrice = '350';
  item.reviews.combinedAverageRating = 8;
  item.reviews.totalReviews = '20';
  const [offer] = await searchMaraOffers({ apiKey: 'key-fixture', fetchImpl: respond([item]) });
  assert.equal(offer.from_price, null);
  assert.equal(offer.rating, null);
  assert.equal(offer.review_count, null);
});

test('authentication/rate/server errors expose typed safe errors without supplier bodies', async () => {
  for (const [status, code] of [[401, 'supplier_authentication'], [403, 'supplier_authentication'],
    [429, 'supplier_rate_limit'], [500, 'supplier_unavailable']]) {
    await assert.rejects(searchMaraOffers({ apiKey: 'private-key',
      fetchImpl: async () => new Response('private-key raw-body', { status }) }),
    (error) => error.code === code && !error.message.includes('private-key') && !error.message.includes('raw-body'));
  }
});

test('missing credentials and malformed/oversized supplier payloads fail closed', async () => {
  await assert.rejects(searchMaraOffers({ apiKey: '', fetchImpl: () => { throw new Error('must not run'); } }),
    (error) => error.code === 'supplier_key_missing');
  for (const body of ['not json', '{}', 'x'.repeat(2 * 1024 * 1024 + 1)]) {
    await assert.rejects(searchMaraOffers({ apiKey: 'fixture', fetchImpl: async () => new Response(body) }),
      (error) => error.code === 'supplier_invalid_response');
  }
});

const activityFixture = (code = '56789P1') => ({ ...fixture(code), title: 'Nairobi National Park Morning Tour',
  status: 'ACTIVE', duration: { fixedDurationInMinutes: 240 } });

test('Nairobi search uses a separate fixed campaign and bounded activity filters with honest durations', async () => {
  let request;
  const variable = { ...activityFixture('56789P2'), duration: { fixedDurationInMinutes: null, variableDurationFromMinutes: 180, variableDurationToMinutes: 360 } };
  const offers = await searchNairobiOffers({ apiKey: 'key-fixture', targetDate: '2026-12-01', fetchImpl: async (url, init) => {
    request = { url, init }; return respond([activityFixture(), variable])();
  } });
  assert.equal(request.url, 'https://api.viator.com/partner/products/search?campaign-value=kate-nairobi');
  const body = JSON.parse(request.init.body);
  assert.equal(body.filtering.destination, '5280');
  assert.deepEqual(body.filtering.durationInMinutes, { from: 1, to: 720 });
  assert.equal(body.filtering.startDate, '2026-12-01');
  assert.equal(offers[0].duration_minutes, 240);
  assert.equal(offers[1].duration_minutes, null);
  assert.equal(offers[1].duration_min_minutes, 180);
  assert.equal(offers[1].duration_max_minutes, 360);
  assert.equal(offers.every((offer) => offer.availability_checked === false), true);
});

test('Nairobi activities reject unproven, coerced, long and contradictory supplier durations', async () => {
  const invalid = [undefined, {}, { fixedDurationInMinutes: 0 }, { fixedDurationInMinutes: -1 },
    { fixedDurationInMinutes: 721 }, { fixedDurationInMinutes: '240' },
    { variableDurationFromMinutes: 60 }, { variableDurationFromMinutes: 0, variableDurationToMinutes: 120 },
    { variableDurationFromMinutes: 120, variableDurationToMinutes: 60 },
    { variableDurationFromMinutes: 60, variableDurationToMinutes: 721 },
    { variableDurationFromMinutes: '60', variableDurationToMinutes: 120 },
    { fixedDurationInMinutes: 120, variableDurationFromMinutes: 60, variableDurationToMinutes: 120 }];
  const offers = await searchNairobiOffers({ apiKey: 'fixture', fetchImpl: respond([
    ...invalid.map((duration, i) => ({ ...activityFixture(`56789P${i + 10}`), duration })),
    { ...activityFixture(), duration: { fixedDurationInMinutes: 720, variableDurationFromMinutes: null, variableDurationToMinutes: null } },
  ]) });
  assert.deepEqual(offers.map((offer) => offer.product_id), ['56789P1']);
  assert.equal(offers[0].duration_max_minutes, 720);
});

test('Nairobi excludes Mara, multi-day, overnight, unrelated and explicitly nonactive catalogue titles', async () => {
  const titles = ['Nairobi to Maasai Mara', 'Nairobi Masai Mara Safari', 'Nairobi 2-Day Safari',
    'Three Days Safari from Nairobi', 'Nairobi 1 Night Safari', 'Nairobi Overnight Safari', 'Nairobi multi-day safari', 'Mombasa Walking Tour'];
  const offers = await searchNairobiOffers({ apiKey: 'fixture', fetchImpl: respond([
    ...titles.map((title, i) => ({ ...activityFixture(`56789P${i + 10}`), title })),
    { ...activityFixture('56789P40'), status: 'INACTIVE' }, { ...activityFixture('56789P41'), status: 'DRAFT' }, activityFixture(),
  ]) });
  assert.deepEqual(offers.map((offer) => offer.product_id), ['56789P1']);
});

test('Nairobi retains strict affiliate URL and price/currency type protections', async () => {
  const unsafe = [
    'http://www.viator.com/tours/Nairobi/a/d5280-56789P1?pid=P00323912',
    'https://evil.example/tours/Nairobi/a/d5280-56789P1?pid=P00323912',
    'https://www.viator.com/tours/Nairobi/a/d5280-OTHER?pid=P00323912',
    'https://www.viator.com/tours/Nairobi/a/d5280-56789P1?pid=P00323912&pid=P1',
  ].map((productUrl) => ({ ...activityFixture(), productUrl }));
  const missingPrice = { ...activityFixture(), pricing: { summary: { fromPrice: '100' }, currency: 'USD' } };
  const wrongCurrency = { ...activityFixture('56789P2'), pricing: { summary: { fromPrice: 100 }, currency: 'EUR' } };
  const negativePrice = { ...activityFixture('56789P3'), pricing: { summary: { fromPrice: -1 }, currency: 'USD' } };
  const offers = await searchNairobiOffers({ apiKey: 'fixture', fetchImpl: respond([...unsafe, missingPrice, wrongCurrency, negativePrice]) });
  assert.deepEqual(offers.map((offer) => offer.product_id), ['56789P1', '56789P2', '56789P3']);
  assert.equal(offers.every((offer) => offer.from_price === null), true);
  await assert.rejects(searchNairobiOffers({ apiKey: 'fixture', currency: 'XYZ', fetchImpl: respond([]) }), (error) => error.code === 'supplier_invalid_request');
});
