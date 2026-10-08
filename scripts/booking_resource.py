"""Free visitor resource for comparing actual safari quotes before booking."""
from __future__ import annotations

from html import escape


INQUIRY_TEMPLATE = """Subject: Written safari quote for [dates] — [party size]

Hello,

We are comparing a Maasai Mara safari starting from [pickup location] on
[departure date], returning to [return location] by [date / required time].

Our party: [number of adults], [number of children and their ages on the trip].
Room arrangement: [rooms / beds required].
Our priorities: [comfort, photography, exclusive vehicle, or other requirements].
The product / option we are considering: [product link and exact option name].

Please provide a written quote for this exact party and these dates, covering:

1. Availability and the day-by-day itinerary, including pickup and return details.
2. Road or flight arrangements; all transfers; vehicle, seating and guide details.
   If flights apply, please include the operator, schedule, baggage allowance,
   airstrip and onward transfers.
3. Which vehicles, transfers, guide services and activities are private or shared;
   maximum occupancy and any minimum-participant requirement.
4. Accommodation names, room / bed arrangements, nights and meal plan.
5. Included activities and any optional activities with separate charges.
6. Entry charges, taxes and other fees: what is included, what is excluded,
   who pays each extra, and when / how those amounts are payable.
7. One full party total in a stated currency, its price basis, all mandatory
   extras, and the quote's expiry date. Please distinguish optional extras.
8. Deposit and balance requirements, cancellation / change terms for this option,
   and what happens if a shared departure does not meet its participant minimum.
9. How the booking is confirmed, who operates the trip, and a contact for
   assistance during the trip.

Please identify any item you cannot confirm yet, rather than assuming it is
included. If the return timing is an estimate, please say so.

Thank you,
[name]
"""


CHECKS = (
    ("Match the request", "Use the same dates, party, room setup, pickup and return requirements for both quotes."),
    ("Name the exact option", "Save the product link, selected option, provider name and quote date. A tour title alone is not the option you are booking."),
    ("Read the whole itinerary", "Confirm the overnight stays, activities and transfers day by day. Check the return plan against any onward commitment."),
    ("Clarify private or shared", "Record what is exclusive to your party, what is shared, maximum vehicle occupancy and any participant minimum."),
    ("Identify accommodation and meals", "Request the accommodation names, room and bed arrangements, number of nights and meal plan."),
    ("List every extra", "Ask which entry charges, taxes, transfers and other mandatory charges sit outside the quoted total. Keep optional extras separate."),
    ("Check the price basis", "Is the amount per person, per booking or for the whole party? Request the full party total and currency for your exact option."),
    ("Check the terms", "Read deposit, balance, cancellation and change terms for the selected option. Record the quote expiry and confirmation process."),
)


COMPARE_FIELDS = (
    "Provider / product link / selected option",
    "Quote date and expiry",
    "Travel dates / party / room setup",
    "Pickup and return locations / arrangements",
    "Day-by-day itinerary / nights",
    "Road or flight / all transfers",
    "Private or shared services / occupancy",
    "Accommodation / rooms / meals",
    "Included activities / optional extras",
    "Entry charges / taxes / mandatory extras",
    "Quoted amount / currency / price basis",
    "Full party total with mandatory extras",
    "Availability confirmed for these dates?",
    "Deposit / balance / cancellation / changes",
    "Participant minimum and fallback",
    "Operator / booking confirmation / trip contact",
    "Unanswered questions to resolve",
)


CHECKLIST_MARKDOWN = """KATE — SAFARI QUOTE COMPARISON & BOOKING CHECKLIST
Free to save, print and share.
Source: https://kate-kenya-trip-planner.netlify.app/resources/safari-booking-checklist/

STEP 1 — CHECK TWO WRITTEN QUOTES
Write 'not confirmed' for unanswered items. An empty field is not an inclusion.

""" + "\n".join(f"[ ] {title}: {detail}" for title, detail in CHECKS) + """

YOUR TWO-QUOTE WORKSHEET
Use the same party, dates and room arrangement. Compare a full party total in
the same currency; request a matched-currency quote where possible. If you
convert a currency yourself, record the rate and date and treat the result as
an estimate, not a provider-confirmed total.

""" + "\n\n".join(f"{field}\n  Quote A: ______________________________\n  Quote B: ______________________________" for field in COMPARE_FIELDS) + """

DECISION BEFORE PAYMENT
[ ] My essential requirements are confirmed in writing.
[ ] I understand the full total, mandatory extras and payment requirements.
[ ] I have read the terms for the exact booking option.
[ ] I have saved the final quote / booking details and provider contact.
If an essential answer is missing, ask the provider before paying.

PROVIDER INQUIRY — REPLACE THE BRACKETS BEFORE SENDING
""" + INQUIRY_TEMPLATE + """

STEP 2 — COMPARE SUPPLIER OPTIONS
https://kate-kenya-trip-planner.netlify.app/mara/#safari-options
The previews here are 3-day Nairobi–Mara options. A displayed from price does
not establish availability for your dates or the total for your party. Confirm
the selected option and final terms on Viator before booking.

MORE PLANNING HELP
https://kate-kenya-trip-planner.netlify.app/guides/3-day-masai-mara-safari-from-nairobi/
https://kate-kenya-trip-planner.netlify.app/guides/private-vs-shared-masai-mara-safari/

AFFILIATE DISCLOSURE
KATE may earn a commission if you book through a Viator link. KATE provides
planning guidance and product previews; your booking is made with the supplier
through Viator. This checklist does not confirm any supplier's inclusions,
availability, price or booking terms. No contact details are required to use it.
"""


