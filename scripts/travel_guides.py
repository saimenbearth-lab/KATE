"""Original KATE planning guides; no supplier prices or availability claims."""
from __future__ import annotations

from html import escape
from scripts.nairobi_guide import GUIDE as NAIROBI_GUIDE


def _faq_section(faqs: tuple[dict[str, str], ...]) -> str:
    answers = "".join(
        f'<section class="guide-faq"><h3>{escape(item["question"])}</h3>'
        f'<p>{escape(item["answer"])}</p></section>'
        for item in faqs
    )
    return '<section aria-labelledby="guide-faq-title"><h2 id="guide-faq-title">Frequently asked questions</h2>' + answers + '</section>'


THREE_DAY_FAQS = (
    {
        "question": "Is a 3-day Maasai Mara safari from Nairobi enough?",
        "answer": "Judge the actual itinerary rather than the number of days in the title. Ask how much of each day is allocated to transfers, activities and overnight stays. Check the departure and return arrangements against your wider trip. A three-day label alone does not confirm the time you will spend on safari.",
    },
    {
        "question": "What should a 3-day safari quote include?",
        "answer": "Request the full itinerary, departure and return details, transport arrangements, accommodation, meal plan, activities, fees, exclusions and cancellation terms. These are items to verify, not inclusions that every safari provides. Ask for the total in a stated currency for your exact party and dates.",
    },
    {
        "question": "Are park fees included in a Maasai Mara safari price?",
        "answer": "Do not assume they are included. Ask the provider which entry charges and other fees are covered, what remains payable separately and how those charges affect your total party price. KATE does not publish an independently verified park-fee schedule.",
    },
    {
        "question": "Should I choose road or fly-in travel from Nairobi?",
        "answer": "Compare the complete journey for your dates. For a road option, confirm the vehicle and transfer arrangements. For a fly-in option, confirm the operator, flight schedule, baggage rules, airstrip and onward transfers. Evaluate the full itinerary and total price; KATE does not declare a universal winner.",
    },
    {
        "question": "Does a supplier from price confirm my safari booking cost?",
        "answer": "No. A catalog from price does not confirm availability for your dates or the cost for your party. Check your date, traveler details, selected option, inclusions and final total on Viator before booking.",
    },
)


PRIVATE_SHARED_FAQS = (
    {
        "question": "What is the difference between a private and a shared Maasai Mara safari?",
        "answer": "Use the terms as questions to investigate. A private label may refer to a vehicle, guide, transfer or a particular activity; it does not establish that every part of the trip is exclusive. For a shared trip, confirm which services are shared and with how many travelers. Ask the provider to spell out the arrangement.",
    },
    {
        "question": "Is a shared safari always cheaper than a private safari?",
        "answer": "No comparison is reliable without quotes for the same dates and party, with the same scope and exclusions. Compare the full party totals rather than unmatched per-person headline prices. Accommodation, transfers, included services and additional charges can differ between the quotes.",
    },
    {
        "question": "Does a private safari guarantee a flexible itinerary?",
        "answer": "No. Confirm the actual schedule, what changes the provider allows and any additional costs. An exclusive vehicle does not by itself establish flexibility in accommodation, transfers, departure times or activities.",
    },
    {
        "question": "What should I ask about group size on a shared safari?",
        "answer": "Ask for the maximum group and vehicle occupancy, seating arrangements, guide arrangements and whether the booking requires a minimum number of participants. Confirm what happens if that minimum is not reached and which cancellation or refund terms apply.",
    },
    {
        "question": "Can I book a private or shared safari directly with KATE?",
        "answer": "KATE provides planning guidance and supplier product previews. It does not verify the private or shared classification of every preview, or take your booking. Open the product on Viator, confirm the specific arrangement and review dates, traveler details, final price and terms before booking.",
    },
)


