import { buildItinerary, validatePageView, validatePlan } from "./validation.js";
import { searchMaraOffers, searchNairobiOffers } from "./viator.js";

export function createHandler({ dbFactory, env, fetchImpl = fetch }) {
  const MAX_BODY_BYTES = 8192;
  const PAGE_INTENTS = {
    "/": "kenya_trip_planning",
    "/planner": "trip_planning",
    "/mara": "mara_3d_decision",
    "/control": "internal_operations",
    "/guides": "mara_safari_research",
    "/guides/3-day-masai-mara-safari-from-nairobi": "mara_3d_decision",
    "/guides/private-vs-shared-masai-mara-safari": "mara_group_type_decision",
    "/resources/safari-booking-checklist": "safari_booking_checks",
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
    return dbFactory();
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

  async function requireAdmin(request, db) {
    const expected = env("KATE_ADMIN_SECRET");
    let storedHash = null;
    if (!expected) {
      const saved = await db.from("business_memory").select("value").eq("key", "control_admin_secret_sha256").maybeSingle();
      if (saved.error || !/^[0-9a-f]{64}$/.test(saved.data?.value || "")) {
        return { ok: false, response: jsonResponse(503, { error: "Control Center access is not configured; analytics remain hidden." }) };
      }
      storedHash = saved.data.value;
    }
    const authorization = request.headers.get("authorization") || "";
    const match = authorization.match(/^Bearer\s+(.+)$/i);
    let valid = false;
    if (match && expected) valid = await equalSecret(match[1], expected);
    else if (match && storedHash) {
      const candidate = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(match[1])));
      let mismatch = 0;
      for (let index = 0; index < candidate.length; index++) mismatch |= candidate[index] ^ parseInt(storedHash.slice(index * 2, index * 2 + 2), 16);
      valid = mismatch === 0;
    }
    if (!valid) {
      return { ok: false, response: jsonResponse(401, { error: "Admin authentication required." }) };
    }
    return { ok: true };
  }

  function validIsoDate(value) {
    if (typeof value !== "string" || !value.trim()) return false;
    return Number.isFinite(Date.parse(value));
  }

  async function commercialRecordId(source, externalId) {
    if (typeof externalId !== "string" || !externalId.trim() || externalId.length > 200) return null;
    const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify([source, externalId.trim()])));
    return Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, "0")).join("");
  }

  const APPROVED_PID = "P00323912";
  const OFFER_TTL_MS = 5 * 60 * 1000;

  function approvedCatalogueUrl(value) {
    try {
      const url = new URL(value);
      return url.protocol === "https:" && !url.username && !url.password && !url.port
        && ["www.viator.com", "viator.com"].includes(url.hostname)
        && !url.hash && url.pathname.startsWith("/tours/") && url.searchParams.getAll("pid").length === 1
        && url.searchParams.get("pid") === APPROVED_PID;
    } catch { return false; }
  }

  function catalogueEligible(product) {
    const checked = Date.parse(product.source_last_checked);
    return product.provider === "Viator" && product.affiliate_state === "approved"
      && product.snapshot_context?.catalogue_status === "ACTIVE"
      && product.snapshot_context?.catalogue_source === "viator_products_search"
      && Number.isFinite(checked) && checked <= Date.now() && Date.now() - checked < 15 * 60 * 1000
      && approvedCatalogueUrl(product.affiliate_url);
  }

  async function catalogueOffers(db, request) {
    const params = new URL(request.url).searchParams;
    const category = params.get("category") ?? "mara";
    if (!["mara", "nairobi"].includes(category)) return jsonResponse(400, { error: "Choose a supported offer category." });
    const currency = params.get("currency") || "USD";
    if (!["USD", "EUR", "GBP", "CHF"].includes(currency)) return jsonResponse(400, { error: "Choose a supported currency." });
    const rawDays = params.get("days") || "3";
    if (!/^[234]$/.test(rawDays)) return jsonResponse(400, { error: "Choose a safari length of 2, 3 or 4 days." });
    const days = Number(rawDays);
    const targetDate = params.get("target_date") || null;
    if (targetDate) {
      const day = new Date(`${targetDate}T00:00:00.000Z`);
      const delta = day.valueOf() - Date.now();
      if (!/^\d{4}-\d{2}-\d{2}$/.test(targetDate) || !Number.isFinite(day.valueOf())
        || day.toISOString().slice(0, 10) !== targetDate || delta < -86400000 || delta > 366 * 86400000) {
        return jsonResponse(400, { error: "Choose a valid travel date within the next year." });
      }
    }
    const key = category === "nairobi" ? `viator_offers:nairobi:${currency}:1-720:${targetDate || "any"}`
      : `viator_offers:${currency}:${days}:${targetDate || "any"}`;
    const cached = await db.from("business_memory").select("value,updated_at").eq("key", key).maybeSingle();
    if (cached.error) return jsonResponse(503, { error: "Safari options are temporarily unavailable." });
    if (cached.data && Date.now() - Date.parse(cached.data.updated_at) < OFFER_TTL_MS) {
      try { return jsonResponse(200, JSON.parse(cached.data.value)); } catch { /* Refresh invalid cache. */ }
    }
    const apiKey = env("VIATOR_API_KEY");
    if (!apiKey) return jsonResponse(503, { error: "Safari options are not connected yet. Please return shortly." });
    const lease = await db.rpc("claim_viator_search");
    if (lease.error) return jsonResponse(503, { error: "Safari options are temporarily unavailable." });
    if (!lease.data) return jsonResponse(429, { error: "Safari options are being refreshed. Please try again shortly." });
    let offers;
    try {
      const search = category === "nairobi" ? searchNairobiOffers : searchMaraOffers;
      offers = await search({ apiKey, currency, targetDate, days, fetchImpl });
    } catch (error) {
      const status = error.code === "supplier_rate_limit" ? 429 : 503;
      return jsonResponse(status, { error: "Safari options could not be loaded from Viator. Please try again later." });
    }
    // The supplier key must belong to the KATE affiliate account already approved in this project.
    const returnedCount = offers.length;
    offers = offers.filter((offer) => approvedCatalogueUrl(offer.affiliate_url));
    if (returnedCount && !offers.length) return jsonResponse(503, { error: "Safari affiliate options are not configured for this account." });
    if (offers.length) {
      const previous = await Promise.all(offers.map((offer) => db.from("products")
        .select("product_id,search_partition,snapshot_context").eq("product_id", offer.product_id).maybeSingle()));
      if (previous.some((result) => result.error)) return jsonResponse(503, { error: "Safari options are temporarily unavailable." });
      const rows = offers.map((offer, index) => ({
        product_id: offer.product_id, comparison_id: category === "nairobi" ? "nairobi-short-activities" : `nairobi-mara-${days}day`, search_partition: previous[index].data?.search_partition || "unresolved",
        provider: "Viator", product_name: offer.title, destination_text: category === "nairobi" ? "Nairobi, Kenya" : "Nairobi / Maasai Mara, Kenya", category: category === "nairobi" ? "activity" : "safari",
        from_price: offer.from_price, currency: offer.currency, price_basis_confirmed: false,
        date_availability_confirmed: false, availability_state: "unverified",
        affiliate_url: offer.affiliate_url, affiliate_state: "approved", source_last_checked: offer.checked_at,
        updated_at: offer.checked_at,
        confidence_note: "Active supplier catalogue listing; final travel-date availability and party price are confirmed on Viator.",
        snapshot_context: { ...(previous[index].data?.snapshot_context || {}), record_state: "active_catalogue_preview",
          catalogue_status: "ACTIVE", catalogue_source: "viator_products_search", approved_pid: APPROVED_PID,
          target_date_filter: targetDate, duration_minutes: offer.duration_minutes, price_basis: "supplier_from_price",
          ...(category === "nairobi" ? { offer_category: "nairobi", comparison_context: "nairobi_optional_extras",
            duration_min_minutes: offer.duration_min_minutes, duration_max_minutes: offer.duration_max_minutes } : {}) },
      }));
      const saved = await db.from("products").upsert(rows, { onConflict: "product_id" });
      if (saved.error) return jsonResponse(503, { error: "Safari options could not be saved. Please try again." });
    }
    const publicOffers = offers.map(({ affiliate_url, ...offer }) => offer);
    const payload = { offers: publicOffers, availability_checked: false, category,
      message: "Supplier catalogue options. From prices are indicative; confirm your travel dates, party price and availability on Viator." };
    const stored = await db.from("business_memory").upsert({ key, value: JSON.stringify(payload), updated_at: new Date().toISOString() }, { onConflict: "key" });
    if (stored.error) return jsonResponse(503, { error: "Safari options could not be saved. Please try again." });
    return jsonResponse(200, payload);
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
      .select("product_id,provider,availability_state,date_availability_confirmed,affiliate_state,affiliate_url,source_last_checked,snapshot_context")
      .eq("product_id", productId).maybeSingle();
    if (error) return jsonResponse(503, { error: "Product data is unavailable." });
    if (!product || (!catalogueEligible(product) && (product.availability_state !== "confirmed" || !product.date_availability_confirmed || product.affiliate_state !== "approved" || !approvedCatalogueUrl(product.affiliate_url)))) {
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
    const page = data.page === "/planner" ? "/planner" : "/mara";
    const { data: target, error } = await db.rpc("record_catalogue_click", {
      p_product_id: productId,
      p_clicked_at: new Date().toISOString(),
      p_page: page,
    });
    if (error) {
      if (error.code === "P0001" || (error.message || "").includes("no_verified_affiliate")) {
        return jsonResponse(409, { error: "This safari option has expired. Refresh the options and try again." });
      }
      return jsonResponse(503, { error: "Affiliate activity could not be stored." });
    }
    let parsed;
    try { parsed = new URL(target); } catch { return jsonResponse(409, { error: "The configured destination is not a valid HTTPS URL." }); }
    if (!approvedCatalogueUrl(parsed.toString())) {
      return jsonResponse(409, { error: "The configured destination is not a valid HTTPS URL." });
    }
    return new Response(null, { status: 303, headers: headers({ Location: parsed.toString() }) });
  }

  async function controlSummary(db, request) {
    const access = await requireAdmin(request, db);
    if (!access.ok) return access.response;
    const { data, error } = await db.rpc("kate_control_summary");
    if (error || !data) return jsonResponse(503, { error: "Stored aggregates are not available right now." });
    return jsonResponse(200, data);
  }

  async function ingestConversion(db, request, data) {
    const access = await requireAdmin(request, db);
    if (!access.ok) return access.response;
    const source = typeof data.source === "string" ? data.source.trim().slice(0, 80) : "";
    const verificationNote = typeof data.verification_note === "string" ? data.verification_note.trim().slice(0, 2000) : "";
    const productId = typeof data.product_id === "string" && data.product_id.trim() ? data.product_id.trim().slice(0, 80) : null;
    const eventTime = data.event_time;
    const id = await commercialRecordId(source, data.external_event_id);
    if (!source || !id || !verificationNote || !validIsoDate(eventTime)) {
      return jsonResponse(400, { error: "A source, external event ID, valid event time, and evidence-backed verification note are required." });
    }
    const { error } = await db.from("conversions").upsert({ id, product_id: productId, event_time: eventTime, source, verification_note: verificationNote }, { onConflict: "id", ignoreDuplicates: true });
    if (error) return jsonResponse(400, { error: "Conversion could not be stored; check its product reference and evidence fields." });
    return jsonResponse(201, { id });
  }

  async function ingestRevenue(db, request, data) {
    const access = await requireAdmin(request, db);
    if (!access.ok) return access.response;
    const amount = data.amount;
    const source = typeof data.source === "string" ? data.source.trim().slice(0, 80) : "";
    const id = await commercialRecordId(source, data.external_event_id);
    const currency = typeof data.currency === "string" ? data.currency.trim().toUpperCase() : "";
    const evidenceNote = typeof data.evidence_note === "string" ? data.evidence_note.trim().slice(0, 2000) : "";
    const recordedAt = data.recorded_at;
    if (!source || !id || !Number.isFinite(amount) || amount < 0 || !/^[A-Z]{3}$/.test(currency) || !evidenceNote || !validIsoDate(recordedAt)) {
      return jsonResponse(400, { error: "A source, external event ID, numeric non-negative amount, currency, record time, and evidence note are required." });
    }
    const { error } = await db.from("revenue").upsert({ id, amount, currency, recorded_at: recordedAt, evidence_note: evidenceNote }, { onConflict: "id", ignoreDuplicates: true });
    if (error) return jsonResponse(400, { error: "Revenue could not be stored; verify the currency and evidence fields." });
    return jsonResponse(201, { id });
  }

  return async (request) => {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: headers({ Allow: "GET, POST, OPTIONS" }) });
    }
    const route = new URL(request.url).pathname.split("/").filter(Boolean).at(-1) || "";
    try {
      const db = dbClient();
      if (route === "health" && request.method === "GET") {
        const admin = await db.from("business_memory").select("value").eq("key", "control_admin_secret_sha256").maybeSingle();
        if (admin.error) return jsonResponse(503, { error: "KATE storage is temporarily unavailable." });
        return jsonResponse(200, { ok: true, backend: "supabase", release: "kate-supplier-preview-v1",
          viator_configured: Boolean(env("VIATOR_API_KEY")),
          admin_configured: Boolean(env("KATE_ADMIN_SECRET")) || /^[0-9a-f]{64}$/.test(admin.data?.value || "") });
      }
      if (route === "offers" && request.method === "GET") return await catalogueOffers(db, request);
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
        let parsed;
        if ((request.headers.get("content-type") || "").toLowerCase().startsWith("application/x-www-form-urlencoded")) {
          const reader = request.body?.getReader();
          let value = "";
          let size = 0;
          const decoder = new TextDecoder();
          if (!reader) return jsonResponse(400, { error: "Choose a valid product." });
          while (true) {
            const chunk = await reader.read();
            if (chunk.done) break;
            size += chunk.value.byteLength;
            if (size > MAX_BODY_BYTES) { await reader.cancel(); return jsonResponse(400, { error: "Send a small form payload." }); }
            value += decoder.decode(chunk.value, { stream: true });
          }
          value += decoder.decode();
          parsed = { value: Object.fromEntries(new URLSearchParams(value)) };
        } else parsed = await readJson(request);
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
  };
}
