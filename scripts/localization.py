"""Handwritten EN/DE localization; structural parsing preserves form/API values."""
from __future__ import annotations

from html import escape
from html.parser import HTMLParser
import json
from urllib.parse import urlsplit, urlunsplit

SITE_URL = 'https://kate-kenya-trip-planner.netlify.app'
PUBLIC_PATHS = ('/', '/mara/', '/planner/', '/guides/', '/guides/3-day-masai-mara-safari-from-nairobi/', '/guides/private-vs-shared-masai-mara-safari/', '/resources/safari-booking-checklist/')

# Exact visible-text matches, not replacements inside HTML, IDs or form values.
_PAIRS = '''Home\tStartseite
Trip Planner\tReiseplaner
3-day Mara\tMara: 3 Tage
Control Center\tVerwaltung
Safari guides\tSafari-Ratgeber
Free booking checklist\tKostenlose Buchungscheckliste
Plan a trip\tReise planen
Road vs fly-in\tStraße oder Flug
PLANNING PREVIEW\tPLANUNGSHILFE
Supplier previews · Confirm dates and total price on Viator\tAngebotsvorschau · Termine und Gesamtpreis auf Viator bestätigen
KENYA TRIP PLANNING · PREVIEW\tKENIA-REISEPLANUNG · VORSCHAU
Explore 3-day Maasai Mara safaris.\tEntdecke 3-tägige Safaris in der Maasai Mara.
Start in Nairobi. Browse supplier product previews and from prices, then check your dates, itinerary and full party price on Viator.\tStarte in Nairobi. Vergleiche Angebotsvorschauen und Ab-Preise. Prüfe danach Termine, Reiseverlauf und Gesamtpreis für deine Gruppe auf Viator.
See 3-day safari options\t3-tägige Safari-Angebote ansehen
Plan my trip\tMeine Reise planen
From prices only.\tNur Ab-Preise.
Confirm dates and total price on Viator.\tTermine und Gesamtpreis auf Viator bestätigen.
Illustrative image · not an inventory signal\tSymbolbild · kein Nachweis eines verfügbaren Angebots
ONE DECISION\tEINE ENTSCHEIDUNG
AT A TIME\tNACH DER ANDEREN
A useful first step\tEin hilfreicher erster Schritt
Clarity before the commitment.\tKlarheit vor der Buchung.
KATE helps frame what to check next—not what to book. Set your trip inputs, then compare the details that matter for your dates.\tKATE hilft dir, die nächsten Prüfpunkte festzulegen. Gib deine Reisewünsche ein und vergleiche die Details für deine Termine.
FOCUSED COMPARISON\tGEZIELTER VERGLEICH
3 DAYS\t3 TAGE
Explore 3-day supplier previews. Check dates, total party price and inclusions on Viator before booking.\tEntdecke 3-tägige Angebotsvorschauen. Prüfe Termine, Gesamtpreis für die Gruppe und enthaltene Leistungen vor der Buchung auf Viator.
Preview, not a booking service.\tPlanungsvorschau, kein Buchungsdienst.
Supplier product previews can be loaded on the Mara page. From prices are not date-specific quotes. KATE may earn a commission from Viator bookings.\tAuf der Mara-Seite kannst du Angebotsvorschauen laden. Ab-Preise sind keine verbindlichen Preise für deine Termine. KATE kann bei Viator-Buchungen eine Provision erhalten.
· Kenya trip planning\t· Kenia-Reiseplanung
Independent planning guide. Supplier previews show from prices only. Check dates, full terms and total party price on Viator before booking. KATE may earn a commission through affiliate links.\tUnabhängige Planungshilfe. Angebotsvorschauen zeigen nur Ab-Preise. Prüfe Termine, vollständige Bedingungen und Gesamtpreis für deine Gruppe vor der Buchung auf Viator. KATE kann über Partnerlinks eine Provision erhalten.
3-DAY TRIP · STARTING IN NAIROBI\t3-TÄGIGE REISE · START IN NAIROBI
Nairobi to the Maasai Mara:\tVon Nairobi in die Maasai Mara:
3-day safari options.\tSafari-Angebote für 3 Tage.
Browse supplier product previews and from prices for a 3-day safari. Check your dates, full itinerary and total party price on Viator before booking.\tVergleiche Angebotsvorschauen und Ab-Preise für eine 3-tägige Safari. Prüfe vor der Buchung Termine, vollständigen Reiseverlauf und Gesamtpreis für deine Gruppe auf Viator.
3 days\t3 Tage
2 days\t2 Tage
4 days\t4 Tage
Nairobi origin\tStart in Nairobi
Decision guide\tEntscheidungshilfe
VIATOR PRODUCT PREVIEWS\tVIATOR-ANGEBOTSVORSCHAU
3-day Maasai Mara safari options\t3-tägige Safari-Angebote für die Maasai Mara
Supplier from prices are a starting point. Final dates, total party price and availability are checked on Viator. Confirm the route, departure point and full itinerary before deciding.\tAb-Preise dienen als Ausgangspunkt. Termine, Gesamtpreis für die Gruppe und Verfügbarkeit werden auf Viator geprüft. Bestätige Route, Abfahrtsort und vollständigen Reiseverlauf vor deiner Entscheidung.
Find a useful safari shortlist\tFinde passende Safari-Angebote zum Prüfen
A guided planning assistant: choose your trip length and what you want to check. It uses supplier previews, without checking your dates or matching trips to your group.\tDer Planungsassistent hilft beim Vergleichen: Wähle Reisedauer und Prüfschwerpunkt. Er nutzt Angebotsvorschauen, ohne Termine zu prüfen oder Angebote auf deine Gruppe abzustimmen.
Trip length\tReisedauer
Price currency\tPreiswährung
What matters most?\tWas ist dir am wichtigsten?
Total cost\tGesamtkosten
Comfort and accommodation\tKomfort und Unterkunft
Travel time and transfers\tReisezeit und Transfers
Show safari options\tSafari-Angebote anzeigen
Your booking checklist\tDeine Buchungscheckliste
Confirm your dates, number of travelers and the total price for your party.\tBestätige Termine, Zahl der Reisenden und Gesamtpreis für deine Gruppe.
Check park fees, transfers, meals and every extra charge.\tPrüfe Parkgebühren, Transfers, Mahlzeiten und alle Zusatzkosten.
Read the cancellation terms before paying.\tLies die Stornobedingungen vor der Zahlung.
From prices are not a quote for your group. Check the final price on Viator.\tAb-Preise sind kein verbindlicher Preis für deine Gruppe. Prüfe den Endpreis auf Viator.
The assistant needs JavaScript to load current supplier previews. The comparison guide below still explains what to check before booking.\tDer Assistent benötigt JavaScript, um aktuelle Angebotsvorschauen zu laden. Der Vergleichsratgeber darunter erklärt weiterhin, was du vor der Buchung prüfen solltest.
Load supplier previews to see from prices. Date-specific availability has not been checked.\tLade Angebotsvorschauen, um Ab-Preise zu sehen. Die Verfügbarkeit für bestimmte Termine wurde nicht geprüft.
Affiliate disclosure: KATE may earn a commission if you book through a Viator link.\tPartnerhinweis: KATE kann eine Provision erhalten, wenn du über einen Viator-Link buchst.
COMPARE THE DETAILS, NOT A HEADLINE PRICE\tVERGLEICHE DIE DETAILS UND DEN GESAMTPREIS
Two ways to frame the same trip.\tZwei Anreisearten für dieselbe Reise.
Compare complete trip details. Supplier from prices are not a quote for your dates or group.\tVergleiche die vollständigen Reisedetails. Ab-Preise sind kein verbindlicher Preis für deine Termine oder Gruppe.
Road\tStraßenanreise
Fly-in\tFluganreise
Ask for a complete overland plan from Nairobi, with each transfer and inclusion spelled out.\tBitte um den vollständigen Reiseplan ab Nairobi, mit allen Transfers und enthaltenen Leistungen.
Confirm with the provider\tBeim Anbieter bestätigen
Exact departure and return arrangements\tGenaue Abfahrts- und Rückkehrregelung
Vehicle and transfer details\tFahrzeug- und Transferdetails
What is included—and any additional fees\tEnthaltene Leistungen und Zusatzgebühren
Total price, currency and traveler basis\tGesamtpreis, Währung und Preisbasis
Date-specific availability and cancellation terms\tVerfügbarkeit für deine Termine und Stornobedingungen
No verified road offer yet\tNoch kein geprüftes Angebot für Straßenanreise
Provider, itinerary, inclusions, total price, date validity, availability and booking URL require verification.\tAnbieter, Reiseverlauf, Leistungen, Gesamtpreis, Gültigkeit, Verfügbarkeit und Buchungslink müssen bestätigt werden.
Ask for the full flight-and-transfer chain, not just the flight segment.\tBitte um die vollständige Flug- und Transferkette, einschließlich aller Anschlussfahrten.
Flight operator, schedule and baggage rules\tFluggesellschaft, Flugplan und Gepäckregeln
Airstrip and ground-transfer arrangements\tLandepiste und Bodentransfers
No verified fly-in offer yet\tNoch kein geprüftes Angebot für Fluganreise
Treat from prices as a starting point\tNutze Ab-Preise als Ausgangspunkt
Supplier catalog previews may show a from price. That price does not confirm date-specific availability, inclusions or the total for your party. Check the details on Viator before booking.\tKatalogvorschauen können einen Ab-Preis zeigen. Dieser bestätigt weder Verfügbarkeit für bestimmte Termine noch Leistungen oder Gesamtpreis für deine Gruppe. Prüfe die Details vor der Buchung auf Viator.
Before deciding:\tVor der Entscheidung:
confirm dates, total party price, currency, inclusions, fees, timings and cancellation terms directly with the provider.\tBestätige Termine, Gesamtpreis für die Gruppe, Währung, Leistungen, Gebühren, Zeiten und Stornobedingungen direkt beim Anbieter.
NEXT STEP\tNÄCHSTER SCHRITT
Frame it around your trip.\tPlane nach deinen Reisewünschen.
Add your group size, budget target and comfort preference. Nairobi–Mara plans of 2–4 days can also load supplier product previews.\tErgänze Gruppengröße, Budgetziel und Komfortwunsch. Für Nairobi–Mara-Pläne von 2–4 Tagen können auch Angebotsvorschauen geladen werden.
Open the trip planner\tReiseplaner öffnen
KENYA · TRIP PLANNER\tKENIA · REISEPLANER
Plan the trip around\tPlane deine Reise nach
 your\tdeinen
priorities.\tPrioritäten.
These inputs shape a practical planning outline. Nairobi–Mara trips of 2–4 days can also load supplier product previews. Your dates and total party price must be checked on Viator.\tDeine Angaben bilden einen praktischen Planungsentwurf. Für Nairobi–Mara-Reisen von 2–4 Tagen können auch Angebotsvorschauen geladen werden. Termine und Gesamtpreis für die Gruppe müssen auf Viator geprüft werden.
Trip basics\tReisegrundlagen
Set the frame. Add only what you already know.\tLege den Rahmen fest. Trage nur ein, was du schon weißt.
Starting point\tStartort
Use the city or place you plan to start from.\tNenne die Stadt oder den Ort, an dem du starten möchtest.
Main focus\tReiseziel
Still deciding\tNoch unentschieden
The comparison page covers Nairobi–Mara only.\tDie Vergleichsseite behandelt nur Nairobi–Mara.
days\tTage
Planning window; not a supplier itinerary.\tPlanungszeitraum, kein Reiseplan des Anbieters.
Travelers\tReisende
Total party size only—no names needed.\tNur die Gesamtzahl der Reisenden; keine Namen erforderlich.
Budget per person\tBudget pro Person
optional\toptional
A planning input only. It is not matched against offers or used as a price quote.\tNur eine Planungsangabe. Sie wird nicht mit Angeboten abgeglichen und ist kein verbindlicher Preis.
Travel date\tReisedatum
Not checked for availability.\tVerfügbarkeit nicht geprüft.
Date flexibility\tFlexibilität beim Datum
Not sure\tNoch nicht sicher
Dates are fixed\tFeste Termine
Dates are flexible\tFlexible Termine
Planning context only.\tNur für die Planung.
Select any that apply.\tWähle alles aus, was auf dich zutrifft.
Wildlife\tTierwelt
Culture\tKultur
Photography\tFotografie
Unhurried pace\tEntspanntes Tempo
Comfort preference\tKomfortwunsch
Balanced\tAusgewogen
Keep it simple\tEinfach und praktisch
More comfort\tMehr Komfort
A preference to carry into provider questions, not an offer filter.\tEin Wunsch für deine Fragen an den Anbieter, kein Angebotsfilter.
Build my planning outline\tMeinen Planungsentwurf erstellen
No contact details requested. Your planning outline and essential usage events are stored in KATE’s Supabase database. No contact details are requested.\tKeine Kontaktdaten erforderlich. Dein Planungsentwurf und grundlegende Nutzungsereignisse werden in der Supabase-Datenbank von KATE gespeichert.
WHAT HAPPENS NEXT\tSO GEHT ES WEITER
A plan to verify, not a promise.\tEin Entwurf zum Prüfen, keine Zusage.
Turn your inputs into a day-by-day planning outline.\tErstelle aus deinen Angaben einen Planungsentwurf für jeden Tag.
Call out what to confirm for your group and preferences.\tErfahre, was du für deine Gruppe und Wünsche bestätigen solltest.
Use the Mara comparison to frame road vs fly-in.\tNutze den Mara-Vergleich für Straßen- und Fluganreise.
Supplier previews and your dates\tAngebotsvorschauen und deine Termine
Eligible Nairobi–Mara plans may show supplier from prices. They are not matched to your budget or comfort preference. Date-specific availability and the price for your party are checked on Viator.\tGeeignete Nairobi–Mara-Pläne können Ab-Preise anzeigen. Sie werden nicht auf dein Budget oder deinen Komfortwunsch abgestimmt. Verfügbarkeit für deine Termine und Preis für deine Gruppe werden auf Viator geprüft.
KENYA SAFARI PLANNING\tSAFARI-PLANUNG FÜR KENIA
Maasai Mara safari guides\tSafari-Ratgeber für die Maasai Mara
Make a useful shortlist before comparing supplier listings. These guides explain the questions to ask about your route, group and total price.\tErstelle eine sinnvolle Vorauswahl, bevor du Anbieterangebote vergleichst. Diese Ratgeber erklären die wichtigsten Fragen zu Route, Gruppe und Gesamtpreis.
3-Day Maasai Mara Safari from Nairobi: Planning Checklist\t3-tägige Maasai-Mara-Safari ab Nairobi: Planungscheckliste
Plan a 3-day Maasai Mara safari from Nairobi. Compare the itinerary, road or fly-in transfers, inclusions, party price and booking terms before you decide.\tPlane eine 3-tägige Maasai-Mara-Safari ab Nairobi. Vergleiche Reiseverlauf, Straßen- oder Flugtransfers, Leistungen, Gruppenpreis und Buchungsbedingungen.
Private vs Shared Maasai Mara Safari: What to Compare\tPrivate oder gemeinsame Maasai-Mara-Safari: Was vergleichen?
Compare private and shared Maasai Mara safaris. Check vehicle exclusivity, group size, flexibility, inclusions and the total for your party before booking.\tVergleiche private und gemeinsame Maasai-Mara-Safaris. Prüfe Fahrzeugexklusivität, Gruppengröße, Flexibilität, Leistungen und Gesamtpreis vor der Buchung.
Free Safari Booking Checklist & Two-Quote Comparison | KATE\tKostenlose Safari-Buchungscheckliste und Angebotsvergleich | KATE
Download a free safari booking checklist, compare two complete quotes and copy a provider inquiry. Check inclusions, party totals and terms before booking.\tLade die kostenlose Safari-Buchungscheckliste herunter, vergleiche zwei vollständige Angebote und kopiere eine Anfrage. Prüfe Leistungen, Gruppenpreis und Bedingungen.
Ready to compare options?\tBereit zum Angebotsvergleich?
Check dates, inclusions and total party price on Viator.\tPrüfe Termine, enthaltene Leistungen und Gesamtpreis für die Gruppe auf Viator.
See three-day safari options ↗\t3-tägige Safari-Angebote ansehen ↗
NAIROBI TO MAASAI MARA · PLANNING GUIDE\tNAIROBI–MAASAI MARA · PLANUNGSRATGEBER
How to choose a\tSo wählst du eine
3-day Maasai Mara safari\t3-tägige Maasai-Mara-Safari
from Nairobi.\tab Nairobi.
Explore 3-day safari options\t3-tägige Safari-Angebote entdecken
Outline my trip\tMeine Reise skizzieren
A useful safari comparison starts with the full journey: where it begins, what each day contains, what is included and what your party will pay. Use this checklist before treating a tour title or from price as a complete offer.\tEin sinnvoller Safari-Vergleich betrachtet die ganze Reise: Startort, Tagesabläufe, Leistungen und Preis für deine Gruppe. Prüfe diese Checkliste, bevor du einen Tourtitel oder Ab-Preis als vollständiges Angebot verstehst.
Start with your departure and return requirements\tBeginne mit deinen Anforderungen an Abfahrt und Rückkehr
Write down your starting point in Nairobi, your preferred departure date, party size and any fixed commitment after the safari. If you have onward travel, ask the provider to explain the return arrangements before you commit to that connection.\tNotiere Startort in Nairobi, Wunschtermin, Gruppengröße und feste Termine nach der Safari. Lass dir bei einer Anschlussreise zuerst die Rückkehrregelung erklären, bevor du den Anschluss buchst.
Confirm the pickup location, the stated departure time, the return location and which transfers are included. Do not assume that “from Nairobi” means collection from your accommodation or that an airport transfer is part of the price. Ask what happens if your arrival or pickup plans change.\tBestätige Abholort, Abfahrtszeit, Rückkehrort und enthaltene Transfers. „Ab Nairobi“ bedeutet nicht automatisch Abholung an deiner Unterkunft oder einen Flughafentransfer. Frage, was bei Änderungen deiner Ankunft oder Abholung gilt.
Read the three days as a schedule\tLies die drei Tage als vollständigen Ablauf
Ask for a day-by-day itinerary that identifies transfers, planned activities and overnight arrangements. A title tells you the marketed duration; the schedule tells you how the trip fits your priorities. Use the following questions as a review framework, not as a promised itinerary.\tBitte um einen Tagesplan mit Transfers, Aktivitäten und Übernachtungen. Der Titel nennt die angebotene Dauer; der Ablauf zeigt, ob die Reise zu deinen Wünschen passt. Die folgenden Fragen sind eine Prüfhilfe und kein zugesagter Reiseverlauf.
Departure day:\tAbreisetag:
Where do you meet, which transfer is arranged and what activities are scheduled after arrival?\tWo trefft ihr euch, welcher Transfer ist vorgesehen und welche Aktivitäten folgen nach der Ankunft?
Middle day:\tMittlerer Tag:
Which activities are included, what is optional and what accommodation or meal arrangements apply?\tWelche Aktivitäten sind enthalten oder optional? Welche Unterkunft und Verpflegung sind vorgesehen?
Return day:\tRückreisetag:
What happens before departure and how does the provider arrange the return to Nairobi?\tWas ist vor der Abfahrt geplant und wie organisiert der Anbieter die Rückkehr nach Nairobi?
Ask the provider to resolve unclear timings and explain any changes that depend on conditions or operating arrangements. KATE’s planner creates an outline to discuss; it is not a supplier itinerary.\tLass unklare Zeiten und mögliche betriebliche oder situationsbedingte Änderungen erklären. Der KATE-Reiseplaner erstellt einen Entwurf zum Besprechen, keinen Reiseplan des Anbieters.
Compare road and fly-in journeys from end to end\tVergleiche Straßen- und Flugreisen von Anfang bis Ende
For an overland option, check the vehicle, pickup and return arrangements, and each transfer in the itinerary. If comfort or photography matters to you, ask specific questions about the vehicle and how activities are organized instead of inferring those details from the product title.\tPrüfe bei Straßenanreise Fahrzeug, Abholung, Rückkehr und alle Transfers. Sind Komfort oder Fotografie wichtig, frage konkret nach Fahrzeug und Organisation der Aktivitäten. Der Produkttitel allein bestätigt diese Details nicht.
For a fly-in option, check the flight operator, schedule, baggage rules, arrival airstrip and ground transfers. Establish whether the quoted option includes the flights and onward transfers you need. A flight segment alone does not describe the full safari.\tPrüfe bei Fluganreise Fluggesellschaft, Flugplan, Gepäckregeln, Landepiste und Bodentransfers. Kläre, ob das Angebot alle benötigten Flüge und Anschlussfahrten enthält. Ein einzelner Flug beschreibt nicht die ganze Safari.
Use the\tNutze die
road versus fly-in planning checklist\tCheckliste für Straßen- und Fluganreise
to compare these details. Product previews are not independently classified into transport categories by KATE.\tzum Vergleich dieser Details. KATE ordnet Angebotsvorschauen nicht unabhängig einer Transportkategorie zu.
Request a complete price for your party\tBitte um den vollständigen Preis für deine Gruppe
Give the provider your actual dates and traveler details, then ask for one total in a stated currency. Check whether a displayed amount is per person, per booking or another basis, and which option it represents. A supplier from price is a starting point for investigation, not your final quote.\tNenne dem Anbieter Termine und Angaben zu den Reisenden. Bitte um einen Gesamtpreis mit Währung. Prüfe, ob der Betrag pro Person, pro Buchung oder auf anderer Basis gilt und welche Option gemeint ist. Ein Ab-Preis ist kein verbindlicher Endpreis.
Identify the accommodation and room arrangements in the selected option.\tBestätige Unterkunft und Zimmeraufteilung der gewählten Option.
Confirm the meal plan, activities and transfers that are included.\tBestätige enthaltene Mahlzeiten, Aktivitäten und Transfers.
Ask which entry charges, taxes and other fees are covered or excluded.\tFrage, welche Eintrittsgebühren, Steuern und anderen Gebühren enthalten oder ausgeschlossen sind.
List any optional extras and the charges that could be payable separately.\tListe optionale Extras und separat zahlbare Kosten auf.
Check cancellation terms, payment requirements and the booking confirmation process.\tPrüfe Stornobedingungen, Zahlungsanforderungen und Buchungsbestätigung.
Keep the scope of the quotes consistent. Comparing a basic option with a different accommodation or transport package can make a headline price misleading even when both products use the same trip length. If group arrangements matter, use the\tVergleiche Angebote mit gleichem Leistungsumfang. Unterschiedliche Unterkünfte oder Transportpakete können den Preisvergleich trotz gleicher Reisedauer verzerren. Nutze bei Fragen zur Gruppe die
private versus shared safari checklist\tCheckliste für private und gemeinsame Safaris
to clarify what is exclusive to your party.\tund kläre, was deiner Gruppe exklusiv zur Verfügung steht.
A message you can send to the provider\tEine Nachricht für deine Anfrage beim Anbieter
We are considering a three-day Maasai Mara safari from Nairobi for our party on our preferred dates. Please confirm the pickup and return details, full daily itinerary, vehicle or flight arrangements, accommodation and room setup, meals and activities. Which entry charges and other fees are included or excluded? Please provide the full party total, currency, availability for our dates and cancellation terms for the specific option we would book.\tWir interessieren uns für eine dreitägige Maasai-Mara-Safari ab Nairobi zu unseren Wunschterminen. Bitte bestätigen Sie Abholung und Rückkehr, Tagesablauf, Fahrzeug oder Flüge, Unterkunft und Zimmeraufteilung, Mahlzeiten und Aktivitäten. Welche Eintrittsgebühren und anderen Kosten sind enthalten oder ausgeschlossen? Bitte nennen Sie Gesamtpreis, Währung, Verfügbarkeit und Stornobedingungen für die konkrete Buchungsoption.
Add your own priorities, such as comfort or photography, as questions. Ask how the provider would meet them; a preference entered in the KATE planner does not establish an included service.\tErgänze Fragen zu deinen Wünschen, etwa Komfort oder Fotografie. Frage, wie der Anbieter sie erfüllen kann. Ein Wunsch im KATE-Reiseplaner bestätigt keine enthaltene Leistung.
Frequently asked questions\tHäufige Fragen
Is a 3-day Maasai Mara safari from Nairobi enough?\tReichen drei Tage für eine Maasai-Mara-Safari ab Nairobi?
Judge the actual itinerary rather than the number of days in the title. Ask how much of each day is allocated to transfers, activities and overnight stays. Check the departure and return arrangements against your wider trip. A three-day label alone does not confirm the time you will spend on safari.\tEntscheidend ist der tatsächliche Ablauf. Frage nach der Zeit für Transfers, Aktivitäten und Übernachtungen. Prüfe Abfahrt und Rückkehr im Zusammenhang mit deiner gesamten Reise. „Drei Tage“ bestätigt allein keine bestimmte Zeit auf Safari.
What should a 3-day safari quote include?\tWas sollte ein Angebot für eine dreitägige Safari enthalten?
Request the full itinerary, departure and return details, transport arrangements, accommodation, meal plan, activities, fees, exclusions and cancellation terms. These are items to verify, not inclusions that every safari provides. Ask for the total in a stated currency for your exact party and dates.\tBitte um Reiseverlauf, Abfahrt und Rückkehr, Transport, Unterkunft, Mahlzeiten, Aktivitäten, Gebühren, Ausschlüsse und Stornobedingungen. Diese Punkte sind zu prüfen und nicht bei jeder Safari enthalten. Verlange den Gesamtpreis mit Währung für deine Gruppe und Termine.
Are park fees included in a Maasai Mara safari price?\tSind Parkgebühren im Safari-Preis enthalten?
Do not assume they are included. Ask the provider which entry charges and other fees are covered, what remains payable separately and how those charges affect your total party price. KATE does not publish an independently verified park-fee schedule.\tGehe nicht automatisch davon aus. Frage, welche Eintritts- und anderen Gebühren enthalten sind, was separat zu zahlen ist und wie sich das auf den Gesamtpreis auswirkt. KATE veröffentlicht keine unabhängig geprüfte Parkgebührenliste.
Should I choose road or fly-in travel from Nairobi?\tSoll ich ab Nairobi per Straße oder Flug anreisen?
Compare the complete journey for your dates. For a road option, confirm the vehicle and transfer arrangements. For a fly-in option, confirm the operator, flight schedule, baggage rules, airstrip and onward transfers. Evaluate the full itinerary and total price; KATE does not declare a universal winner.\tVergleiche die komplette Reise für deine Termine. Bei Straßenanreise prüfst du Fahrzeug und Transfers, bei Fluganreise Betreiber, Flugplan, Gepäckregeln, Landepiste und Anschlusstransfers. Bewerte Ablauf und Gesamtpreis; KATE nennt keinen pauschalen Gewinner.
Does a supplier from price confirm my safari booking cost?\tBestätigt ein Ab-Preis meine Buchungskosten?
No. A catalog from price does not confirm availability for your dates or the cost for your party. Check your date, traveler details, selected option, inclusions and final total on Viator before booking.\tNein. Ein Katalog-Ab-Preis bestätigt weder Verfügbarkeit noch Kosten für deine Gruppe. Prüfe vor der Buchung Datum, Reisende, gewählte Option, Leistungen und Endpreis auf Viator.
Check the final details on Viator\tPrüfe die endgültigen Details auf Viator
Supplier product previews may show from prices. KATE does not confirm date-specific availability, the total for your party or every itinerary detail. Review the selected option and full terms on Viator before booking.\tAngebotsvorschauen können Ab-Preise zeigen. KATE bestätigt weder Verfügbarkeit für bestimmte Termine noch Gruppenpreis oder alle Reisedetails. Prüfe die gewählte Option und vollständigen Bedingungen vor der Buchung auf Viator.
Affiliate disclosure:\tPartnerhinweis:
KATE may earn a commission if you book through a Viator link.\tKATE kann eine Provision erhalten, wenn du über einen Viator-Link buchst.
Explore the options for your trip.\tEntdecke die Optionen für deine Reise.
Use supplier previews as a starting point, then confirm the details with the provider.\tNutze Angebotsvorschauen als Ausgangspunkt und bestätige die Details beim Anbieter.
MAASAI MARA · SAFARI COMPARISON GUIDE\tMAASAI MARA · SAFARI-VERGLEICH
Private or shared Maasai Mara safari:\tPrivate oder gemeinsame Maasai-Mara-Safari:
what to compare.\tWas du vergleichen solltest.
Choose by the confirmed arrangements for your party. Establish what is exclusive, what is shared and what the full quote covers before using either label to judge value or comfort.\tEntscheide anhand bestätigter Leistungen für deine Gruppe. Kläre, was exklusiv oder gemeinsam genutzt wird und was das Angebot enthält, bevor du Preis und Komfort bewertest.
Explore safari options\tSafari-Angebote entdecken
Ask what “private” or “shared” applies to\tFrage, worauf sich „privat“ oder „gemeinsam“ bezieht
Break the trip into services: the transfer from Nairobi, the safari vehicle, guide arrangements, activities, accommodation and return transfer. Ask which of these are exclusive to your party and which involve other travelers. Do not extend a claim about one service to the whole trip.\tBetrachte die Reiseleistung einzeln: Transfer ab Nairobi, Safari-Fahrzeug, Guide, Aktivitäten, Unterkunft und Rücktransfer. Frage, was exklusiv für deine Gruppe ist und was andere Reisende nutzen. Eine Aussage zu einer Leistung gilt nicht automatisch für die ganze Reise.
For a private option, request a written explanation of what your party has exclusive use of. For a shared option, ask how participants are grouped and whether the group or vehicle can change during the itinerary. Neither label substitutes for a complete description of the selected booking option.\tBitte bei einer privaten Option um eine schriftliche Beschreibung der exklusiven Nutzung. Frage bei einer gemeinsamen Option nach Gruppenzusammensetzung und möglichen Gruppen- oder Fahrzeugwechseln. Beide Begriffe ersetzen keine vollständige Leistungsbeschreibung.
Compare the vehicle and group arrangements\tVergleiche Fahrzeug und Gruppenregelung
Discuss the maximum number of passengers, seating arrangements and guide provision. If your priority is photography, comfort or an unhurried pace, turn that into concrete questions: what vehicle is planned, how are stops organized and what choices can your party make?\tFrage nach maximaler Passagierzahl, Sitzplätzen und Guide. Formuliere Wünsche wie Fotografie, Komfort oder Ruhe als konkrete Fragen: Welches Fahrzeug ist geplant, wie sind Stopps organisiert und was kann deine Gruppe mitentscheiden?
For a shared departure, ask whether there is a minimum participant requirement and what happens if it is not met. Confirm any changes, cancellation or refund arrangements in the actual booking terms. For a private departure, verify that the vehicle or guide exclusivity you need is part of the option being quoted.\tKläre bei einer gemeinsamen Abfahrt die Mindestteilnehmerzahl und das Vorgehen, wenn sie nicht erreicht wird. Prüfe Änderungen, Storno und Erstattung in den Buchungsbedingungen. Bei einer privaten Abfahrt muss die benötigte Exklusivität ausdrücklich im Angebot stehen.
These are questions to put to the provider. KATE does not verify vehicle occupancy, exclusive use or the private/shared classification of every product preview.\tDiese Fragen sind beim Anbieter zu klären. KATE bestätigt nicht Fahrzeugbelegung, Exklusivität oder die Einordnung jeder Angebotsvorschau als privat oder gemeinsam.
Check flexibility rather than assuming it\tLass Flexibilität bestätigen
If you want control over departure times, activities or stops, ask which changes the provider permits. Request the standard schedule first, then clarify the choices available and any additional cost. An exclusive vehicle does not by itself establish that accommodation, transfers or activities can be changed.\tFrage nach erlaubten Änderungen bei Zeiten, Aktivitäten oder Stopps. Lass dir erst den Standardablauf nennen, dann Wahlmöglichkeiten und Zusatzkosten. Ein exklusives Fahrzeug bestätigt allein keine Änderbarkeit anderer Leistungen.
For a shared itinerary, ask which timings are fixed and how the provider handles different preferences within the group. Keep your onward travel and pickup requirements in view when assessing either arrangement. Confirm the exact return plan before relying on it for another travel commitment.\tKläre bei gemeinsamen Reisen feste Zeiten und den Umgang mit unterschiedlichen Wünschen. Berücksichtige Abholung und Anschlussreise. Bestätige den Rückkehrplan, bevor du ihn für weitere Reisetermine zugrunde legst.
Compare total party prices on the same basis\tVergleiche Gruppenpreise auf gleicher Basis
Request quotes for the same dates and traveler details. Compare the full totals and the included services before drawing a conclusion from a per-person amount or catalog from price. A lower headline figure may describe a different room setup, transfer arrangement or package scope.\tVerlange Angebote für dieselben Termine und Reisenden. Vergleiche Gesamtpreise und Leistungen statt allein Pro-Person- oder Ab-Preise. Ein niedriger Betrag kann andere Zimmer, Transfers oder Leistungen betreffen.
Travel:\tAnreise:
Which departure, return and other transfers are covered?\tWelche Hin-, Rück- und weiteren Transfers sind enthalten?
Stay:\tUnterkunft:
Which accommodation, room arrangements and meal plan are quoted?\tWelche Unterkunft, Zimmeraufteilung und Verpflegung sind angeboten?
Activities:\tAktivitäten:
Which activities are included, optional or payable separately?\tWelche Aktivitäten sind enthalten, optional oder separat zahlbar?
Fees:\tGebühren:
Which entry charges and other costs remain outside the total?\tWelche Eintrittsgebühren und weiteren Kosten sind nicht im Gesamtpreis enthalten?
Terms:\tBedingungen:
What cancellation, payment and confirmation rules apply to that option?\tWelche Storno-, Zahlungs- und Bestätigungsregeln gelten für diese Option?
Do not assume a shared safari always costs less or that a private safari always offers better value. The useful comparison is the price and scope offered for your actual party.\tEine gemeinsame Safari ist nicht immer günstiger und eine private nicht immer die bessere Wahl. Vergleiche Preis und Leistungsumfang für deine tatsächliche Gruppe.
Keep transport mode separate from group type\tTrenne Anreiseart und Gruppenart
Private versus shared describes an arrangement to verify. Road versus fly-in describes a different part of the journey. Check both rather than interpreting one label as evidence of the other.\tPrivat oder gemeinsam beschreibt eine zu prüfende Nutzung. Straße oder Flug betrifft die Anreise. Kläre beides getrennt; aus einem Begriff folgt der andere nicht.
For road travel, confirm the vehicle and the complete transfer chain. For fly-in travel, confirm the flight operator, schedule, baggage rules, airstrip and onward transfers. Ask whether the selected option covers the full journey you need. Use KATE’s\tPrüfe bei Straßenanreise Fahrzeug und alle Transfers. Bei Fluganreise bestätige Betreiber, Flugplan, Gepäck, Landepiste und Anschlusstransfers. Frage, ob die Option die ganze benötigte Reise abdeckt. Nutze die
road and fly-in checklist\tCheckliste für Straßen- und Fluganreise
for the questions to resolve.\tals Hilfe für deine Fragen.
Make your decision from the provider’s answers\tEntscheide anhand der Antworten des Anbieters
Write down the requirements that matter to your party: exclusive use if needed, an acceptable group arrangement, your comfort preferences, a clear itinerary and a complete price. Compare the answers to those requirements. If an important detail remains unclear, resolve it before paying instead of relying on the tour title.\tNotiere deine Anforderungen: benötigte Exklusivität, passende Gruppe, Komfort, klarer Ablauf und vollständiger Preis. Vergleiche die Antworten damit. Kläre wichtige offene Details vor der Zahlung; der Tourtitel allein genügt nicht.
For a focused Nairobi departure, the\tFür eine Reise ab Nairobi hilft der
three-day Maasai Mara planning guide\tRatgeber für dreitägige Maasai-Mara-Reisen
helps you review departure, overnight and return arrangements. The\tbei Abfahrt, Übernachtung und Rückkehr. Der
trip planner\tReiseplaner
can organize your preferences into an outline to discuss with a provider.\tordnet deine Wünsche in einem Entwurf für das Gespräch mit dem Anbieter.
Please confirm which vehicles, guide services, transfers and activities would be exclusive to our party and which would be shared. What are the maximum group size and seating arrangements? Are there participant requirements or permitted itinerary changes? Please quote the complete price for our dates and party, including a clear list of exclusions and the applicable cancellation terms.\tBitte bestätigen Sie, welche Fahrzeuge, Guides, Transfers und Aktivitäten exklusiv für unsere Gruppe oder gemeinsam genutzt werden. Wie groß ist die Gruppe maximal und wie sind die Sitzplätze geregelt? Gibt es eine Mindestteilnehmerzahl oder erlaubte Ablaufänderungen? Bitte nennen Sie den Gesamtpreis für unsere Termine und Gruppe, Ausschlüsse und Stornobedingungen.
What is the difference between a private and a shared Maasai Mara safari?\tWas unterscheidet eine private von einer gemeinsamen Safari?
Use the terms as questions to investigate. A private label may refer to a vehicle, guide, transfer or a particular activity; it does not establish that every part of the trip is exclusive. For a shared trip, confirm which services are shared and with how many travelers. Ask the provider to spell out the arrangement.\tKläre die Begriffe beim Anbieter. „Privat“ kann Fahrzeug, Guide, Transfer oder einzelne Aktivitäten betreffen und gilt nicht automatisch für die ganze Reise. Frage bei gemeinsamer Nutzung, welche Leistungen mit wie vielen Reisenden geteilt werden.
Is a shared safari always cheaper than a private safari?\tIst eine gemeinsame Safari immer günstiger?
No comparison is reliable without quotes for the same dates and party, with the same scope and exclusions. Compare the full party totals rather than unmatched per-person headline prices. Accommodation, transfers, included services and additional charges can differ between the quotes.\tEin verlässlicher Vergleich braucht dieselben Termine, Reisenden, Leistungen und Ausschlüsse. Vergleiche vollständige Gruppenpreise. Unterkunft, Transfers, enthaltene Leistungen und Zusatzkosten können unterschiedlich sein.
Does a private safari guarantee a flexible itinerary?\tGarantiert eine private Safari einen flexiblen Ablauf?
No. Confirm the actual schedule, what changes the provider allows and any additional costs. An exclusive vehicle does not by itself establish flexibility in accommodation, transfers, departure times or activities.\tNein. Bestätige Ablauf, erlaubte Änderungen und Zusatzkosten. Ein exklusives Fahrzeug garantiert allein keine Flexibilität bei Unterkunft, Transfers, Abfahrtszeiten oder Aktivitäten.
What should I ask about group size on a shared safari?\tWas sollte ich zur Gruppengröße fragen?
Ask for the maximum group and vehicle occupancy, seating arrangements, guide arrangements and whether the booking requires a minimum number of participants. Confirm what happens if that minimum is not reached and which cancellation or refund terms apply.\tFrage nach maximaler Gruppen- und Fahrzeugbelegung, Sitzplätzen, Guide und Mindestteilnehmerzahl. Kläre, was bei zu wenigen Teilnehmern passiert und welche Storno- oder Erstattungsregeln gelten.
Can I book a private or shared safari directly with KATE?\tKann ich eine Safari direkt bei KATE buchen?
KATE provides planning guidance and supplier product previews. It does not verify the private or shared classification of every preview, or take your booking. Open the product on Viator, confirm the specific arrangement and review dates, traveler details, final price and terms before booking.\tKATE bietet Planungshilfen und Angebotsvorschauen, prüft nicht jede Einordnung als privat oder gemeinsam und nimmt keine Buchung an. Öffne das Produkt auf Viator und prüfe Organisation, Termine, Reisende, Endpreis und Bedingungen.
Verify the selected option\tPrüfe die gewählte Option
KATE’s supplier previews do not establish whether a trip is private or shared. Confirm the arrangement, dates, total party price and terms on Viator before booking.\tKATE-Vorschauen bestätigen nicht, ob eine Reise privat oder gemeinsam ist. Bestätige Organisation, Termine, Gruppenpreis und Bedingungen vor der Buchung auf Viator.
Find options to investigate.\tFinde Optionen zum Vergleichen.
Explore 3-day Nairobi–Mara product previews, then ask the questions that matter to your party.\tEntdecke 3-tägige Nairobi–Mara-Vorschauen und stelle danach die wichtigen Fragen für deine Gruppe.
See safari options\tSafari-Angebote ansehen
FREE SAFARI PLANNING RESOURCE\tKOSTENLOSE SAFARI-PLANUNGSHILFE
Two safari quotes.\tZwei Safari-Angebote.
One clear comparison.\tEin klarer Vergleich.
Use this checklist to find out what each quote actually covers. Save the worksheet, copy the inquiry and compare the answers before you book. No signup required.\tMit dieser Checkliste prüfst du die tatsächlichen Leistungen jedes Angebots. Speichere das Arbeitsblatt, kopiere die Anfrage und vergleiche die Antworten vor der Buchung. Ohne Anmeldung.
Download the free checklist\tKostenlose Checkliste herunterladen
Copy the provider inquiry\tAnbieteranfrage kopieren
STEP 1 · CHECK\tSCHRITT 1 · PRÜFEN
Ask the same questions of both providers.\tStelle beiden Anbietern dieselben Fragen.
Start with the same dates, party and room arrangement. Tick each item when you have a clear answer for both quotes. Write\tVergleiche dieselben Termine, Reisenden und Zimmer. Hake einen Punkt ab, sobald beide Anbieter klar geantwortet haben. Schreibe
“not confirmed”\t„nicht bestätigt“
beside unanswered questions; an empty field does not mean included.\tneben offene Fragen. Ein leeres Feld bedeutet nicht, dass eine Leistung enthalten ist.
Match the request.\tGleiche Anfrage.
Use the same dates, party, room setup, pickup and return requirements for both quotes.\tNutze für beide Angebote dieselben Termine, Reisenden, Zimmer-, Abhol- und Rückkehrwünsche.
Name the exact option.\tGenaue Option.
Save the product link, selected option, provider name and quote date. A tour title alone is not the option you are booking.\tSpeichere Produktlink, gewählte Option, Anbieter und Angebotsdatum. Ein Tourtitel allein beschreibt nicht deine Buchungsoption.
Read the whole itinerary.\tVollständiger Reiseverlauf.
Confirm the overnight stays, activities and transfers day by day. Check the return plan against any onward commitment.\tBestätige Übernachtungen, Aktivitäten und Transfers für jeden Tag. Prüfe die Rückkehr im Hinblick auf Anschlussreisen.
Clarify private or shared.\tPrivat oder gemeinsam.
Record what is exclusive to your party, what is shared, maximum vehicle occupancy and any participant minimum.\tNotiere exklusive und gemeinsame Leistungen, maximale Fahrzeugbelegung und Mindestteilnehmerzahl.
Identify accommodation and meals.\tUnterkunft und Verpflegung.
Request the accommodation names, room and bed arrangements, number of nights and meal plan.\tFrage nach Unterkunftsnamen, Zimmern und Betten, Übernachtungen und Mahlzeiten.
List every extra.\tAlle Zusatzkosten.
Ask which entry charges, taxes, transfers and other mandatory charges sit outside the quoted total. Keep optional extras separate.\tKläre, welche Eintrittsgebühren, Steuern, Transfers und Pflichtkosten zusätzlich anfallen. Trenne optionale Extras davon.
Check the price basis.\tPreisbasis.
Is the amount per person, per booking or for the whole party? Request the full party total and currency for your exact option.\tGilt der Betrag pro Person, Buchung oder Gruppe? Bitte um Gruppen-Gesamtpreis und Währung für deine genaue Option.
Check the terms.\tBuchungsbedingungen.
Read deposit, balance, cancellation and change terms for the selected option. Record the quote expiry and confirmation process.\tLies Anzahlungs-, Restzahlungs-, Storno- und Änderungsregeln der Option. Notiere Angebotsgültigkeit und Bestätigungsablauf.
Your ticks stay on this page only; they are not saved after a reload. Download the plain-text worksheet to keep your notes, or use your browser’s print command to print this page.\tHäkchen bleiben nur auf dieser Seite und gehen beim Neuladen verloren. Lade das Text-Arbeitsblatt herunter, um Notizen zu speichern, oder drucke die Seite über deinen Browser.
Put Quote A and Quote B side by side.\tVergleiche Angebot A und B nebeneinander.
This is a blank comparison worksheet, not a supplier quote. Fill it in on paper or in the download. Keep optional extras separate from mandatory charges so you can see what you must pay.\tDies ist ein leeres Vergleichsblatt, kein Anbieterangebot. Fülle es auf Papier oder in der heruntergeladenen Datei aus. Trenne optionale Extras von Pflichtkosten.
Two quotes for the same trip requirements\tZwei Angebote für dieselben Reisewünsche
What to compare\tVergleichspunkt
Quote A\tAngebot A
Quote B\tAngebot B
Provider / product link / selected option\tAnbieter / Produktlink / gewählte Option
Write your answer\tAntwort eintragen
Quote date and expiry\tAngebotsdatum und Gültigkeit
Travel dates / party / room setup\tReisetermine / Gruppe / Zimmer
Pickup and return locations / arrangements\tAbhol- und Rückkehrort / Organisation
Day-by-day itinerary / nights\tTagesablauf / Übernachtungen
Road or flight / all transfers\tStraße oder Flug / alle Transfers
Private or shared services / occupancy\tPrivate oder gemeinsame Leistungen / Belegung
Accommodation / rooms / meals\tUnterkunft / Zimmer / Mahlzeiten
Included activities / optional extras\tEnthaltene Aktivitäten / optionale Extras
Entry charges / taxes / mandatory extras\tEintrittsgebühren / Steuern / Pflichtkosten
Quoted amount / currency / price basis\tAngebotsbetrag / Währung / Preisbasis
Full party total with mandatory extras\tGruppen-Gesamtpreis einschließlich Pflichtkosten
Availability confirmed for these dates?\tVerfügbarkeit für diese Termine bestätigt?
Deposit / balance / cancellation / changes\tAnzahlung / Restzahlung / Storno / Änderungen
Participant minimum and fallback\tMindestteilnehmerzahl und Alternative
Operator / booking confirmation / trip contact\tVeranstalter / Bestätigung / Kontakt während der Reise
Unanswered questions to resolve\tNoch zu klärende Fragen
Compare full party totals in the same currency. Ask for a matched-currency quote where possible. If you convert a currency yourself, note the rate and date and treat the result as an estimate. Do not compare a per-person headline amount with a full party total.\tVergleiche Gruppen-Gesamtpreise in derselben Währung. Bitte möglichst um Angebote in gleicher Währung. Bei eigener Umrechnung notiere Kurs und Datum; das Ergebnis ist eine Schätzung. Vergleiche keinen Pro-Person-Preis mit einem Gruppenpreis.
Before payment:\tVor der Zahlung:
confirm your essential requirements in writing, understand the total and mandatory extras, read the exact option’s terms and save the final quote or booking details. Resolve missing essential answers with the provider.\tBestätige wichtige Anforderungen schriftlich, kläre Gesamt- und Pflichtkosten, lies die Bedingungen der genauen Option und speichere Angebot oder Buchungsdetails. Kläre wichtige offene Antworten beim Anbieter.
Copy one complete inquiry.\tKopiere eine vollständige Anfrage.
Replace the brackets with your own requirements, then send it through the provider’s contact channel. KATE does not send this message or collect its contents.\tErsetze die Klammern durch deine Angaben und sende die Anfrage über den Kontaktkanal des Anbieters. KATE verschickt die Nachricht nicht und erfasst ihren Inhalt nicht.
Provider inquiry template\tVorlage für die Anbieteranfrage
Copy inquiry\tAnfrage kopieren
If copying is unavailable, select the text above and use your device’s copy command. You can also find the inquiry in the\tFalls Kopieren nicht verfügbar ist, markiere den Text und nutze die Kopierfunktion deines Geräts. Die Anfrage steht auch im
free checklist download\tkostenlosen Checklisten-Download
Need help deciding what to ask?\tBrauchst du Hilfe bei deinen Fragen?
Plan a three-day Maasai Mara safari from Nairobi\tPlane eine dreitägige Maasai-Mara-Safari ab Nairobi
: departure, daily itinerary and return requirements.\t: Abfahrt, Tagesablauf und Rückkehr.
Compare private and shared safaris\tVergleiche private und gemeinsame Safaris
: exclusivity, occupancy and group arrangements.\t: Exklusivität, Belegung und Gruppenregelung.
Share this checklist with your travel companions using the page address. It is free to download, print and share.\tTeile diese Checkliste über die Seitenadresse mit deinen Mitreisenden. Download, Ausdruck und Weitergabe sind kostenlos.
Check the selected option before booking\tPrüfe die gewählte Option vor der Buchung
This checklist does not verify any supplier’s inclusions, availability, price or terms. A displayed from price does not confirm the cost for your party. Review dates, traveler details, the exact option and the final total on Viator.\tDiese Checkliste bestätigt keine Leistungen, Verfügbarkeit, Preise oder Bedingungen eines Anbieters. Ein Ab-Preis bestätigt nicht die Kosten für deine Gruppe. Prüfe Termine, Reisende, genaue Option und Endpreis auf Viator.
KATE may earn a commission if you book through a Viator link. KATE provides planning guidance and product previews; your booking is made with the supplier through Viator.\tKATE kann eine Provision erhalten, wenn du über einen Viator-Link buchst. KATE bietet Planungshilfen und Angebotsvorschauen; du buchst beim Anbieter über Viator.
STEP 2 · COMPARE OFFERS\tSCHRITT 2 · ANGEBOTE VERGLEICHEN
Explore options with your checklist ready.\tVergleiche Angebote mit deiner Checkliste.
Start with 3-day Nairobi–Mara supplier previews, then confirm the details for your actual dates and party.\tBeginne mit 3-tägigen Nairobi–Mara-Vorschauen und bestätige die Details für deine Termine und Gruppe.
Compare 3-day safari options\t3-tägige Safari-Angebote vergleichen
KATE home\tKATE-Startseite
Main navigation\tHauptnavigation
Budget currency\tBudgetwährung
Add a planning target\tBudgetziel eingeben
Illustrative Maasai Mara safari landscape\tSymbolbild einer Safari-Landschaft in der Maasai Mara
Illustrative savannah landscape created for this preview; not evidence of an itinerary or availability.\tSymbolbild einer Savannenlandschaft; kein Nachweis eines Reiseverlaufs oder verfügbarer Angebote.
Quote A: write your answer\tAngebot A: Antwort eintragen
Quote B: write your answer\tAngebot B: Antwort eintragen
Explore three-day Maasai Mara safari options from Nairobi. Compare supplier from prices and confirm your travel dates and full party price on Viator.\tEntdecke dreitägige Maasai-Mara-Safaris ab Nairobi. Vergleiche Ab-Preise und bestätige Termine und Gruppen-Gesamtpreis auf Viator.
Browse three-day Maasai Mara safari previews from Nairobi, compare road and fly-in planning, and check itinerary details and final prices on Viator.\tEntdecke dreitägige Maasai-Mara-Vorschauen ab Nairobi. Vergleiche Straßen- und Fluganreise und prüfe Reisedetails und Endpreise auf Viator.
Build a Kenya trip planning outline with your dates, group size and preferences. Confirm supplier availability and total prices separately.\tErstelle einen Kenia-Reiseentwurf mit Terminen, Gruppengröße und Wünschen. Bestätige Verfügbarkeit und Gesamtpreise separat.
Practical Maasai Mara safari planning guides: three-day trips from Nairobi, private versus shared tours, and checks to make before booking.\tPraktische Maasai-Mara-Ratgeber: dreitägige Reisen ab Nairobi, private oder gemeinsame Touren und Prüfpunkte vor der Buchung.
3-day Maasai Mara safaris from Nairobi\t3-tägige Maasai-Mara-Safaris ab Nairobi
3-day Maasai Mara Safari Options from Nairobi\t3-tägige Maasai-Mara-Safari-Angebote ab Nairobi
Kenya Trip Planner\tKenia-Reiseplaner
Maasai Mara safari planning guides\tPlanungsratgeber für Maasai-Mara-Safaris
'''
TEXT_DE = {line.split('\t', 1)[0].strip(): line.split('\t', 1)[1] for line in _PAIRS.splitlines() if '\t' in line}
TEXT_DE['Choose language'] = 'Sprache wählen'
TEXT_DE.update({
    'SAFARI PLANNING': 'SAFARI-PLANUNG',
    'Safari options': 'Safari-Angebote',
    'Compare 2–4-day Maasai Mara safaris.': 'Vergleiche Maasai-Mara-Safaris für 2–4 Tage.',
    'Compare safari options': 'Safari-Angebote vergleichen',
    'Choose your safari length, compare supplier from prices and use the checklist to confirm the details before booking.': 'Wähle deine Safari-Dauer, vergleiche Ab-Preise und bestätige die Details vor der Buchung mithilfe der Checkliste.',
    'Bookings handled by Viator.': 'Buchungen erfolgen über Viator.',
    '2–4-day Maasai Mara safaris from Nairobi': 'Maasai-Mara-Safaris für 2–4 Tage ab Nairobi',
    'Compare two-, three- and four-day Maasai Mara safaris from Nairobi. Explore supplier from prices and optional Nairobi activities, then confirm dates and total party prices on Viator.': 'Vergleiche Maasai-Mara-Safaris für zwei, drei oder vier Tage ab Nairobi. Entdecke Ab-Preise und optionale Nairobi-Aktivitäten. Bestätige Termine und Gruppen-Gesamtpreise auf Viator.',
    'Nairobi activities before or after your safari': 'Nairobi-Aktivitäten vor oder nach deiner Safari',
    'Add a Nairobi experience': 'Ergänze ein Erlebnis in Nairobi',
    'Explore short Nairobi activities': 'Kurze Aktivitäten in Nairobi entdecken',
    'Browse short supplier-listed activities in Nairobi. Check your dates, pickup location, transfer times and total party price on Viator before adding one to your trip.': 'Entdecke kurze Anbieter-Aktivitäten in Nairobi. Prüfe Termine, Abholort, Transferzeiten und Gruppen-Gesamtpreis auf Viator, bevor du eine Aktivität ergänzt.',
    'Show Nairobi activities': 'Nairobi-Aktivitäten anzeigen',
    'These are separate bookings, not included in a safari. Confirm timing, pickup and any extra fees with each supplier.': 'Diese Aktivitäten werden separat gebucht und sind nicht in einer Safari enthalten. Bestätige Zeiten, Abholung und Zusatzgebühren bei jedem Anbieter.',
    'Nairobi extras': 'Nairobi-Ergänzungen',
    'Short activities, separate bookings': 'Kurze Aktivitäten, separate Buchungen',
})

