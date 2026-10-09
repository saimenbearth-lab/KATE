"""A bilingual, flight-first guide to KATE's separate Nairobi bookings."""
from html import escape


PATH = '/guides/nairobi-airport-transfers-and-safari-extras/'
TITLE = 'Nairobi Airport Transfers and Activities Before or After a Safari'
TITLE_DE = 'Nairobi: Flughafentransfers und Aktivitäten vor oder nach der Safari'
DESCRIPTION = 'Plan Nairobi airport pickup and short activities around your safari. Check flight timing, luggage, entry charges and separate booking terms before choosing.'
DESCRIPTION_DE = 'Plane Flughafentransfers und kurze Aktivitäten in Nairobi rund um deine Safari. Prüfe Flugzeiten, Gepäck, Eintrittsgebühren und separate Buchungsbedingungen.'

BRIEF_EN = '''Subject: Nairobi transfer / activity for [date] — [party size]

Hello,
We are considering [product link and exact option] on [date].
Our party: [adults], [children and ages], [luggage / child seats needed].
Arrival: [airport, terminal, flight number, scheduled local arrival].
Pickup: [airport / hotel / other address], earliest ready time [local time].
Required drop-off: [exact location], latest arrival [local time].
Our onward flight or safari departure: [date, time, airport / meeting point].

Please confirm in writing:
1. Availability, pickup instructions and a local contact for this exact option.
2. The full pickup-to-drop-off schedule, including every transfer and activity.
3. Vehicle and luggage capacity, private/shared arrangements and child seats.
4. One total for our party in [currency], including mandatory charges.
5. Which entry tickets, parking, waiting and other charges are excluded.
6. Delay, missed-pickup, cancellation and change terms for this booking.
7. Whether our required drop-off time can be met, and any timing uncertainty.

If this includes an attraction, please confirm its admission arrangements and
whether any ticket needs a separate reservation or payment.
Please distinguish confirmed details from estimates.
Thank you, [name]
'''

BRIEF_DE = '''Betreff: Nairobi-Transfer / Aktivität am [Datum] — [Gruppengröße]

Guten Tag,
wir prüfen [Produktlink und genaue Option] am [Datum].
Unsere Gruppe: [Erwachsene], [Kinder und Alter], [Gepäck / benötigte Kindersitze].
Ankunft: [Flughafen, Terminal, Flugnummer, planmäßige lokale Ankunftszeit].
Abholung: [Flughafen / Hotel / andere Adresse], frühestens bereit ab [Ortszeit].
Ziel: [genauer Ort], späteste erforderliche Ankunft [Ortszeit].
Weiterflug oder Safari-Abfahrt: [Datum, Uhrzeit, Flughafen / Treffpunkt].

Bitte bestätigen Sie schriftlich:
1. Verfügbarkeit, genaue Abholung und lokalen Kontakt für diese Option.
2. Gesamtablauf von Abholung bis Ziel, mit allen Transfers und Aktivitäten.
3. Fahrzeug- und Gepäckkapazität, private/gemeinsame Nutzung und Kindersitze.
4. Einen Gruppen-Gesamtpreis in [Währung] einschließlich Pflichtkosten.
5. Ausgeschlossene Eintritts-, Park-, Warte- und sonstige Zusatzkosten.
6. Regeln bei Verspätung, verpasster Abholung, Storno und Änderungen.
7. Ob unsere benötigte Zielzeit eingehalten werden kann und welche Unsicherheit bleibt.

Bei einem Besuch einer Attraktion bestätigen Sie bitte die Eintrittsregelung
und ob Tickets separat reserviert oder bezahlt werden müssen.
Bitte unterscheiden Sie bestätigte Angaben von Schätzungen.
Vielen Dank, [Name]
'''


