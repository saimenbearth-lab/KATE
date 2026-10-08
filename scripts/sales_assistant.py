"""Markup for the free, deterministic Mara planning assistant."""

ADVISOR_HTML = '''
<form class="sales-assistant" data-sales-assistant>
<div class="assistant-intro"><h3>Find a useful safari shortlist</h3><p>A guided planning assistant: choose your trip length and what you want to check. It uses supplier previews, without checking your dates or matching trips to your group.</p></div>
<div class="offer-controls assistant-controls">
<label class="field"><span>Trip length</span><select name="days" data-offer-days><option value="2">2 days</option><option value="3" selected>3 days</option><option value="4">4 days</option></select></label>
<label class="field"><span>Price currency</span><select name="currency" data-offer-currency><option>USD</option><option>EUR</option><option>GBP</option><option>CHF</option></select></label>
<label class="field"><span>What matters most?</span><select name="priority" data-offer-priority><option value="cost">Total cost</option><option value="comfort">Comfort and accommodation</option><option value="travel_time">Travel time and transfers</option></select></label>
<button class="button button-primary" type="submit" data-offers-load>Show safari options</button>
</div>
<div class="assistant-checklist" data-assistant-checklist aria-live="polite"><h4>Your booking checklist</h4><ul><li>Confirm your dates, number of travelers and the total price for your party.</li><li>Check park fees, transfers, meals and every extra charge.</li><li>Read the cancellation terms before paying.</li></ul><p>From prices are not a quote for your group. Check the final price on Viator.</p></div>
<noscript><p>The assistant needs JavaScript to load current supplier previews. The comparison guide below still explains what to check before booking.</p></noscript>
</form>
'''