INQUIRY_DE = '''Betreff: Schriftliches Safari-Angebot für [Termine] — [Gruppengröße]

Guten Tag,

wir vergleichen eine Maasai-Mara-Safari ab [Abholort] am [Abreisedatum],
mit Rückkehr nach [Rückkehrort] bis [Datum / benötigte Uhrzeit].

Unsere Gruppe: [Erwachsene], [Kinder und ihr Alter zum Reisezeitpunkt].
Zimmeraufteilung: [benötigte Zimmer / Betten].
Unsere Prioritäten: [Komfort, Fotografie, exklusives Fahrzeug oder andere Wünsche].
Das gewünschte Produkt / die Option: [Produktlink und genaue Optionsbezeichnung].

Bitte erstellen Sie ein schriftliches Angebot für diese Gruppe und Termine mit:

1. Verfügbarkeit und Tagesablauf einschließlich Abholung und Rückkehr.
2. Straßen- oder Fluganreise, allen Transfers, Fahrzeug, Sitzplätzen und Guide.
   Bei Flügen: Betreiber, Flugplan, Gepäckregeln, Landepiste und Anschlusstransfers.
3. Privaten oder gemeinsam genutzten Fahrzeugen, Transfers, Guides und Aktivitäten;
   maximaler Belegung und etwaiger Mindestteilnehmerzahl.
4. Unterkunftsnamen, Zimmern und Betten, Übernachtungen und Mahlzeiten.
5. Enthaltenen Aktivitäten und optionalen Aktivitäten mit separaten Kosten.
6. Eintrittsgebühren, Steuern und weiteren Kosten: enthaltene und ausgeschlossene
   Beträge, wer Zusatzkosten zahlt und wann / wie sie zu zahlen sind.
7. Einem Gruppen-Gesamtpreis mit Währung, Preisbasis, allen Pflichtkosten und
   Angebotsgültigkeit. Bitte optionale Extras getrennt ausweisen.
8. Anzahlungs- und Restzahlungsregeln, Storno- und Änderungsbedingungen sowie
   Vorgehen bei nicht erreichter Mindestteilnehmerzahl einer gemeinsamen Abfahrt.
9. Buchungsbestätigung, Reiseveranstalter und Kontakt während der Reise.

Bitte kennzeichnen Sie unbestätigte Punkte, statt enthaltene Leistungen anzunehmen.
Bitte nennen Sie es ausdrücklich, wenn die Rückkehrzeit nur eine Schätzung ist.

Vielen Dank,
[Name]
'''
from scripts.booking_resource import INQUIRY_TEMPLATE, CHECKS, COMPARE_FIELDS  # noqa: E402
TEXT_DE[' '.join(INQUIRY_TEMPLATE.split())] = INQUIRY_DE


