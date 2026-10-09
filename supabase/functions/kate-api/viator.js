const API_URL = 'https://api.viator.com/partner/products/search';
const CURRENCIES = new Set(['USD', 'EUR', 'GBP', 'CHF']);
const MAX_RESPONSE_BYTES = 2 * 1024 * 1024;

function supplierError(code) {
  return Object.assign(new Error('Supplier previews unavailable.'), { code });
}

function affiliateUrl(value, productId) {
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password || url.port || url.hash
      || !['www.viator.com', 'viator.com'].includes(url.hostname)
      || !url.pathname.startsWith('/tours/') || !url.pathname.endsWith(`-${productId}`)
      || url.searchParams.getAll('pid').length !== 1 || !/^P\d+$/.test(url.searchParams.get('pid') || '')) return null;
    return url.toString();
  } catch { return null; }
}

async function boundedJson(response) {
  if (!response.body || Number(response.headers.get('content-length') || 0) > MAX_RESPONSE_BYTES) {
    throw supplierError('supplier_invalid_response');
  }
  const reader = response.body.getReader();
  const chunks = [];
  let size = 0;
  while (true) {
    const chunk = await reader.read();
    if (chunk.done) break;
    size += chunk.value.byteLength;
    if (size > MAX_RESPONSE_BYTES) {
      await reader.cancel();
      throw supplierError('supplier_invalid_response');
    }
    chunks.push(chunk.value);
  }
  const buffer = new Uint8Array(size);
  let position = 0;
  for (const chunk of chunks) { buffer.set(chunk, position); position += chunk.byteLength; }
  try { return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(buffer)); }
  catch { throw supplierError('supplier_invalid_response'); }
}

function activityDuration(duration) {
  const fixed = duration?.fixedDurationInMinutes;
  const minimum = duration?.variableDurationFromMinutes;
  const maximum = duration?.variableDurationToMinutes;
  if (fixed != null) {
    if (!Number.isFinite(fixed) || fixed <= 0 || fixed > 720 || minimum != null || maximum != null) return null;
    return { duration_minutes: fixed, duration_min_minutes: fixed, duration_max_minutes: fixed };
  }
  if (!Number.isFinite(minimum) || !Number.isFinite(maximum) || minimum <= 0 || maximum < minimum || maximum > 720) return null;
  return { duration_minutes: null, duration_min_minutes: minimum, duration_max_minutes: maximum };
}

function nairobiActivityTitle(title) {
  return /\bnairobi\b/i.test(title)
    && !/\b(?:masai|maasai)\s+mara\b|\bmara\b|\bovernight\b|\bmulti[ -]?day\b|\b(?:[2-9]|\d{2,}|two|three|four|five|six|seven|eight|nine|ten)[ -]*days?\b|\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)[ -]*nights?\b/i.test(title);
}

async function searchOffers({ apiKey, currency = 'USD', targetDate = null, days = 3, category, fetchImpl = fetch }) {
  if (typeof apiKey !== 'string' || !apiKey.trim()) throw supplierError('supplier_key_missing');
  if (!CURRENCIES.has(currency)) throw supplierError('supplier_invalid_request');
  if (category === 'mara' && ![2, 3, 4].includes(days)) throw supplierError('supplier_invalid_request');
  if (targetDate && !/^\d{4}-\d{2}-\d{2}$/.test(targetDate)) throw supplierError('supplier_invalid_request');
  const filtering = { destination: '5280', durationInMinutes: category === 'nairobi'
    ? { from: 1, to: 720 } : { from: days * 1440, to: days * 1440 } };
  if (targetDate) Object.assign(filtering, { startDate: targetDate, endDate: targetDate });
  let response;
  try {
    response = await fetchImpl(`${API_URL}?campaign-value=kate-${category}`, {
      method: 'POST', redirect: 'error', signal: AbortSignal.timeout(15000),
      headers: { 'exp-api-key': apiKey, 'Accept': 'application/json;version=2.0',
        'Accept-Language': 'en-US', 'Content-Type': 'application/json' },
      body: JSON.stringify({ filtering, sorting: { sort: 'TRAVELER_RATING', order: 'DESCENDING' },
        pagination: { start: 1, count: 20 }, currency }),
    });
  } catch { throw supplierError('supplier_unavailable'); }
  if (!response.ok) {
    await response.body?.cancel();
    if ([401, 403].includes(response.status)) throw supplierError('supplier_authentication');
    if (response.status === 429) throw supplierError('supplier_rate_limit');
    throw supplierError('supplier_unavailable');
  }
  const payload = await boundedJson(response);
  if (!payload || !Array.isArray(payload.products)) throw supplierError('supplier_invalid_response');
  const checkedAt = new Date().toISOString();
  const offers = [];
  const seen = new Set();
  // Search returns active catalogue entries; this is not an exact party/date availability check.
  for (const product of payload.products.slice(0, 50)) {
    const id = product?.productCode;
    const title = product?.title;
    if (typeof id !== 'string' || !/^[A-Za-z0-9_-]{1,80}$/.test(id) || seen.has(id)
      || typeof title !== 'string' || !(category === 'nairobi' ? nairobiActivityTitle(title) : /\b(?:masai|maasai)\s+mara\b/i.test(title))
      || product.status === 'INACTIVE') continue;
    // Search serves active catalogue entries. If a status is explicitly supplied,
    // a Nairobi activity must not contradict that active-catalogue provenance.
    if (category === 'nairobi' && product.status !== undefined && product.status !== 'ACTIVE') continue;
    const url = affiliateUrl(product.productUrl, id);
    if (!url) continue;
    const minutes = product.duration?.fixedDurationInMinutes;
    const activity = category === 'nairobi' ? activityDuration(product.duration) : null;
    if (category === 'nairobi' ? !activity : Number.isFinite(minutes) && minutes !== days * 1440) continue;
    const price = product.pricing?.summary?.fromPrice;
    const supplierCurrency = product.pricing?.currency;
    const rating = product.reviews?.combinedAverageRating;
    const reviewCount = product.reviews?.totalReviews;
    seen.add(id);
    offers.push({ product_id: id, title: title.slice(0, 300), affiliate_url: url,
      from_price: supplierCurrency === currency && Number.isFinite(price) && price >= 0 ? price : null,
      currency, duration_minutes: Number.isFinite(minutes) && minutes > 0 ? minutes : null,
      ...(activity || {}),
      rating: Number.isFinite(rating) && rating >= 0 && rating <= 5 ? rating : null,
      review_count: Number.isInteger(reviewCount) && reviewCount >= 0 ? reviewCount : null,
      checked_at: checkedAt, availability_checked: false, price_basis: 'supplier_from_price' });
    if (offers.length === 3) break;
  }
  return offers;
}

export async function searchMaraOffers(options) {
  return searchOffers({ ...options, category: 'mara' });
}

export async function searchNairobiOffers(options) {
  return searchOffers({ ...options, category: 'nairobi' });
}
