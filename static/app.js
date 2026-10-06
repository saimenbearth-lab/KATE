(() => {
  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const form = document.querySelector('[data-planner-form]');
  if (form) {
    const errorBox = document.querySelector('[data-form-error]');
    const output = document.querySelector('[data-plan-output]');
    const submit = form.querySelector('button[type="submit"]');
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      errorBox.hidden = true;
      output.hidden = true;
      if (!form.reportValidity()) return;
      submit.disabled = true;
      submit.textContent = 'Preparing outline…';
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
        renderPlan(data, output);
        output.hidden = false;
        output.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } catch (error) {
        errorBox.textContent = error.message || 'We could not prepare this planning view. No availability or booking was checked. Try again or open the comparison page.';
        errorBox.hidden = false;
      } finally {
        submit.disabled = false;
        submit.innerHTML = 'Build my planning outline <span aria-hidden="true">↗</span>';
      }
    });
  }

  function renderPlan(data, container) {
    container.replaceChildren();
    const card = make('section', 'output-card');
    const head = make('div', 'output-head');
    const titleWrap = make('div');
    titleWrap.append(make('h2', '', `${data.planning_inputs.days}-day planning outline`));
    titleWrap.append(make('p', '', 'A useful structure to verify with a provider—not a supplier itinerary.'));
    head.append(titleWrap, make('span', 'output-label', 'PLANNING OUTLINE'));
    card.append(head);

    const chips = make('div', 'input-chips');
    const inputs = data.planning_inputs;
    [inputs.origin, inputs.focus, `${inputs.travelers} traveler${inputs.travelers === 1 ? '' : 's'}`,
      inputs.budget ? `Budget target: ${inputs.budget.amount} ${inputs.budget.currency} p.p.` : 'Budget target not set',
      `Comfort: ${inputs.comfort.replaceAll('_', ' ')}`,
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
    const strong = make('strong', '', 'No verified offers yet. ');
    noticeText.append(strong, document.createTextNode(`${data.message} Live Viator inventory is not connected.`));
    notice.append(make('span', 'trust-icon', 'i'), noticeText);
    card.append(notice);

    const actions = make('div', 'output-actions');
    const mara = make('a', 'button button-primary', 'Compare road vs fly-in ↗');
    mara.href = '/mara';
    const home = make('a', 'button button-quiet', 'Back to KATE');
    home.href = '/';
    actions.append(mara, home);
    card.append(actions);
    container.append(card);
  }

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
    const eventGrid = make('div', 'metrics-grid');
    const eventLabels = [
      ['page_view', 'Page views'], ['planner_started', 'Planner started'],
      ['planner_completed', 'Planner completed'], ['product_view', 'Product views'],
      ['affiliate_click', 'Affiliate clicks'],
    ];
    eventLabels.forEach(([key, label]) => {
      const n = data.events[key] || 0;
      eventGrid.append(metricCard(label, n ? String(n) : 'No data yet', 'Persisted events; no projections.'));
    });
    container.append(eventGrid);

    const pageSection = make('section', 'metric-subsection');
    pageSection.append(make('h2', '', 'Page views by page'));
    const pageGrid = make('div', 'metrics-grid');
    const pageNames = [['/', 'Home'], ['/planner', 'Planner'], ['/mara', 'Mara comparison'], ['/control', 'Control Center']];
    pageNames.forEach(([path, label]) => {
      const n = data.page_views[path] || 0;
      pageGrid.append(metricCard(label, n ? String(n) : 'No data yet', path));
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
    outcomeGrid.append(metricCard('Conversions', data.conversions ? String(data.conversions) : 'No data yet', 'No conversion records are inferred.'));
    const revenueValue = data.revenue.length
      ? data.revenue.map((item) => `${item.amount} ${item.currency}`).join(' · ')
      : 'No data yet';
    outcomeGrid.append(metricCard('Recorded revenue', revenueValue, data.revenue.length ? 'Stored evidence-backed records only.' : 'No revenue records are present.'));
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
