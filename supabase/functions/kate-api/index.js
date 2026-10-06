import { createClient } from "npm:@supabase/supabase-js@2";
import { buildItinerary, validatePageView, validatePlan } from "./validation.js";

const MAX_BODY_BYTES = 8192;
const PAGE_INTENTS = {
  "/": "kenya_trip_planning",
  "/planner": "trip_planning",
  "/mara": "mara_3d_decision",
  "/control": "internal_operations",
};

function headers(extra = {}) {
  return {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    ...extra,
  };
}

function jsonResponse(status, payload) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: headers({ "Content-Type": "application/json; charset=utf-8" }),
  });
}

function dbClient() {
  const url = Deno.env.get("SUPABASE_URL");
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!url || !serviceKey) throw new Error("server_configuration_missing");
  return createClient(url, serviceKey, { auth: { persistSession: false, autoRefreshToken: false } });
}

async function readJson(request) {
  const announced = Number(request.headers.get("content-length") || 0);
  if (announced > MAX_BODY_BYTES || !request.body) return { error: "Send a small JSON form payload." };
  const reader = request.body.getReader();
  const chunks = [];
  let size = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAX_BODY_BYTES) {
        await reader.cancel();
        return { error: "Send a small JSON form payload." };
      }
      chunks.push(value);
    }
    if (!size || !(request.headers.get("content-type") || "").toLowerCase().includes("application/json")) {
      return { error: "Send a small JSON form payload." };
    }
    const buffer = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) {
      buffer.set(chunk, offset);
      offset += chunk.byteLength;
    }
    const value = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(buffer));
    if (!value || typeof value !== "object" || Array.isArray(value)) return { error: "Send a small JSON form payload." };
    return { value };
  } catch {
    return { error: "Send a small JSON form payload." };
  }
}

async function equalSecret(candidate, expected) {
  if (!candidate || !expected) return false;
  const encoder = new TextEncoder();
  const [left, right] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(candidate)),
    crypto.subtle.digest("SHA-256", encoder.encode(expected)),
  ]);
  const a = new Uint8Array(left);
  const b = new Uint8Array(right);
  let mismatch = 0;
  for (let i = 0; i < a.length; i += 1) mismatch |= a[i] ^ b[i];
  return mismatch === 0;
}

async function requireAdmin(request) {
  const expected = Deno.env.get("KATE_ADMIN_SECRET");
  if (!expected) return { ok: false, response: jsonResponse(503, { error: "Control Center access is not configured; analytics remain hidden." }) };
  const authorization = request.headers.get("authorization") || "";
  const match = authorization.match(/^Bearer\s+(.+)$/i);
  if (!match || !(await equalSecret(match[1], expected))) {
    return { ok: false, response: jsonResponse(401, { error: "Admin authentication required." }) };
  }
  return { ok: true };
}

function validIsoDate(value) {
  if (typeof value !== "string" || !value.trim()) return false;
  return Number.isFinite(Date.parse(value));
}

async function recordPageView(db, data) {
  const page = validatePageView(data);
  if (!page) return jsonResponse(400, { error: "Choose a supported KATE page." });
  const { error } = await db.from("events").insert({
    event_type: "page_view",
    source: "web",
    page,
    intent: PAGE_INTENTS[page],
  });
  if (error) return jsonResponse(503, { error: "Tracking could not be stored. Please try again." });
  return jsonResponse(202, { ok: true });
}