THREE_DAY_BODY = '''
<section class="page-intro guide-intro">
<p class="eyebrow"><span class="eyebrow-dot"></span> NAIROBI TO MAASAI MARA · PLANNING GUIDE</p>
<h1>How to choose a <em>3-day Maasai Mara safari</em> from Nairobi.</h1>
<p>A useful safari comparison starts with the full journey: where it begins, what each day contains, what is included and what your party will pay. Use this checklist before treating a tour title or from price as a complete offer.</p>
<div class="hero-actions"><a class="button button-primary" href="/mara/#safari-options">Explore 3-day safari options <span aria-hidden="true">↗</span></a><a class="button button-quiet" href="/planner/">Outline my trip</a></div>
</section>
<article class="guide-content">
<section><h2>Start with your departure and return requirements</h2>
<p>Write down your starting point in Nairobi, your preferred departure date, party size and any fixed commitment after the safari. If you have onward travel, ask the provider to explain the return arrangements before you commit to that connection.</p>
<p>Confirm the pickup location, the stated departure time, the return location and which transfers are included. Do not assume that “from Nairobi” means collection from your accommodation or that an airport transfer is part of the price. Ask what happens if your arrival or pickup plans change.</p></section>

<section><h2>Read the three days as a schedule</h2>
<p>Ask for a day-by-day itinerary that identifies transfers, planned activities and overnight arrangements. A title tells you the marketed duration; the schedule tells you how the trip fits your priorities. Use the following questions as a review framework, not as a promised itinerary.</p>
<ol><li><strong>Departure day:</strong> Where do you meet, which transfer is arranged and what activities are scheduled after arrival?</li>
<li><strong>Middle day:</strong> Which activities are included, what is optional and what accommodation or meal arrangements apply?</li>
<li><strong>Return day:</strong> What happens before departure and how does the provider arrange the return to Nairobi?</li></ol>
<p>Ask the provider to resolve unclear timings and explain any changes that depend on conditions or operating arrangements. KATE’s planner creates an outline to discuss; it is not a supplier itinerary.</p></section>

<section><h2>Compare road and fly-in journeys from end to end</h2>
<p>For an overland option, check the vehicle, pickup and return arrangements, and each transfer in the itinerary. If comfort or photography matters to you, ask specific questions about the vehicle and how activities are organized instead of inferring those details from the product title.</p>
<p>For a fly-in option, check the flight operator, schedule, baggage rules, arrival airstrip and ground transfers. Establish whether the quoted option includes the flights and onward transfers you need. A flight segment alone does not describe the full safari.</p>
<p>Use the <a href="/mara/">road versus fly-in planning checklist</a> to compare these details. Product previews are not independently classified into transport categories by KATE.</p></section>

<section><h2>Request a complete price for your party</h2>
<p>Give the provider your actual dates and traveler details, then ask for one total in a stated currency. Check whether a displayed amount is per person, per booking or another basis, and which option it represents. A supplier from price is a starting point for investigation, not your final quote.</p>
<ul><li>Identify the accommodation and room arrangements in the selected option.</li>
<li>Confirm the meal plan, activities and transfers that are included.</li>
<li>Ask which entry charges, taxes and other fees are covered or excluded.</li>
<li>List any optional extras and the charges that could be payable separately.</li>
<li>Check cancellation terms, payment requirements and the booking confirmation process.</li></ul>
<p>Keep the scope of the quotes consistent. Comparing a basic option with a different accommodation or transport package can make a headline price misleading even when both products use the same trip length. If group arrangements matter, use the <a href="/guides/private-vs-shared-masai-mara-safari/">private versus shared safari checklist</a> to clarify what is exclusive to your party.</p></section>

<section><h2>A message you can send to the provider</h2>
<blockquote><p>We are considering a three-day Maasai Mara safari from Nairobi for our party on our preferred dates. Please confirm the pickup and return details, full daily itinerary, vehicle or flight arrangements, accommodation and room setup, meals and activities. Which entry charges and other fees are included or excluded? Please provide the full party total, currency, availability for our dates and cancellation terms for the specific option we would book.</p></blockquote>
<p>Add your own priorities, such as comfort or photography, as questions. Ask how the provider would meet them; a preference entered in the KATE planner does not establish an included service.</p></section>
''' + _faq_section(THREE_DAY_FAQS) + '''
</article>
<section class="decision-note"><div class="note-mark">i</div><div><h2>Check the final details on Viator</h2><p>Supplier product previews may show from prices. KATE does not confirm date-specific availability, the total for your party or every itinerary detail. Review the selected option and full terms on Viator before booking.</p><p><strong>Affiliate disclosure:</strong> KATE may earn a commission if you book through a Viator link.</p></div></section>
<section class="mara-cta"><div><p class="section-kicker">NEXT STEP</p><h2>Explore the options for your trip.</h2><p>Use supplier previews as a starting point, then confirm the details with the provider.</p></div><a class="button button-light" href="/mara/#safari-options">See 3-day safari options <span aria-hidden="true">↗</span></a></section>
'''


