(() => {
  const t = (text, params = {}) => window.KATE_I18N?.t
    ? window.KATE_I18N.t(text, params)
    : String(text).replace(/\{(\w+)\}/g, (match, key) => params[key] ?? match);
  const locale = () => window.KATE_I18N?.locale || 'en';
  const currencies = new Set(['USD', 'EUR', 'GBP', 'CHF']);
  const currencyControls = new Set();
  let preferredCurrency = null;
  try {
    const saved = window.localStorage?.getItem('kate_currency');
    if (currencies.has(saved)) preferredCurrency = saved;
  } catch (_) { /* Currency controls also work when browser storage is unavailable. */ }
  function registerCurrency(control, changed = () => {}) {
    if (!preferredCurrency && currencies.has(control.value)) preferredCurrency = control.value;
    if (preferredCurrency) control.value = preferredCurrency;
    currencyControls.add({ control, changed });
    control.addEventListener('change', () => {
      if (!currencies.has(control.value)) {
        control.value = preferredCurrency || 'USD';
        return;
      }
      preferredCurrency = control.value;
      try { window.localStorage?.setItem('kate_currency', preferredCurrency); } catch (_) {}
      currencyControls.forEach((entry) => {
        if (entry.control.isConnected === false) {
          currencyControls.delete(entry);
          return;
        }
        entry.control.value = preferredCurrency;
        entry.changed();
      });
    });
  }
  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = t(text);
    return node;
  };

  const form = document.querySelector('[data-planner-form]');
  if (form) {
    const errorBox = document.querySelector('[data-form-error]');
    const output = document.querySelector('[data-plan-output]');
    const submit = form.querySelector('button[type="submit"]');
    registerCurrency(form.elements.currency);
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      errorBox.hidden = true;
      output.hidden = true;
      if (!form.reportValidity()) return;
      submit.disabled = true;
      submit.textContent = t('Preparing outline…');
      const checked = [...form.querySelectorAll('input[name="interests"]:checked')].map((node) => node.value);
      const rawBudget = form.elements.budget.value.trim();
      const payload = {
        origin: form.elements.origin.value,
        focus: form.elements.focus.value,
        days: Number(form.elements.days.value),
        travelers: Number(form.elements.travelers.value),
        budget: rawBudget === '' ? null : Number(rawBudget),
        currency: form.elements.currency.value,
        interests: checked,
        comfort: form.elements.comfort.value,
        target_date: form.elements.target_date.value,
        flexibility: form.elements.flexibility.value,
      };
      try {
        const response = await fetch('/api/plan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'We could not prepare this planning view.');
        renderPlan(data, output, payload);
        output.hidden = false;
        output.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } catch (error) {
        errorBox.textContent = t(error.message || 'We could not prepare this planning view. No availability or booking was checked. Try again or open the comparison page.');
        errorBox.hidden = false;
      } finally {
        submit.disabled = false;
        const arrow = make('span', '', '↗');
        arrow.setAttribute('aria-hidden', 'true');
        submit.replaceChildren(document.createTextNode(t('Build my planning outline ')), arrow);
      }
    });
  }

  function renderPlan(data, container, request) {
    container.replaceChildren();
    const card = make('section', 'output-card');
    const head = make('div', 'output-head');
    const titleWrap = make('div');
    titleWrap.append(make('h2', '', t('{days}-day planning outline', { days: data.planning_inputs.days })));
    titleWrap.append(make('p', '', 'A useful structure to verify with a provider—not a supplier itinerary.'));
    head.append(titleWrap, make('span', 'output-label', 'PLANNING OUTLINE'));
    card.append(head);

    const chips = make('div', 'input-chips');
    const inputs = data.planning_inputs;
    [inputs.origin, inputs.focus, t(inputs.travelers === 1 ? '{count} traveler' : '{count} travelers', { count: inputs.travelers }),
      inputs.budget ? t('Budget target: {amount} {currency} p.p.', { amount: new Intl.NumberFormat(locale()).format(inputs.budget.amount), currency: inputs.budget.currency }) : 'Budget target not set',
      t('Comfort: {comfort}', { comfort: t(inputs.comfort.replaceAll('_', ' ')) }),
      ...(inputs.interests.length ? inputs.interests.map((x) => x.replaceAll('_', ' ')) : [])]
      .forEach((value) => chips.append(make('span', '', value)));
    card.append(chips);

    const list = make('ol', 'itinerary-list');
    data.itinerary.forEach((item) => {
      const row = make('li');
      row.append(make('span', '', item.day));
      row.append(make('h3', '', item.title));
      row.append(make('p', '', item.detail));
      list.append(row);
    });
    card.append(list);

    const notice = make('div', 'output-notice');
    const noticeText = make('div');
    const strong = make('strong', '', 'Planning outline only. ');
    noticeText.append(strong, document.createTextNode(t('Confirm itinerary, total party price and date-specific availability directly with the provider.')));
    notice.append(make('span', 'trust-icon', 'i'), noticeText);
    card.append(notice);

    const actions = make('div', 'output-actions');
    const mara = make('a', 'button button-primary', 'Compare road vs fly-in ↗');
    mara.href = window.KATE_I18N?.path?.('/mara') || '/mara';
    const home = make('a', 'button button-quiet', 'Back to KATE');
    home.href = window.KATE_I18N?.path?.('/') || '/';
    actions.append(mara, home);
    card.append(actions);
    container.append(card);
    if (request.origin.trim().toLowerCase() === 'nairobi' && request.focus === 'maasai_mara'
        && request.days >= 2 && request.days <= 4) {
      const section = makeOfferSection(request.currency);
      container.append(section);
      setupOffers(section, '/planner', request.target_date, request.days)();
    }
  }

  function makeOfferSection(currency) {
    const section = make('section', 'offers-section');
    section.setAttribute('data-offers', '');
    section.setAttribute('data-nosnippet', '');
    section.append(make('p', 'section-kicker', 'VIATOR PRODUCT PREVIEWS'));
    section.append(make('h2', '', 'Explore Nairobi–Mara trips'));
    section.append(make('p', 'offer-disclosure', 'Supplier from prices are a starting point. Final dates, total party price and availability are checked on Viator. These previews are not matched to your group, budget or comfort preference.'));
    const controls = make('div', 'offer-controls');
    const label = make('label', 'field');
    label.append(make('span', '', 'Price currency'));
    const select = make('select');
    select.setAttribute('data-offer-currency', '');
    ['USD', 'EUR', 'GBP', 'CHF'].forEach((value) => {
      const option = make('option', '', value);
      option.value = value;
      select.append(option);
    });
    select.value = currency;
    label.append(select);
    const button = make('button', 'button button-quiet', 'Load product previews');
    button.type = 'button';
    button.setAttribute('data-offers-load', '');
    controls.append(label, button);
    section.append(controls);
    const status = make('p', 'offer-status');
    status.setAttribute('data-offers-status', '');
    status.setAttribute('role', 'status');
    const results = make('div', 'offer-grid');
    results.setAttribute('data-offers-results', '');
    section.append(status, results);
    section.append(make('p', 'offer-disclosure', 'Affiliate disclosure: KATE may earn a commission if you book through a Viator link.'));
    return section;
  }

  function setupOffers(section, sourcePage, targetDate = '', days = 3) {
    const category = section.getAttribute('data-offer-category') === 'nairobi' ? 'nairobi' : 'mara';
    const currency = section.querySelector('[data-offer-currency]');
    const tripLength = section.querySelector('[data-offer-days]');
    const priority = section.querySelector('[data-offer-priority]');
    const assistant = section.querySelector('[data-sales-assistant]');
    const checklist = section.querySelector('[data-assistant-checklist]');
    const button = section.querySelector('[data-offers-load]');
    const status = section.querySelector('[data-offers-status]');
    const results = section.querySelector('[data-offers-results]');
    const controls = [button, currency, tripLength, priority].filter(Boolean);
    let loading = false;
    let hasRequested = false;
    let requestCurrency = currency.value;
    let generation = 0;
    let controller;
    const updateChecklist = () => {
      if (!checklist || !priority) return;
      const checks = [
        'Confirm your dates, number of travelers and the total price for your party.',
        'Read the cancellation terms before paying.',
      ];
      if (priority.value === 'comfort') {
        checks.splice(1, 0, 'Confirm the named accommodation, room sharing and bathroom facilities.',
          'Check the vehicle type, group size and whether transfers and game drives are shared.');
      } else if (priority.value === 'travel_time') {
        checks.splice(1, 0, 'Check the pickup location, departure and return times, and complete itinerary.',
          'Confirm road or air transfers and how much time is scheduled for game drives.');
      } else {
        checks.splice(1, 0, 'Check park fees, transfers, meals and every extra charge.');
      }
      const list = make('ul');
      checks.forEach((check) => list.append(make('li', '', check)));
      checklist.replaceChildren(make('h4', '', 'Your booking checklist'), list,
        make('p', '', priority.value === 'cost'
          ? 'Available previews are shown by lowest listed from price. This is not a quote for your group.'
          : 'These questions help you compare listings. The previews are not verified matches for this priority.'));
    };
    if (priority) priority.addEventListener('change', updateChecklist);
    updateChecklist();
    const load = async (replace = false) => {
      if (loading && replace !== true) return;
      const current = ++generation;
      const isCurrent = () => current === generation;
      controller?.abort();
      controller = typeof AbortController === 'function' ? new AbortController() : null;
      const signal = controller?.signal;
      loading = true;
      hasRequested = true;
      requestCurrency = currency.value;

      controls.forEach((control) => { control.disabled = true; });
      updateChecklist();
      results.replaceChildren();
      status.textContent = t('Loading supplier product previews…');
      const selectedDays = tripLength ? Number(tripLength.value) : days;
      const params = new URLSearchParams({ currency: requestCurrency });
      if (category === 'nairobi') params.set('category', 'nairobi');
      else params.set('days', String(selectedDays));
      if (assistant) {
        const heading = section.querySelector('[data-offers-title]');
        if (heading) heading.textContent = t('{days}-day Maasai Mara safari options', { days: selectedDays });
      }
      if (targetDate) params.set('target_date', targetDate);
      try {
        const request = () => fetch(`/api/offers?${params}`, { headers: { Accept: 'application/json' }, ...(signal ? { signal } : {}) });
        let response = await request();
        if (!isCurrent()) return;
        if (response.status === 429) {
          status.textContent = t(category === 'nairobi'
            ? 'Nairobi activities are busy. Waiting a few seconds, then trying once more…'
            : 'Safari options are busy. Waiting a few seconds, then trying once more…');
          await new Promise((resolve) => setTimeout(resolve, 6000));
          if (!isCurrent()) return;
          response = await request();
        }
        if (!isCurrent()) return;
        const data = await response.json();
        if (!isCurrent()) return;
        if (!response.ok) throw new Error(response.status === 429
          ? category === 'nairobi'
            ? 'Nairobi activities are still busy. Please try again shortly.'
            : 'Safari options are still busy. Please try again shortly.'
          : response.status === 503
            ? 'Product previews are currently unavailable. You can still use the planning guide.'
            : 'Product previews could not be loaded. Please try again later.');
        if (!Array.isArray(data.offers)) throw new Error('Product previews could not be loaded. Please try again later.');
        const offers = [...data.offers];
        if (priority && priority.value === 'cost') {
          const price = (offer) => typeof offer.from_price === 'number' && Number.isFinite(offer.from_price)
            ? offer.from_price : Infinity;
          offers.sort((left, right) => price(left) - price(right));
        }
        offers.forEach((offer) => results.append(renderOffer(offer, sourcePage)));
        status.textContent = t(data.offers.length
          ? 'From prices only. Date-specific availability and the price for your party have not been checked.'
          : 'No supplier previews found. Date-specific availability has not been checked.');
      } catch (error) {
        if (!isCurrent()) return;
        status.textContent = t(error.message || 'Product previews are currently unavailable.');
      } finally {
        if (!isCurrent()) return;
        controls.forEach((control) => { control.disabled = false; });
        loading = false;
      }
    };
    registerCurrency(currency, () => {
      if (hasRequested && currency.value !== requestCurrency) load(true);
    });
    if (assistant) {
      assistant.addEventListener('submit', (event) => {
        event.preventDefault();
        load();
      });
    } else {
      button.addEventListener('click', load);
    }
    return load;
  }

  function renderOffer(offer, sourcePage) {
    const card = make('article', 'offer-card');
    card.append(make('h3', '', offer.title));
    let price = 'From price unavailable';
    if (typeof offer.from_price === 'number' && Number.isFinite(offer.from_price)) {
      try {
        price = t('From {price}', { price: new Intl.NumberFormat(locale(), { style: 'currency', currency: offer.currency }).format(offer.from_price) });
      } catch (_) {
        price = t('From {price}', { price: `${offer.from_price} ${offer.currency}` });
      }
    }
    card.append(make('p', 'offer-price', price));
    if (typeof offer.duration_minutes === 'number' && Number.isFinite(offer.duration_minutes)) {
      card.append(make('p', 'offer-meta', t('Supplier duration: {duration}', { duration: offer.duration_minutes >= 1440
        ? t('{count} days', { count: new Intl.NumberFormat(locale(), { maximumFractionDigits: 1 }).format(offer.duration_minutes / 1440) })
        : t('{count} minutes', { count: new Intl.NumberFormat(locale()).format(offer.duration_minutes) }) })));
    }
    if (typeof offer.rating === 'number' && Number.isFinite(offer.rating)) {
      const reviews = Number.isInteger(offer.review_count) ? t(' · {count} reviews', { count: new Intl.NumberFormat(locale()).format(offer.review_count) }) : '';
      card.append(make('p', 'offer-meta', t('Viator rating: {rating}/5{reviews}', { rating: new Intl.NumberFormat(locale()).format(offer.rating), reviews })));
    }
    const checkedAt = new Date(typeof offer.checked_at === 'string' ? offer.checked_at : NaN);
    if (!Number.isNaN(checkedAt.getTime())) {
      const checked = make('time', 'offer-meta', t('Supplier data checked: {date}', { date: checkedAt.toLocaleString(locale()) }));
      checked.dateTime = checkedAt.toISOString();
      card.append(checked);
    }
    card.append(make('p', 'offer-disclosure', 'From price; final dates, party price and availability on Viator.'));
    const handoff = make('form');
    handoff.method = 'post';
    handoff.action = '/api/affiliate-click';
    [['product_id', offer.product_id], ['page', sourcePage]].forEach(([name, value]) => {
      const field = make('input');
      field.type = 'hidden';
      field.name = name;
      field.value = value;
      handoff.append(field);
    });
    const button = make('button', 'button button-primary', 'Check details on Viator ↗');
    button.type = 'submit';
    handoff.append(button);
    card.append(handoff);
    return card;
  }

  document.querySelectorAll('[data-offers]').forEach((section) => {
    const load = setupOffers(section, '/mara');
    const linkedHash = section.getAttribute('data-offer-category') === 'nairobi'
      ? '#nairobi-extras' : '#safari-options';
    let linkedLoadStarted = false;
    const loadLinkedOptions = () => {
      if (window.location.hash === linkedHash && !linkedLoadStarted) {
        linkedLoadStarted = true;
        load();
      }
    };
    window.addEventListener('hashchange', loadLinkedOptions);
    loadLinkedOptions();
  });

  const dashboard = document.querySelector('[data-control-dashboard]');
  const loginForm = document.querySelector('[data-control-login]');
  if (dashboard && loginForm) {
    const secretInput = loginForm.querySelector('[data-admin-secret]');
    const errorBox = loginForm.querySelector('[data-control-error]');
    loginForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      errorBox.hidden = true;
      if (!loginForm.reportValidity()) return;
      const button = loginForm.querySelector('button[type="submit"]');
      const secret = secretInput.value;
      button.disabled = true;
      try {
        const response = await fetch('/api/control', {
          headers: { 'Accept': 'application/json', 'Authorization': `Bearer ${secret}` },
          cache: 'no-store',
        });
        const data = await response.json();
        secretInput.value = '';
        if (!response.ok) throw new Error(data.error || 'Stored aggregates are not available for this session.');
        loginForm.hidden = true;
        renderDashboard(data, dashboard);
        dashboard.hidden = false;
      } catch (error) {
        errorBox.textContent = error.message || 'Admin access could not be verified.';
        errorBox.hidden = false;
      } finally {
        secretInput.value = '';
        button.disabled = false;
      }
    });
  } else if (dashboard) {
    // Local Python/SQLite preview compatibility; production uses the explicit login form above.
    fetch('/api/control', { headers: { 'Accept': 'application/json' } })
      .then(async (response) => {
        if (!response.ok) throw new Error('Stored aggregates are not available for this session.');
        return response.json();
      })
      .then((data) => renderDashboard(data, dashboard))
      .catch((error) => {
        dashboard.replaceChildren(make('p', 'metrics-error', error.message));
      });
  }

  function metricCard(label, value, detail = '') {
    const card = make('article', 'metric-card');
    card.append(make('span', '', label));
    card.append(make('strong', '', value));
    if (detail) card.append(make('small', '', detail));
    return card;
  }

  function renderDashboard(data, container) {
    container.replaceChildren();
    container.append(make('h2', 'metrics-intro', 'Recorded activity'));
    container.append(make('p', 'privacy-note', 'Event counts include checks and automated requests. They do not establish unique visitors or customer interest. Supplier bookings and commission reports are not synchronized automatically.'));
    const eventGrid = make('div', 'metrics-grid');
    const eventLabels = [
      ['page_view', 'Page views'], ['planner_started', 'Planner started'],
      ['planner_completed', 'Planner completed'], ['product_view', 'Product views'],
      ['affiliate_click', 'Affiliate clicks'],
    ];
    eventLabels.forEach(([key, label]) => {
      const n = data.events[key] || 0;
      eventGrid.append(metricCard(label, String(n), 'Recorded events, including test activity.'));
    });
    container.append(eventGrid);

    const pageSection = make('section', 'metric-subsection');
    pageSection.append(make('h2', '', 'Page views by page'));
    const pageGrid = make('div', 'metrics-grid');
    const pageNames = [
      ['/', 'Home'], ['/planner', 'Planner'], ['/mara', 'Safari options'], ['/control', 'Control Center'],
      ['/guides', 'Safari guides'],
      ['/guides/3-day-masai-mara-safari-from-nairobi', 'Three-day safari guide'],
      ['/guides/private-vs-shared-masai-mara-safari', 'Private vs shared guide'],
    ];
    pageNames.forEach(([path, label]) => {
      const n = data.page_views[path] || 0;
      pageGrid.append(metricCard(label, String(n), path));
    });
    pageSection.append(pageGrid);
    container.append(pageSection);

    const snapshotSection = make('section', 'metric-subsection');
    snapshotSection.append(make('h2', '', 'Discovery snapshot records · separate filters'));
    const snapshotGrid = make('div', 'metrics-grid');
    ['road', 'fly', 'unresolved'].forEach((partition) => {
      const n = data.discovery_snapshot_by_filter[partition] || 0;
      snapshotGrid.append(metricCard(`${partition} filter only`, n ? String(n) : 'No data yet', 'Not a ranking, offer count or availability result.'));
    });
    snapshotSection.append(snapshotGrid);
    container.append(snapshotSection);

    const outcomeSection = make('section', 'metric-subsection');
    outcomeSection.append(make('h2', '', 'Commercial outcomes'));
    const outcomeGrid = make('div', 'metrics-grid');
    outcomeGrid.append(metricCard('Imported conversions', String(data.conversions || 0), 'Evidence-backed records only; supplier reporting is not synchronized.'));
    const revenueValue = data.revenue.length
      ? data.revenue.map((item) => `${item.amount} ${item.currency}`).join(' · ')
      : 'No imported revenue';
    outcomeGrid.append(metricCard('Imported revenue', revenueValue, data.revenue.length ? 'Stored evidence-backed records; not a payout confirmation.' : 'No evidence-backed revenue report has been imported. This is not a supplier account balance.'));
    outcomeSection.append(outcomeGrid);
    outcomeSection.append(make('p', 'privacy-note', data.note));
    container.append(outcomeSection);
  }

  // Static Netlify pages do not pass through the local Python GET handler.
  const page = window.location.pathname.replace(/\/$/, '') || '/';
  fetch('/api/event', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event_type: 'page_view', page }),
    keepalive: true,
  }).catch(() => {});
})();