async function createPlan(db, data) {
  // Preserve the existing funnel semantics: record the start even if validation fails.
  const started = await db.from("events").insert({
    event_type: "planner_started",
    source: "planner_form",
    page: "/planner",
    intent: "kenya_trip_planning",
    position: "form_submit",
  });
  if (started.error) return jsonResponse(503, { error: "Planning storage is unavailable. Please try again." });

  const result = validatePlan(data);
  if (result.error) return jsonResponse(400, { error: result.error });
  const input = result.value;
  const sessionId = crypto.randomUUID();
  const intentId = crypto.randomUUID();
  const intentType = input.focus === "maasai_mara" && input.days === 3 && input.origin.toLowerCase() === "nairobi"
    ? "mara_3d_decision"
    : "kenya_trip_planning";
  const summary = "Illustrative planning outline; live availability and prices not checked.";

  const { error } = await db.rpc("record_planner_completion", {
    p_session_id: sessionId,
    p_intent_id: intentId,
    p_origin: input.origin,
    p_focus: input.focus,
    p_days: input.days,
    p_travelers: input.travelers,
    p_budget: input.budget,
    p_currency: input.currency,
    p_interests: input.interests,
    p_comfort: input.comfort,
    p_target_date: input.targetDate,
    p_flexibility: input.flexibility,
    p_intent_type: intentType,
    p_destination_id: input.focus === "maasai_mara" ? "maasai-mara" : null,
    p_occurred_at: new Date().toISOString(),
    p_output_summary: summary,
  });
  if (error) return jsonResponse(503, { error: "The planning outline could not be saved. Please try again." });

  return jsonResponse(200, {
    session_id: sessionId,
    itinerary: buildItinerary(input),
    planning_inputs: {
      origin: input.origin,
      focus: input.focus === "maasai_mara" ? "Maasai Mara" : "Still deciding",
      days: input.days,
      travelers: input.travelers,
      budget: input.budget === null ? null : { amount: input.budget, currency: input.currency },
      interests: input.interests,
      comfort: input.comfort,
      target_date: input.targetDate,
      date_flexibility: input.flexibility,
    },
    availability_checked: false,
    price_checked: false,
    message: "Planning outline only. No live inventory, supplier availability or price was checked.",
  });
}

async function recordProductView(db, data) {
  const productId = typeof data.product_id === "string" ? data.product_id.slice(0, 80) : "";
  if (!productId) return jsonResponse(400, { error: "Choose a valid product." });
  const { data: product, error } = await db.from("products")
    .select("product_id,availability_state,date_availability_confirmed,affiliate_state,affiliate_url")
    .eq("product_id", productId).maybeSingle();
  if (error) return jsonResponse(503, { error: "Product data is unavailable." });
  if (!product || product.availability_state !== "confirmed" || !product.date_availability_confirmed || product.affiliate_state !== "approved" || !product.affiliate_url) {
    return jsonResponse(409, { error: "No verified public product is available." });
  }
  const { error: insertError } = await db.from("events").insert({
    event_type: "product_view", source: "product_card", page: "/mara",
    intent: "mara_3d_decision", product_id: productId, position: "offer_card",
  });
  if (insertError) return jsonResponse(503, { error: "Product activity could not be stored." });
  return jsonResponse(200, { ok: true });
}

async function recordAffiliateClick(db, data) {
  const productId = typeof data.product_id === "string" ? data.product_id.slice(0, 80) : "";
  if (!productId) return jsonResponse(400, { error: "Choose a valid product." });
  const { data: target, error } = await db.rpc("record_affiliate_click", {
    p_product_id: productId,
    p_clicked_at: new Date().toISOString(),
  });
  if (error) {
    if (error.code === "P0001" || (error.message || "").includes("no_verified_affiliate")) {
      return jsonResponse(409, { error: "No approved affiliate URL and verified availability are configured." });
    }
    return jsonResponse(503, { error: "Affiliate activity could not be stored." });
  }
  let parsed;
  try { parsed = new URL(target); } catch { return jsonResponse(409, { error: "The configured destination is not a valid HTTPS URL." }); }
  if (parsed.protocol !== "https:" || parsed.username || parsed.password) {
    return jsonResponse(409, { error: "The configured destination is not a valid HTTPS URL." });
  }
  return new Response(null, { status: 303, headers: headers({ Location: parsed.toString() }) });
}

async function controlSummary(db, request) {
  const access = await requireAdmin(request);
  if (!access.ok) return access.response;
  const { data, error } = await db.rpc("kate_control_summary");
  if (error || !data) return jsonResponse(503, { error: "Stored aggregates are not available right now." });
  return jsonResponse(200, data);
}

