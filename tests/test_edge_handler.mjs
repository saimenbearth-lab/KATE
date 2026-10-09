import test from 'node:test';
import assert from 'node:assert/strict';
import { createHandler } from '../supabase/functions/kate-api/handler.js';

const target = 'https://www.viator.com/tours/Nairobi/Mara/d5280-427094P4?pid=P00323912&mcid=42383';
const upstream = { products: [{ productCode: '427094P4', title: '3 Days Masai Mara Safari',
  productUrl: target, duration: { fixedDurationInMinutes: 4320 },
  pricing: { summary: { fromPrice: 350 }, currency: 'USD' },
  reviews: { combinedAverageRating: 4.8, totalReviews: 25 } }] };

function setup({ vars = {}, rpcError = null, lease = true, upstreamValue = upstream, fetchError = null } = {}) {
  const memory = new Map();
  const calls = [];
  let fetches = 0;
  const db = {
    from(table) {
      let key;
      return {
        select() { return this; }, eq(column, value) { key = value; return this; },
        async maybeSingle() { return { data: memory.get(key) || null, error: null }; },
        async upsert(value, options) {
          calls.push({ table, value, options });
          if (table === 'business_memory') memory.set(value.key, value);
          return { error: null };
        },
        async insert(value) { calls.push({ table, value }); return { error: null }; },
      };
    },
    async rpc(name, args) {
      calls.push({ rpc: name, args });
      if (rpcError) return { error: rpcError, data: null };
      if (name === 'claim_viator_search') return { data: lease, error: null };
      if (name === 'record_catalogue_click') return { data: target, error: null };
      if (name === 'kate_control_summary') return { data: { events: {}, revenue: [] }, error: null };
      return { data: null, error: null };
    },
  };
  const handler = createHandler({ dbFactory: () => db, env: (name) => vars[name],
    fetchImpl: async () => { fetches++; if (fetchError) throw fetchError;
      return new Response(JSON.stringify(upstreamValue), { status: 200 }); } });
  return { handler, calls, memory, fetches: () => fetches };
}

function post(path, data, secret) {
  return new Request(`https://kate.example/api/${path}`, { method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(secret ? { Authorization: `Bearer ${secret}` } : {}) },
    body: JSON.stringify(data) });
}

test('Nairobi guide page views use a separate intent in both languages', async () => {
  const canonical = '/guides/nairobi-airport-transfers-and-safari-extras';
  for (const page of [canonical + '/', '/de' + canonical + '/']) {
    const { handler, calls, fetches } = setup();
    const response = await handler(post('event', { event_type: 'page_view', page }));
    assert.equal(response.status, 202);
    assert.equal(fetches(), 0);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].value.page, canonical);
    assert.equal(calls[0].value.intent, 'nairobi_transfer_and_activity_planning');
    assert.equal(calls[0].value.event_type, 'page_view');
  }
});

test('health exposes presence flags without credentials or business data', async () => {
  const s = setup({ vars: { VIATOR_API_KEY: 'private-supplier-key' } });
  const response = await s.handler(new Request('https://kate.example/api/health'));
  const value = await response.json();
  assert.equal(value.viator_configured, true);
  assert.equal(value.admin_configured, false);
  assert.equal(JSON.stringify(value).includes('private-supplier-key'), false);
  assert.equal(s.calls.length, 0);
});

test('control denies missing or wrong credentials and permits a configured admin', async () => {
  for (const [vars, authorization, expected] of [ [{}, '', 503],
    [{ KATE_ADMIN_SECRET: 'admin-fixture' }, 'Bearer wrong', 401],
    [{ KATE_ADMIN_SECRET: 'admin-fixture' }, 'Bearer admin-fixture', 200] ]) {
    const s = setup({ vars });
    const response = await s.handler(new Request('https://kate.example/api/control', { headers: { authorization } }));
    assert.equal(response.status, expected);
    assert.equal(s.calls.some((call) => call.rpc === 'kate_control_summary'), expected === 200);
  }
});

test('offers fail gracefully before supplier calls when the key is absent', async () => {
  const s = setup();
  const response = await s.handler(new Request('https://kate.example/api/offers'));
  assert.equal(response.status, 503);
  assert.equal(s.fetches(), 0);
});

test('offers reject invalid currencies and complete invalid dates before supplier calls', async () => {
  for (const query of ['currency=XYZ', 'days=5', 'category=', 'category=other', 'category=Nairobi',
    'category=nairobi&currency=XYZ', 'category=nairobi&days=5', 'category=nairobi&target_date=2026-02-31',
    'target_date=2026-10-07extra', 'target_date=2026-02-31']) {
    const s = setup({ vars: { VIATOR_API_KEY: 'key-fixture' } });
    const response = await s.handler(new Request(`https://kate.example/api/offers?${query}`));
    assert.equal(response.status, 400, query);
    assert.equal(s.fetches(), 0);
  }
});