_check_items = "".join(
    f'<li><label><input type="checkbox" class="resource-check"> '
    f'<span><strong>{escape(title)}.</strong> {escape(detail)}</span></label></li>'
    for title, detail in CHECKS
)
_comparison_rows = "".join(
    f'<tr><th scope="row">{escape(field)}</th>'
    '<td><span class="resource-blank" aria-label="Quote A: write your answer">Write your answer</span></td>'
    '<td><span class="resource-blank" aria-label="Quote B: write your answer">Write your answer</span></td></tr>'
    for field in COMPARE_FIELDS
)


RESOURCE = {
    "path": "/resources/safari-booking-checklist/",
    "title": "Free Safari Booking Checklist & Two-Quote Comparison | KATE",
    "description": "Download a free safari booking checklist, compare two complete quotes and copy a provider inquiry. Check inclusions, party totals and terms before booking.",
    "body": '''
<section class="page-intro guide-intro">
<p class="eyebrow"><span class="eyebrow-dot"></span> FREE SAFARI PLANNING RESOURCE</p>
<h1>Two safari quotes. <em>One clear comparison.</em></h1>
<p>Use this checklist to find out what each quote actually covers. Save the worksheet, copy the inquiry and compare the answers before you book. No signup required.</p>
<div class="hero-actions"><a class="button button-primary" href="/resources/safari-booking-checklist.txt" download="KATE-safari-booking-checklist.txt">Download the free checklist <span aria-hidden="true">↓</span></a><a class="button button-quiet" href="#provider-inquiry">Copy the provider inquiry</a></div>
</section>
<article class="guide-content resource-content">
<section aria-labelledby="resource-step-one"><p class="section-kicker">STEP 1 · CHECK</p><h2 id="resource-step-one">Ask the same questions of both providers.</h2>
<p>Start with the same dates, party and room arrangement. Tick each item when you have a clear answer for both quotes. Write <strong>“not confirmed”</strong> beside unanswered questions; an empty field does not mean included.</p>
<ul class="resource-checklist">''' + _check_items + '''</ul>
<p>Your ticks stay on this page only; they are not saved after a reload. Download the plain-text worksheet to keep your notes, or use your browser’s print command to print this page.</p></section>

<section aria-labelledby="resource-compare-title"><h2 id="resource-compare-title">Put Quote A and Quote B side by side.</h2>
<p>This is a blank comparison worksheet, not a supplier quote. Fill it in on paper or in the download. Keep optional extras separate from mandatory charges so you can see what you must pay.</p>
<div class="resource-table-wrap"><table class="resource-comparison"><caption>Two quotes for the same trip requirements</caption><thead><tr><th scope="col">What to compare</th><th scope="col">Quote A</th><th scope="col">Quote B</th></tr></thead><tbody>''' + _comparison_rows + '''</tbody></table></div>
<p>Compare full party totals in the same currency. Ask for a matched-currency quote where possible. If you convert a currency yourself, note the rate and date and treat the result as an estimate. Do not compare a per-person headline amount with a full party total.</p>
<p><strong>Before payment:</strong> confirm your essential requirements in writing, understand the total and mandatory extras, read the exact option’s terms and save the final quote or booking details. Resolve missing essential answers with the provider.</p></section>

<section id="provider-inquiry" aria-labelledby="resource-inquiry-title"><h2 id="resource-inquiry-title">Copy one complete inquiry.</h2>
<p>Replace the brackets with your own requirements, then send it through the provider’s contact channel. KATE does not send this message or collect its contents.</p>
<label for="safari-provider-inquiry">Provider inquiry template</label>
<textarea id="safari-provider-inquiry" class="resource-inquiry" data-copy-template readonly rows="24" spellcheck="false">''' + escape(INQUIRY_TEMPLATE) + '''</textarea>
<button type="button" class="button button-primary" data-copy-template-button aria-controls="safari-provider-inquiry">Copy inquiry</button>
<p class="resource-copy-status" data-copy-template-status role="status" aria-live="polite"></p>
<p>If copying is unavailable, select the text above and use your device’s copy command. You can also find the inquiry in the <a href="/resources/safari-booking-checklist.txt" download="KATE-safari-booking-checklist.txt">free checklist download</a>.</p></section>

<section><h2>Need help deciding what to ask?</h2><ul><li><a href="/guides/3-day-masai-mara-safari-from-nairobi/">Plan a three-day Maasai Mara safari from Nairobi</a>: departure, daily itinerary and return requirements.</li><li><a href="/guides/private-vs-shared-masai-mara-safari/">Compare private and shared safaris</a>: exclusivity, occupancy and group arrangements.</li></ul>
<p>Share this checklist with your travel companions using the page address. It is free to download, print and share.</p></section>
</article>
<section class="decision-note"><div class="note-mark">i</div><div><h2>Check the selected option before booking</h2><p>This checklist does not verify any supplier’s inclusions, availability, price or terms. A displayed from price does not confirm the cost for your party. Review dates, traveler details, the exact option and the final total on Viator.</p><p><strong>Affiliate disclosure:</strong> KATE may earn a commission if you book through a Viator link. KATE provides planning guidance and product previews; your booking is made with the supplier through Viator.</p></div></section>
<section class="mara-cta"><div><p class="section-kicker">STEP 2 · COMPARE OFFERS</p><h2>Explore options with your checklist ready.</h2><p>Start with 3-day Nairobi–Mara supplier previews, then confirm the details for your actual dates and party.</p></div><a class="button button-light" href="/mara/#safari-options">Compare 3-day safari options <span aria-hidden="true">↗</span></a></section>
''',
}
