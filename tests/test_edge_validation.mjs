import test from 'node:test';
import assert from 'node:assert/strict';
import { buildItinerary, validatePageView, validatePlan } from '../supabase/functions/kate-api/validation.js';

test('valid Planner payload preserves the original limits and normalized inputs', () => {
  const result = validatePlan({
    origin: ' Nairobi ', focus: 'maasai_mara', days: 3, travelers: 2,
    budget: 1200, currency: 'CHF', interests: ['wildlife', 'photography', 'wildlife'],
    comfort: 'balanced', target_date: '', flexibility: 'not_sure',
  });
  assert.equal(result.error, undefined);
  assert.deepEqual(result.value.interests, ['photography', 'wildlife']);
  assert.equal(result.value.origin, 'Nairobi');
  assert.equal(result.value.budget, 1200);
});

test('invalid Planner bounds, dates, and types are rejected', () => {
  assert.match(validatePlan({ origin: '', days: 3, travelers: 2 }).error, /starting point/);
  assert.match(validatePlan({ origin: 'Nairobi', days: 22, travelers: 2 }).error, /Trip length/);
  assert.match(validatePlan({ origin: 'Nairobi', days: 3, travelers: 21 }).error, /Travelers/);
  assert.match(validatePlan({ origin: 'Nairobi', days: 3, travelers: 2, target_date: '2026-02-31' }).error, /valid date/);
  assert.match(validatePlan({ origin: 'Nairobi', days: 3, travelers: 2, interests: 'wildlife' }).error, /valid interests/);
});

test('outline matches the original one-day and three-day itinerary behavior', () => {
  const one = buildItinerary({ origin: 'Nairobi', days: 1, focus: 'maasai_mara', interests: [] });
  assert.equal(one.length, 1);
  assert.equal(one[0].title, 'One-day planning window');
  const three = buildItinerary({ origin: 'Nairobi', days: 3, focus: 'maasai_mara', interests: ['wildlife'] });
  assert.deepEqual(three.map((item) => item.day), ['DAY 01', 'DAY 02', 'DAY 03']);
  assert.equal(three[1].title, 'Day 2 · Your main priorities');
  assert.equal(three[2].title, 'Return and final checks');
  assert.match(three[2].detail, /total party price/);
});

test('page-view tracking accepts only known routes', () => {
  assert.equal(validatePageView({ page: '/' }), '/');
  assert.equal(validatePageView({ page: '/planner/' }), '/planner');
  assert.equal(validatePageView({ page: '/admin' }), null);
  assert.equal(validatePageView({ page: 42 }), null);
});