def translate_text(text: str, language: str = 'de') -> str:
    if language != 'de' or not text.strip():
        return text
    key = ' '.join(text.split())
    translated = TEXT_DE.get(key)
    if translated is None and key.endswith(' · KATE'):
        base = key[:-7]
        translated = TEXT_DE.get(base, base) + ' · KATE'
    if translated is None:
        return text  # Honest, readable English fallback for new unmapped content.
    leading = text[:len(text) - len(text.lstrip())]
    trailing = text[len(text.rstrip()):]
    return leading + translated + trailing


def english_path(path: str) -> str:
    if path == '/de' or path == '/de/':
        return '/'
    if path.startswith('/de/'):
        return path[3:]
    return path if path.startswith('/') else '/' + path


def localized_path(path: str, language: str = 'de') -> str:
    parsed = urlsplit(path)
    base = english_path(parsed.path)
    canonical = base if base == '/' or base.endswith('/') else base + '/'
    downloadable = base == '/resources/safari-booking-checklist.txt'
    if canonical not in PUBLIC_PATHS and not downloadable:
        return path
    result = ('/de' + base if base != '/' else '/de/') if language == 'de' else base
    if not downloadable and not result.endswith('/'):
        result += '/'
    return urlunsplit(('', '', result, parsed.query, parsed.fragment))