test('Nairobi activity API stores separate honest context and cache without exposing affiliate URLs', async () => {
  const activity = { ...upstream.products[0], productCode: '56789P1', title: 'Nairobi National Park Morning Tour',
    productUrl: 'https://www.viator.com/tours/Nairobi/Park/d5280-56789P1?pid=P00323912',
    status: 'ACTIVE', duration: { variableDurationFromMinutes: 180, variableDurationToMinutes: 360 } };
  const s = setup({ vars: { VIATOR_API_KEY: 'key-fixture' }, upstreamValue: { products: [activity] } });
  // Existing Mara cache cannot masquerade as a Nairobi response.
  s.memory.set('viator_offers:USD:3:any', { value: JSON.stringify({ offers: [{ product_id: 'mara-cache' }] }), updated_at: new Date().toISOString() });
  for (let i = 0; i < 2; i++) {
    const response = await s.handler(new Request('https://kate.example/api/offers?category=nairobi&currency=USD'));
    assert.equal(response.status, 200);
    const value = await response.json();
    assert.equal(value.category, 'nairobi');
    assert.equal(value.offers[0].product_id, '56789P1');
    assert.equal(value.offers[0].affiliate_url, undefined);
    assert.equal(value.offers[0].duration_minutes, null);
    assert.equal(value.offers[0].duration_max_minutes, 360);
    assert.equal(value.availability_checked, false);
  }
  assert.equal(s.fetches(), 1);
  const saved = s.calls.find((call) => call.table === 'products').value[0];
  assert.equal(saved.category, 'activity');
  assert.equal(saved.comparison_id, 'nairobi-short-activities');
  assert.equal(saved.destination_text, 'Nairobi, Kenya');
  assert.equal(saved.snapshot_context.comparison_context, 'nairobi_optional_extras');
  assert.equal(saved.snapshot_context.duration_min_minutes, 180);
  assert.equal(saved.snapshot_context.catalogue_status, 'ACTIVE');
  assert.equal(saved.date_availability_confirmed, false);
  assert.equal(saved.price_basis_confirmed, false);
  assert.equal(s.memory.has('viator_offers:nairobi:USD:1-720:any'), true);
});

test('Nairobi searches share the global refresh lease and reject other affiliate accounts', async () => {
  const activity = { ...upstream.products[0], title: 'Nairobi Morning Tour', duration: { fixedDurationInMinutes: 120 },
    productUrl: target.replace('P00323912', 'P00000001') };
  const blocked = setup({ vars: { VIATOR_API_KEY: 'fixture' }, lease: false, upstreamValue: { products: [activity] } });
  assert.equal((await blocked.handler(new Request('https://kate.example/api/offers?category=nairobi'))).status, 429);
  assert.equal(blocked.fetches(), 0);
  const wrongPid = setup({ vars: { VIATOR_API_KEY: 'fixture' }, upstreamValue: { products: [activity] } });
  assert.equal((await wrongPid.handler(new Request('https://kate.example/api/offers?category=nairobi'))).status, 503);
  assert.equal(wrongPid.calls.some((call) => call.table === 'products'), false);
});

test('Control Center accepts a server-stored password verifier without an environment secret', async () => {
  const s = setup();
  const fixtureSecret = 'test-only-random-control-token';
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(fixtureSecret));
  const value = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
  s.memory.set('control_admin_secret_sha256', { value });
  const health = await s.handler(new Request('https://kate.example/api/health'));
  assert.equal((await health.json()).admin_configured, true);
  const denied = await s.handler(new Request('https://kate.example/api/control', { headers: { Authorization: 'Bearer wrong' } }));
  assert.equal(denied.status, 401);
  const allowed = await s.handler(new Request('https://kate.example/api/control', { headers: { Authorization: `Bearer ${fixtureSecret}` } }));
  assert.equal(allowed.status, 200);
  assert.equal((await allowed.text()).includes(value), false);
});

test('supplier previews store provenance, hide redirect URLs, and cache repeat requests', async () => {
  const s = setup({ vars: { VIATOR_API_KEY: 'key-fixture' } });
  for (let i = 0; i < 2; i++) {
    const response = await s.handler(new Request('https://kate.example/api/offers?currency=USD'));
    assert.equal(response.status, 200);
    const data = await response.json();
    assert.equal(data.offers.length, 1);
    assert.equal(data.offers[0].affiliate_url, undefined);
    assert.equal(data.offers[0].from_price, 350);
    assert.equal(data.availability_checked, false);
  }
  assert.equal(s.fetches(), 1);
  const saved = s.calls.find((call) => call.table === 'products').value[0];
  assert.equal(saved.snapshot_context.catalogue_status, 'ACTIVE');
  assert.equal(saved.date_availability_confirmed, false);
  assert.equal(saved.price_basis_confirmed, false);
  assert.equal(saved.affiliate_url, target);
});

