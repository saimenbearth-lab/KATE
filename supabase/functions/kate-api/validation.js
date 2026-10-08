export const ALLOWED_PAGES = new Set(["/", "/planner", "/mara", "/control", "/guides", "/guides/3-day-masai-mara-safari-from-nairobi", "/guides/private-vs-shared-masai-mara-safari"]);
export const ALLOWED_INTERESTS = new Set(["wildlife", "culture", "photography", "slow_pace"]);

export function validatePlan(data) {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    return { error: "Send a small JSON form payload." };
  }

  const origin = typeof data.origin === "string" ? data.origin.trim() : "";
  if (!origin || origin.length > 80) return { error: "Add a starting point (80 characters maximum)." };

  const days = data.days;
  const travelers = data.travelers;
  if (!Number.isInteger(days) || days < 1 || days > 21) {
    return { error: "Trip length must be between 1 and 21 days." };
  }
  if (!Number.isInteger(travelers) || travelers < 1 || travelers > 20) {
    return { error: "Travelers must be between 1 and 20." };
  }

  const focus = typeof data.focus === "string" ? data.focus : "maasai_mara";
  if (!new Set(["maasai_mara", "undecided"]).has(focus)) return { error: "Choose a listed trip focus." };

  let budget = null;
  if (data.budget !== null && data.budget !== undefined && data.budget !== "") {
    budget = data.budget;
    if (!Number.isFinite(budget) || budget < 0 || budget > 10_000_000) {
      return { error: "Enter a non-negative planning budget." };
    }
    budget = Math.round(budget * 100) / 100;
  }

  const currency = typeof data.currency === "string" ? data.currency : "CHF";
  if (!new Set(["CHF", "EUR", "USD", "GBP"]).has(currency)) return { error: "Choose a listed currency." };

  const rawInterests = data.interests === undefined ? [] : data.interests;
  if (!Array.isArray(rawInterests) || rawInterests.some((item) => typeof item !== "string")) {
    return { error: "Choose valid interests." };
  }
  const interests = [...new Set(rawInterests.filter((item) => ALLOWED_INTERESTS.has(item)))].sort();

  const comfort = typeof data.comfort === "string" ? data.comfort : "balanced";
  if (!new Set(["simple", "balanced", "more_comfort"]).has(comfort)) {
    return { error: "Choose a listed comfort preference." };
  }

  let targetDate = null;
  if (data.target_date !== undefined && data.target_date !== null) {
    if (typeof data.target_date !== "string") return { error: "Use a valid date or leave it blank." };
    const rawDate = data.target_date.trim();
    if (rawDate) {
      const date = new Date(`${rawDate}T00:00:00.000Z`);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(rawDate) || Number.isNaN(date.valueOf()) || date.toISOString().slice(0, 10) !== rawDate) {
        return { error: "Use a valid date or leave it blank." };
      }
      targetDate = rawDate;
    }
  }

  const flexibility = typeof data.flexibility === "string" ? data.flexibility : "not_sure";
  if (!new Set(["fixed", "flexible", "not_sure"]).has(flexibility)) {
    return { error: "Choose a listed date preference." };
  }

  return {
    value: { origin, focus, days, travelers, budget, currency, interests, comfort, targetDate, flexibility },
  };
}

export function validatePageView(data) {
  if (!data || typeof data.page !== "string") return null;
  const page = data.page.replace(/\/$/, "") || "/";
  return ALLOWED_PAGES.has(page) ? page : null;
}

export function buildItinerary({ origin, days, focus, interests }) {
  const focusText = focus === "maasai_mara" ? "the Maasai Mara" : "your selected Kenya focus";
  const interestText = interests.length ? interests.map((item) => item.replaceAll("_", " ")).join(", ") : "your chosen priorities";
  const itinerary = [];
  for (let day = 1; day <= days; day += 1) {
    let title;
    let detail;
    if (days === 1) {
      title = "One-day planning window";
      detail = `From ${origin}, check whether travel, your selected focus (${focusText}) and the return plan fit the same day. Confirm the exact schedule, inclusions and fees directly; no route or availability has been checked.`;
    } else if (day === 1) {
      title = "Arrival and onward arrangements";
      detail = `From ${origin}, confirm the departure or pickup details, onward transport, first-day inclusions and the provider's exact itinerary for ${focusText}.`;
    } else if (day === days) {
      title = "Return and final checks";
      detail = "Confirm the return arrangements, hand-off point, schedule, total party price, extra fees and cancellation terms with the provider.";
    } else {
      title = `Day ${day} · Your main priorities`;
      detail = `Leave room for ${interestText}. Confirm the exact activity schedule, transfers and what is included; this outline does not imply that any service is available.`;
    }
    itinerary.push({ day: `DAY ${String(day).padStart(2, "0")}`, title, detail });
  }
  return itinerary;
}