def language_selector(path: str, language: str = 'en') -> str:
    en = localized_path(english_path(path), 'en')
    de = localized_path(en, 'de')
    links = ''.join(f'<a href="{escape(href, quote=True)}" lang="{locale}" hreflang="{locale}" data-kate-language="{locale}"' + (' aria-current="true"' if locale == language else '') + f'>{label}</a>' for locale, href, label in [('en', en, 'EN'), ('de', de, 'DE')])
    return '<div class="language-selector" aria-label="' + ('Sprache wählen' if language == 'de' else 'Choose language') + '">' + links + '</div>'


def _url(href: str, language: str) -> str:
    p = urlsplit(href)
    if p.scheme or p.netloc:
        if p.scheme not in {'http', 'https'} or p.netloc != urlsplit(SITE_URL).netloc:
            return href
        return SITE_URL + localized_path(urlunsplit(('', '', p.path, p.query, p.fragment)), language)
    if not href.startswith('/') or href.startswith('//'):
        return href
    return localized_path(href, language)


def _schema(value: object, language: str) -> object:
    if isinstance(value, list):
        return [_schema(v, language) for v in value]
    if isinstance(value, dict):
        return {k: (translate_text(v, language) if k in {'name', 'description', 'headline', 'text'} and isinstance(v, str) else _url(v, language) if k in {'url', '@id'} and isinstance(v, str) else _schema(v, language)) for k, v in value.items()}
    return value