PRIVATE_SHARED_BODY = '''
<section class="page-intro guide-intro">
<p class="eyebrow"><span class="eyebrow-dot"></span> MAASAI MARA · SAFARI COMPARISON GUIDE</p>
<h1>Private or shared Maasai Mara safari: <em>what to compare.</em></h1>
<p>Choose by the confirmed arrangements for your party. Establish what is exclusive, what is shared and what the full quote covers before using either label to judge value or comfort.</p>
<div class="hero-actions"><a class="button button-primary" href="/mara/#safari-options">Explore safari options <span aria-hidden="true">↗</span></a><a class="button button-quiet" href="/planner/">Outline my trip</a></div>
</section>
<article class="guide-content">
<section><h2>Ask what “private” or “shared” applies to</h2>
<p>Break the trip into services: the transfer from Nairobi, the safari vehicle, guide arrangements, activities, accommodation and return transfer. Ask which of these are exclusive to your party and which involve other travelers. Do not extend a claim about one service to the whole trip.</p>
<p>For a private option, request a written explanation of what your party has exclusive use of. For a shared option, ask how participants are grouped and whether the group or vehicle can change during the itinerary. Neither label substitutes for a complete description of the selected booking option.</p></section>

<section><h2>Compare the vehicle and group arrangements</h2>
<p>Discuss the maximum number of passengers, seating arrangements and guide provision. If your priority is photography, comfort or an unhurried pace, turn that into concrete questions: what vehicle is planned, how are stops organized and what choices can your party make?</p>
<p>For a shared departure, ask whether there is a minimum participant requirement and what happens if it is not met. Confirm any changes, cancellation or refund arrangements in the actual booking terms. For a private departure, verify that the vehicle or guide exclusivity you need is part of the option being quoted.</p>
<p>These are questions to put to the provider. KATE does not verify vehicle occupancy, exclusive use or the private/shared classification of every product preview.</p></section>

<section><h2>Check flexibility rather than assuming it</h2>
<p>If you want control over departure times, activities or stops, ask which changes the provider permits. Request the standard schedule first, then clarify the choices available and any additional cost. An exclusive vehicle does not by itself establish that accommodation, transfers or activities can be changed.</p>
<p>For a shared itinerary, ask which timings are fixed and how the provider handles different preferences within the group. Keep your onward travel and pickup requirements in view when assessing either arrangement. Confirm the exact return plan before relying on it for another travel commitment.</p></section>

<section><h2>Compare total party prices on the same basis</h2>
<p>Request quotes for the same dates and traveler details. Compare the full totals and the included services before drawing a conclusion from a per-person amount or catalog from price. A lower headline figure may describe a different room setup, transfer arrangement or package scope.</p>
<ul><li><strong>Travel:</strong> Which departure, return and other transfers are covered?</li>
<li><strong>Stay:</strong> Which accommodation, room arrangements and meal plan are quoted?</li>
<li><strong>Activities:</strong> Which activities are included, optional or payable separately?</li>
<li><strong>Fees:</strong> Which entry charges and other costs remain outside the total?</li>
<li><strong>Terms:</strong> What cancellation, payment and confirmation rules apply to that option?</li></ul>
<p>Do not assume a shared safari always costs less or that a private safari always offers better value. The useful comparison is the price and scope offered for your actual party.</p></section>

<section><h2>Keep transport mode separate from group type</h2>
<p>Private versus shared describes an arrangement to verify. Road versus fly-in describes a different part of the journey. Check both rather than interpreting one label as evidence of the other.</p>
<p>For road travel, confirm the vehicle and the complete transfer chain. For fly-in travel, confirm the flight operator, schedule, baggage rules, airstrip and onward transfers. Ask whether the selected option covers the full journey you need. Use KATE’s <a href="/mara/">road and fly-in checklist</a> for the questions to resolve.</p></section>

<section><h2>Make your decision from the provider’s answers</h2>
<p>Write down the requirements that matter to your party: exclusive use if needed, an acceptable group arrangement, your comfort preferences, a clear itinerary and a complete price. Compare the answers to those requirements. If an important detail remains unclear, resolve it before paying instead of relying on the tour title.</p>
<p>For a focused Nairobi departure, the <a href="/guides/3-day-masai-mara-safari-from-nairobi/">three-day Maasai Mara planning guide</a> helps you review departure, overnight and return arrangements. The <a href="/planner/">trip planner</a> can organize your preferences into an outline to discuss with a provider.</p>
<blockquote><p>Please confirm which vehicles, guide services, transfers and activities would be exclusive to our party and which would be shared. What are the maximum group size and seating arrangements? Are there participant requirements or permitted itinerary changes? Please quote the complete price for our dates and party, including a clear list of exclusions and the applicable cancellation terms.</p></blockquote></section>
''' + _faq_section(PRIVATE_SHARED_FAQS) + '''
</article>
<section class="decision-note"><div class="note-mark">i</div><div><h2>Verify the selected option</h2><p>KATE’s supplier previews do not establish whether a trip is private or shared. Confirm the arrangement, dates, total party price and terms on Viator before booking.</p><p><strong>Affiliate disclosure:</strong> KATE may earn a commission if you book through a Viator link.</p></div></section>
<section class="mara-cta"><div><p class="section-kicker">NEXT STEP</p><h2>Find options to investigate.</h2><p>Explore 3-day Nairobi–Mara product previews, then ask the questions that matter to your party.</p></div><a class="button button-light" href="/mara/#safari-options">See safari options <span aria-hidden="true">↗</span></a></section>
'''


GUIDES = (
    NAIROBI_GUIDE,
    {
        "path": "/guides/3-day-masai-mara-safari-from-nairobi/",
        "title": "3-Day Maasai Mara Safari from Nairobi: Planning Checklist",
        "description": "Plan a 3-day Maasai Mara safari from Nairobi. Compare the itinerary, road or fly-in transfers, inclusions, party price and booking terms before you decide.",
        "body": THREE_DAY_BODY,
        "faqs": THREE_DAY_FAQS,
    },
    {
        "path": "/guides/private-vs-shared-masai-mara-safari/",
        "title": "Private vs Shared Maasai Mara Safari: What to Compare",
        "description": "Compare private and shared Maasai Mara safaris. Check vehicle exclusivity, group size, flexibility, inclusions and the total for your party before booking.",
        "body": PRIVATE_SHARED_BODY,
        "faqs": PRIVATE_SHARED_FAQS,
    },
)