test('refresh lease prevents duplicate upstream bursts', async () => {
  const s = setup({ vars: { VIATOR_API_KEY: 'key-fixture' }, lease: false });
  const response = await s.handler(new Request('https://kate.example/api/offers'));
  assert.equal(response.status, 429);
  assert.equal(s.fetches(), 0);
});

test('upstream failures do not disclose raw responses or credentials', async () => {
  const s = setup({ vars: { VIATOR_API_KEY: 'private-key' }, fetchError: new Error('private-key supplier-body') });
  const response = await s.handler(new Request('https://kate.example/api/offers'));
  assert.equal(response.status, 503);
  const body = await response.text();
  assert.equal(body.includes('private-key'), false);
  assert.equal(body.includes('supplier-body'), false);
});

test('supplier URLs with another affiliate account are never stored', async () => {
  const wrong = structuredClone(upstream);
  wrong.products[0].productUrl = target.replace('P00323912', 'P00000001');
  const s = setup({ vars: { VIATOR_API_KEY: 'key-fixture' }, upstreamValue: wrong });
  const response = await s.handler(new Request('https://kate.example/api/offers'));
  assert.equal(response.status, 503);
  assert.equal(s.calls.some((call) => call.table === 'products'), false);
});

test('native click-out forms produce a tracked 303 handoff with planner attribution', async () => {
  const s = setup();
  const response = await s.handler(new Request('https://kate.example/api/affiliate-click', {
    method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: 'product_id=427094P4&page=%2Fplanner',
  }));
  assert.equal(response.status, 303);
  assert.equal(response.headers.get('location'), target);
  assert.equal(s.calls[0].rpc, 'record_catalogue_click');
  assert.equal(s.calls[0].args.p_page, '/planner');
});

test('expired catalogue clicks return 409 without a redirect', async () => {
  const s = setup({ rpcError: { code: 'P0001', message: 'no_verified_affiliate' } });
  const response = await s.handler(post('affiliate-click', { product_id: '427094P4' }));
  assert.equal(response.status, 409);
  assert.equal(response.headers.get('location'), null);
});

test('oversized public JSON and form bodies are rejected before activity writes', async () => {
  for (const [path, type, body] of [['plan', 'application/json', JSON.stringify({ origin: 'x'.repeat(9000) })],
    ['affiliate-click', 'application/x-www-form-urlencoded', `product_id=${'x'.repeat(9000)}`]]) {
    const s = setup();
    const response = await s.handler(new Request(`https://kate.example/api/${path}`, {
      method: 'POST', headers: { 'Content-Type': type }, body,
    }));
    assert.equal(response.status, 400);
    assert.equal(s.calls.length, 0);
  }
});

test('revenue rejects coercible nonnumeric values and unidentifiable report rows', async () => {
  const base = { source: 'viator-report', external_event_id: 'booking-1', amount: 28, currency: 'USD',
    recorded_at: '2026-10-06T12:00:00Z', evidence_note: 'Approved commission report fixture' };
  for (const amount of [null, false, '', '28', [], {}]) {
    const s = setup({ vars: { KATE_ADMIN_SECRET: 'admin-fixture' } });
    const response = await s.handler(post('revenue', { ...base, amount }, 'admin-fixture'));
    assert.equal(response.status, 400);
    assert.equal(s.calls.length, 0);
  }
  const s = setup({ vars: { KATE_ADMIN_SECRET: 'admin-fixture' } });
  assert.equal((await s.handler(post('revenue', { ...base, external_event_id: '' }, 'admin-fixture'))).status, 400);
});

test('repeated conversion and revenue imports use stable IDs and ignore duplicates', async () => {
  for (const path of ['conversions', 'revenue']) {
    const s = setup({ vars: { KATE_ADMIN_SECRET: 'admin-fixture' } });
    const data = { source: 'viator-report', external_event_id: 'booking-1', amount: 28, currency: 'USD',
      event_time: '2026-10-06T12:00:00Z', recorded_at: '2026-10-06T12:00:00Z',
      verification_note: 'Supplier report fixture', evidence_note: 'Supplier report fixture' };
    for (let i = 0; i < 2; i++) assert.equal((await s.handler(post(path, data, 'admin-fixture'))).status, 201);
    assert.equal(s.calls[0].value.id, s.calls[1].value.id);
    assert.equal(s.calls[0].options.ignoreDuplicates, true);
    assert.equal(s.calls[0].options.onConflict, 'id');
  }
});