class _Localizer(HTMLParser):
    def __init__(self, path: str, language: str):
        super().__init__(convert_charrefs=True)
        self.path, self.language = english_path(path), language
        self.parts: list[str] = []
        self.raw_tag: str | None = None
        self.json_script = False
        self.raw_data: list[str] = []

    def handle_decl(self, decl):
        self.parts.append('<!' + decl + '>')

    def handle_comment(self, data):
        self.parts.append('<!--' + data + '-->')

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == 'link' and attributes.get('rel') == 'alternate' and attributes.get('hreflang') in {'en', 'de', 'x-default'}:
            return
        if tag == 'meta' and attributes.get('property') == 'og:locale':
            return
        translated = []
        for key, value in attrs:
            if tag == 'html' and key == 'lang':
                value = self.language
            elif key in {'alt', 'title', 'aria-label', 'placeholder'} and value is not None:
                value = translate_text(value, self.language)
            elif key == 'href' and value is not None and 'data-kate-language' not in attributes:
                value = (SITE_URL + localized_path(self.path, self.language)) if tag == 'link' and attributes.get('rel') == 'canonical' else _url(value, self.language)
            elif key == 'aria-current' and 'data-kate-language' in attributes:
                if attributes['data-kate-language'] != self.language:
                    continue
                value = 'true'
            elif tag == 'meta' and key == 'content' and value is not None:
                if attributes.get('name') == 'description' or attributes.get('property') in {'og:title', 'og:description', 'og:image:alt'}:
                    value = translate_text(value, self.language)
                elif attributes.get('property') == 'og:url':
                    value = SITE_URL + localized_path(self.path, self.language)
            translated.append((key, value))
        if 'data-kate-language' in attributes and attributes['data-kate-language'] == self.language and not any(key == 'aria-current' for key, value in translated):
            translated.append(('aria-current', 'true'))
        encoded = ''.join(' ' + key + ('' if value is None else '="' + escape(value, quote=True) + '"') for key, value in translated)
        self.parts.append('<' + tag + encoded + '>')
        if tag in {'script', 'style'}:
            self.raw_tag = tag
            self.json_script = tag == 'script' and attributes.get('type') == 'application/ld+json'
            self.raw_data = []

    def handle_startendtag(self, tag, attrs):
        before = len(self.parts)
        self.handle_starttag(tag, attrs)
        if len(self.parts) > before:
            self.parts[-1] = self.parts[-1][:-1] + ' />'

    def handle_endtag(self, tag):
        if tag == self.raw_tag:
            source = ''.join(self.raw_data)
            if self.json_script:
                try:
                    source = json.dumps(_schema(json.loads(source), self.language), ensure_ascii=False).replace('<', '\\u003c')
                except (ValueError, TypeError):
                    pass
            self.parts.append(source)
            self.raw_tag = None
            self.json_script = False
        if tag == 'head':
            for locale in ('en', 'de', 'x-default'):
                target = 'en' if locale == 'x-default' else locale
                self.parts.append(f'<link rel="alternate" hreflang="{locale}" href="{SITE_URL}{localized_path(self.path, target)}">')
            self.parts.append(f'<meta property="og:locale" content="{"de_DE" if self.language == "de" else "en_US"}">')
        self.parts.append('</' + tag + '>')

    def handle_data(self, data):
        if self.raw_tag:
            self.raw_data.append(data)
        else:
            self.parts.append(escape(translate_text(data, self.language), quote=False))