def body(language='en'):
    de = language == 'de'
    def text(en, german):
        return german if de else en

    sections = (
        (
            'Choose the job first: transfer or activity',
            'Wähle zuerst: Transfer oder Aktivität',
            'An airport transfer solves a pickup and drop-off need. A park visit or city activity adds another experience. They are different bookings: an activity title does not establish that an airport transfer, admission or a hotel pickup is included.',
            'Ein Flughafentransfer bringt dich vom vereinbarten Abholort zum Ziel. Ein Parkbesuch oder eine Stadtaktivität ergänzt deine Reise. Das sind unterschiedliche Buchungen: Ein Aktivitätstitel bestätigt weder Flughafentransfer noch Eintritt oder Hotelabholung.',
        ),
        (
            'Build the schedule around the flight or safari departure',
            'Plane vom Flug oder der Safari-Abfahrt aus',
            'Use the exact airports, terminals, local dates and times from your travel confirmations. Your flight arrival time is not the time you are ready for pickup. Allow for arrival procedures, baggage, travel between each stop and the check-in requirements confirmed by your airline. Ask the supplier for the full pickup-to-drop-off schedule. KATE does not provide a guaranteed airport connection or a universal safe transfer time.',
            'Nutze genaue Flughäfen, Terminals, lokale Daten und Uhrzeiten aus deinen Reisebestätigungen. Die Flugankunft ist nicht der Zeitpunkt, an dem du zur Abholung bereit bist. Berücksichtige Einreise, Gepäck, Fahrten zwischen allen Stopps und die von deiner Fluggesellschaft bestätigten Check-in-Vorgaben. Bitte den Anbieter um den Gesamtablauf von Abholung bis Ziel. KATE garantiert keinen Anschluss und gibt keine pauschal sichere Transferzeit an.',
        ),
        (
            'A free afternoon is different from a short flight connection',
            'Ein freier Nachmittag ist anders als ein kurzer Fluganschluss',
            'For a hotel-based day before or after a safari, establish the hotel pickup and return arrangements and avoid overlapping them with the safari departure. For a flight connection, check whether you can leave the airport, where your bags will be and when you must return. If essential timings or entry requirements are unresolved, arrange the transfer first and leave the activity unbooked.',
            'Für einen Tag im Hotel vor oder nach der Safari bestätigst du Hotelabholung und Rückkehr und vermeidest Überschneidungen mit der Safari-Abfahrt. Bei einem Fluganschluss prüfst du, ob du den Flughafen verlassen kannst, wo dein Gepäck bleibt und wann du zurück sein musst. Sind wichtige Zeiten oder Einreisevoraussetzungen offen, kläre zuerst den Transfer und buche die Aktivität noch nicht.',
        ),
        (
            'Match the vehicle to people and luggage',
            'Stimme das Fahrzeug auf Personen und Gepäck ab',
            'Give the supplier the number of travelers, children’s ages and luggage count. Ask about luggage capacity, child seats if needed, the precise meeting point, flight-delay handling, included waiting time and a local contact. Confirm whether the vehicle or activity is private or shared; neither follows automatically from a product title.',
            'Nenne dem Anbieter die Zahl der Reisenden, das Alter der Kinder und die Gepäckstücke. Frage nach Gepäckkapazität, benötigten Kindersitzen, genauem Treffpunkt, Umgang mit Flugverspätungen, enthaltener Wartezeit und einem lokalen Kontakt. Bestätige private oder gemeinsame Nutzung von Fahrzeug und Aktivität; der Produkttitel allein belegt das nicht.',
        ),
        (
            'Check admission and the full party total',
            'Prüfe Eintritt und Gruppen-Gesamtpreis',
            'Ask which attraction tickets, park entry, parking and other mandatory charges are included in your selected option. Do not add a separate park ticket before checking whether the supplier already provides it. For independent KWS park arrangements, consult the official KWS eCitizen service and verify the applicable category and date. KATE does not publish a verified fee schedule. Request one final total for your exact party in a stated currency.',
            'Frage, welche Tickets, Parkeintritte, Parkgebühren und anderen Pflichtkosten in der gewählten Option enthalten sind. Kaufe ein Parkticket erst separat, wenn geklärt ist, ob der Anbieter es bereits bereitstellt. Für eigenständige KWS-Parkbesuche nutze den offiziellen KWS-eCitizen-Dienst und prüfe passende Kategorie und Datum. KATE veröffentlicht keine verifizierte Gebührenliste. Bitte um einen Endpreis für deine genaue Gruppe in einer angegebenen Währung.',
        ),
        (
            'Keep each booking and its terms separate',
            'Halte Buchungen und ihre Bedingungen getrennt',
            'A safari, airport transfer and Nairobi activity can have different operators and cancellation terms. Confirm what each booking covers, save the operator contacts and check what happens if a flight or safari return changes. A supplier from price does not confirm availability or your party total. Review the final option and terms on Viator before paying.',
            'Safari, Flughafentransfer und Nairobi-Aktivität können unterschiedliche Veranstalter und Stornobedingungen haben. Bestätige den Umfang jeder Buchung, speichere die Kontakte und prüfe, was bei Flugänderungen oder verspäteter Safari-Rückkehr gilt. Ein Ab-Preis bestätigt weder Verfügbarkeit noch Gruppen-Gesamtpreis. Prüfe genaue Option und Bedingungen vor der Zahlung auf Viator.',
        ),
    )
    article = ''.join('<section><h2>' + escape(text(en_h, de_h)) + '</h2><p>' + escape(text(en_p, de_p)) + '</p></section>' for en_h, de_h, en_p, de_p in sections)
    inquiry = BRIEF_DE if de else BRIEF_EN
    return f'''
<section class="page-intro guide-intro">
<p class="eyebrow">{text('NAIROBI · TRANSFERS AND SHORT ACTIVITIES', 'NAIROBI · TRANSFERS UND KURZE AKTIVITÄTEN')}</p>
<h1>{text('Nairobi before or after your safari: <em>plan the transfer and the extra day.</em>', 'Nairobi vor oder nach der Safari: <em>plane den Transfer und den Zusatztag.</em>')}</h1>
<p>{text('Have a free day in Nairobi, or need a reliable pickup plan? Start with your flight and safari schedule, then compare a separate transfer or activity that fits.', 'Du hast einen freien Tag in Nairobi oder brauchst einen klaren Abholplan? Beginne mit Flug und Safari-Zeiten und vergleiche dann passende separate Transfers oder Aktivitäten.')}</p>
<div class="hero-actions"><a class="button button-primary" href="/mara/#nairobi-extras">{text('See Nairobi activities and transfers', 'Nairobi-Aktivitäten und Transfers ansehen')} <span aria-hidden="true">↗</span></a><a class="button button-quiet" href="#nairobi-inquiry">{text('Prepare my pickup request', 'Meine Abholanfrage vorbereiten')}</a></div>
</section>
<article class="guide-content">{article}
<section><h2>{text('Official park information', 'Offizielle Parkinformationen')}</h2><p><a href="https://kws.ecitizen.go.ke/">{text('Kenya Wildlife Service: official eCitizen service', 'Kenya Wildlife Service: offizieller eCitizen-Dienst')}</a>. {text('Use the operator’s written inclusions and current official information; do not infer tickets or fees from a preview.', 'Nutze schriftliche Angaben des Veranstalters und aktuelle offizielle Informationen; leite Tickets oder Gebühren nicht aus einer Vorschau ab.')}</p></section>
<section id="nairobi-inquiry"><h2>{text('Copy a pickup and activity request', 'Abhol- und Aktivitätsanfrage kopieren')}</h2>
<p>{text('Replace the brackets and send this through the supplier’s contact channel. This page does not send a message or collect your flight details.', 'Ersetze die Angaben in Klammern und nutze den Kontaktweg des Anbieters. Diese Seite sendet keine Nachricht und erfasst deine Flugdaten nicht.')}</p>
<label for="nairobi-provider-template">{text('Your message to the supplier', 'Deine Nachricht an den Anbieter')}</label>
<textarea class="resource-inquiry" id="nairobi-provider-template" rows="20" readonly data-copy-template>{escape(inquiry)}</textarea>
<button class="button button-primary" type="button" data-copy-template-button aria-controls="nairobi-provider-template">{text('Copy the request', 'Anfrage kopieren')}</button><p role="status" data-copy-template-status></p></section>
</article>
<section class="decision-note"><div class="note-mark">i</div><div><h2>{text('Separate options, confirmed with the supplier', 'Separate Angebote, beim Anbieter bestätigen')}</h2><p>{text('KATE previews short Nairobi activities and transfers from the supplier catalogue. An airport connection, admission, pickup, date availability and final party price must be confirmed for the specific option.', 'KATE zeigt kurze Nairobi-Aktivitäten und Transfers aus dem Anbieterkatalog. Anschluss, Eintritt, Abholung, Terminverfügbarkeit und Gruppen-Endpreis müssen für die konkrete Option bestätigt werden.')}</p><p>{text('Affiliate disclosure: KATE may earn a commission if you book through a Viator link.', 'Partnerhinweis: KATE kann eine Provision erhalten, wenn du über einen Viator-Link buchst.')}</p></div></section>
<section class="mara-cta"><div><h2>{text('Choose the next part of your trip.', 'Wähle den nächsten Teil deiner Reise.')}</h2><p>{text('Compare Nairobi extras or return to the safari shortlist.', 'Vergleiche Nairobi-Ergänzungen oder kehre zu den Safari-Angeboten zurück.')}</p></div><div class="hero-actions"><a class="button button-light" href="/mara/#nairobi-extras">{text('See Nairobi activities and transfers', 'Nairobi-Aktivitäten und Transfers ansehen')} ↗</a><a class="button button-light" href="/mara/#safari-options">{text('Compare safari options', 'Safari-Angebote vergleichen')} ↗</a></div></section>
'''


GUIDE = {'path': PATH, 'title': TITLE, 'description': DESCRIPTION, 'body': body(), 'body_de': body('de'), 'faqs': ()}