async function ingestConversion(db, request, data) {
  const access = await requireAdmin(request);
  if (!access.ok) return access.response;
  const source = typeof data.source === "string" ? data.source.trim().slice(0, 80) : "";
  const verificationNote = typeof data.verification_note === "string" ? data.verification_note.trim().slice(0, 2000) : "";
  const productId = typeof data.product_id === "string" && data.product_id.trim() ? data.product_id.trim().slice(0, 80) : null;
  const eventTime = data.event_time;
  if (!source || !verificationNote || !validIsoDate(eventTime)) {
    return jsonResponse(400, { error: "A source, valid event time, and evidence-backed verification note are required." });
  }
  const id = crypto.randomUUID();
  const { error } = await db.from("conversions").insert({ id, product_id: productId, event_time: eventTime, source, verification_note: verificationNote });
  if (error) return jsonResponse(400, { error: "Conversion could not be stored; check its product reference and evidence fields." });
  return jsonResponse(201, { id });
}

async function ingestRevenue(db, request, data) {
  const access = await requireAdmin(request);
  if (!access.ok) return access.response;
  const amount = Number(data.amount);
  const currency = typeof data.currency === "string" ? data.currency.trim().toUpperCase() : "";
  const evidenceNote = typeof data.evidence_note === "string" ? data.evidence_note.trim().slice(0, 2000) : "";
  const recordedAt = data.recorded_at;
  if (!Number.isFinite(amount) || amount < 0 || !/^[A-Z]{3}$/.test(currency) || !evidenceNote || !validIsoDate(recordedAt)) {
    return jsonResponse(400, { error: "A non-negative amount, currency, record time, and evidence note are required." });
  }
  const id = crypto.randomUUID();
  const { error } = await db.from("revenue").insert({ id, amount, currency, recorded_at: recordedAt, evidence_note: evidenceNote });
  if (error) return jsonResponse(400, { error: "Revenue could not be stored; verify the currency and evidence fields." });
  return jsonResponse(201, { id });
}

Deno.serve(async (request) => {
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: headers({ Allow: "GET, POST, OPTIONS" }) });
  }
  const route = new URL(request.url).pathname.split("/").filter(Boolean).at(-1) || "";
  if (route === "health" && request.method === "GET") return jsonResponse(200, { ok: true, backend: "supabase" });

  try {
    const db = dbClient();
    if (route === "control" && request.method === "GET") return await controlSummary(db, request);
    if (route === "event" && request.method === "POST") {
      const parsed = await readJson(request);
      if (parsed.error) return jsonResponse(400, { error: parsed.error });
      if (parsed.value.event_type !== "page_view") return jsonResponse(400, { error: "Unsupported public event." });
      return await recordPageView(db, parsed.value);
    }
    if (route === "plan" && request.method === "POST") {
      const parsed = await readJson(request);
      if (parsed.error) return jsonResponse(400, { error: parsed.error });
      return await createPlan(db, parsed.value);
    }
    if (route === "product-view" && request.method === "POST") {
      const parsed = await readJson(request);
      if (parsed.error) return jsonResponse(400, { error: parsed.error });
      return await recordProductView(db, parsed.value);
    }
    if (route === "affiliate-click" && request.method === "POST") {
      const parsed = await readJson(request);
      if (parsed.error) return jsonResponse(400, { error: parsed.error });
      return await recordAffiliateClick(db, parsed.value);
    }
    if (route === "conversions" && request.method === "POST") {
      const parsed = await readJson(request);
      if (parsed.error) return jsonResponse(400, { error: parsed.error });
      return await ingestConversion(db, request, parsed.value);
    }
    if (route === "revenue" && request.method === "POST") {
      const parsed = await readJson(request);
      if (parsed.error) return jsonResponse(400, { error: parsed.error });
      return await ingestRevenue(db, request, parsed.value);
    }
    return jsonResponse(404, { error: "Not found." });
  } catch {
    // Never include request bodies, headers, secrets, or upstream payloads in logs/responses.
    return jsonResponse(503, { error: "KATE backend is temporarily unavailable." });
  }
});