def localize_html(html_string: str, path: str, language: str = 'de') -> str:
    """Localize complete rendered HTML. Supported pages must already have canonical tags.

    Call for both English and German variants to add reciprocal hreflang links.
    Script code, assets, API actions, IDs and submitted form values stay intact.
    """
    if language not in {'en', 'de'}:
        raise ValueError('Supported languages: en, de')
    parser = _Localizer(path, language)
    parser.feed(html_string)
    parser.close()
    return ''.join(parser.parts)


CHECKLIST_DE = '''KATE — SAFARI-BUCHUNGSCHECKLISTE UND ANGEBOTSVERGLEICH
Kostenlos herunterladen, drucken und teilen.
Quelle: https://kate-kenya-trip-planner.netlify.app/de/resources/safari-booking-checklist/

SCHRITT 1 — ZWEI SCHRIFTLICHE ANGEBOTE PRÜFEN
Notiere „nicht bestätigt“ bei offenen Fragen. Ein leeres Feld bedeutet nicht enthalten.

''' + '\n'.join('[ ] ' + translate_text(title + '.') + ' ' + translate_text(detail) for title, detail in CHECKS) + '''

VERGLEICHSBLATT FÜR ZWEI ANGEBOTE
Nutze dieselben Termine, Reisenden und Zimmer. Vergleiche Gruppen-Gesamtpreise
in gleicher Währung. Bitte möglichst um Angebote in gleicher Währung. Bei eigener
Umrechnung notiere Kurs und Datum; das Ergebnis ist nur eine Schätzung.

''' + '\n\n'.join(translate_text(field) + '\n  Angebot A: ____________________________\n  Angebot B: ____________________________' for field in COMPARE_FIELDS) + '''

VOR DER ZAHLUNG
[ ] Wichtige Anforderungen sind schriftlich bestätigt.
[ ] Gesamtpreis, Pflichtkosten und Zahlungsbedingungen sind klar.
[ ] Bedingungen der genauen Buchungsoption sind gelesen.
[ ] Angebot / Buchungsdetails und Anbieter-Kontakt sind gespeichert.
Kläre wichtige offene Fragen beim Anbieter vor der Zahlung.

ANBIETERANFRAGE — KLAMMERN VOR DEM SENDEN ERSETZEN
''' + INQUIRY_DE + '''
SCHRITT 2 — ANGEBOTE VERGLEICHEN
https://kate-kenya-trip-planner.netlify.app/de/mara/#safari-options
Diese Vorschauen zeigen 3-tägige Nairobi–Mara-Optionen. Ab-Preise bestätigen
weder Verfügbarkeit für deine Termine noch Gruppen-Gesamtpreis. Prüfe die genaue
Option und Bedingungen vor der Buchung auf Viator.

WEITERE PLANUNGSHILFEN
https://kate-kenya-trip-planner.netlify.app/de/guides/3-day-masai-mara-safari-from-nairobi/
https://kate-kenya-trip-planner.netlify.app/de/guides/private-vs-shared-masai-mara-safari/

PARTNERHINWEIS
KATE kann eine Provision erhalten, wenn du über einen Viator-Link buchst. KATE
bietet Planungshilfen und Angebotsvorschauen; du buchst beim Anbieter über Viator.
Diese Checkliste bestätigt keine Leistungen, Verfügbarkeit, Preise oder Bedingungen.
Keine Kontaktdaten erforderlich.
'''
