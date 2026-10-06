-- KATE production hardening plus the exact user-authorized source-returned click-outs.
-- The migration never claims price, date availability, cancellation terms, commission, bookings, or revenue.

-- Cover the destination FK for joins/deletes without changing the existing relationship.
CREATE INDEX IF NOT EXISTS travel_intents_destination_id_idx
  ON public.travel_intents(destination_id)
  WHERE destination_id IS NOT NULL;

-- The project already has a postgres-owned event trigger that calls this function.
-- Keep that owner-controlled trigger intact; do not expose the SECURITY DEFINER RPC to browser roles.
REVOKE ALL ON FUNCTION public.rls_auto_enable() FROM PUBLIC, anon, authenticated;

-- Supplied by KATE HQ from clickOffToPDP via the user-authorized Viator flow.
-- source_last_checked is the HQ record timestamp (2026-10-06 05:48:53 +02:00), not an availability check.
INSERT INTO public.products (
  product_id, comparison_id, search_partition, provider, product_name, destination_text,
  category, from_price, currency, price_basis_confirmed, date_availability_confirmed,
  availability_state, affiliate_url, affiliate_state, cancellation_note, confidence_note,
  snapshot_context, source_last_checked
) VALUES
(
  '427094P4', 'nairobi-mara-3day', 'road', 'Viator',
  '3 Days 2 Nights Masai Mara Shared Transport Safari', 'Nairobi / Maasai Mara, Kenya',
  'safari', NULL, NULL, false, false,
  'unverified',
  'https://www.viator.com/tours/Nairobi/3-Days-2-Nights-Masai-Mara-Shared-Transport-Safari/d5280-427094P4?pid=P00323912&mcid=42383&medium=link&medium_version=selector',
  'approved', NULL,
  'Source-returned click-out only; date availability, price basis, cancellation, commission, booking, and revenue are not verified.',
  jsonb_build_object(
    'source', 'KATE HQ / Product',
    'source_method', 'clickOffToPDP',
    'source_returned', true,
    'user_authorized_viator_flow', true,
    'record_state', 'discovery_needs_data',
    'approved_pid', 'P00323912',
    'tracking', jsonb_build_object('mcid', '42383', 'medium', 'link', 'medium_version', 'selector'),
    'checked_at', '2026-10-06T05:48:53+02:00',
    'affiliate_state_note', 'Approved PID/click-out only; commission terms are not verified.',
    'data_status', jsonb_build_object('date_availability', 'not_verified', 'price_basis', 'not_verified', 'cancellation', 'not_verified', 'commission', 'not_verified', 'booking', 'not_verified', 'revenue', 'not_verified')
  ),
  '2026-10-06T03:48:53Z'
),
(
  '107758P7', 'nairobi-mara-3day', 'fly', 'Viator',
  '3 Days Maasai Mara Safari', 'Nairobi / Maasai Mara, Kenya',
  'safari', NULL, NULL, false, false,
  'unverified',
  'https://www.viator.com/tours/Nairobi/3-Days-masai-mara-safari/d5280-107758P7?pid=P00323912&mcid=42383&medium=link&medium_version=selector',
  'approved', NULL,
  'Source-returned click-out only; date availability, price basis, cancellation, commission, booking, and revenue are not verified.',
  jsonb_build_object(
    'source', 'KATE HQ / Product',
    'source_method', 'clickOffToPDP',
    'source_returned', true,
    'user_authorized_viator_flow', true,
    'record_state', 'discovery_needs_data',
    'approved_pid', 'P00323912',
    'tracking', jsonb_build_object('mcid', '42383', 'medium', 'link', 'medium_version', 'selector'),
    'checked_at', '2026-10-06T05:48:53+02:00',
    'affiliate_state_note', 'Approved PID/click-out only; commission terms are not verified.',
    'data_status', jsonb_build_object('date_availability', 'not_verified', 'price_basis', 'not_verified', 'cancellation', 'not_verified', 'commission', 'not_verified', 'booking', 'not_verified', 'revenue', 'not_verified')
  ),
  '2026-10-06T03:48:53Z'
),
(
  '260078P150', 'nairobi-mara-3day', 'fly', 'Viator',
  '3 Days Masai Mara Flying Safari and Hot Air Balloon Ride Package', 'Nairobi / Maasai Mara, Kenya',
  'safari', NULL, NULL, false, false,
  'unverified',
  'https://www.viator.com/tours/Nairobi/3-Days-Masai-Mara-Flying-Safari-and-Hot-Air-Balloon-Ride-Package/d5280-260078P150?pid=P00323912&mcid=42383&medium=link&medium_version=selector',
  'approved', NULL,
  'Source-returned click-out only; date availability, price basis, cancellation, commission, booking, and revenue are not verified.',
  jsonb_build_object(
    'source', 'KATE HQ / Product',
    'source_method', 'clickOffToPDP',
    'source_returned', true,
    'user_authorized_viator_flow', true,
    'record_state', 'discovery_needs_data',
    'approved_pid', 'P00323912',
    'tracking', jsonb_build_object('mcid', '42383', 'medium', 'link', 'medium_version', 'selector'),
    'checked_at', '2026-10-06T05:48:53+02:00',
    'affiliate_state_note', 'Approved PID/click-out only; commission terms are not verified.',
    'data_status', jsonb_build_object('date_availability', 'not_verified', 'price_basis', 'not_verified', 'cancellation', 'not_verified', 'commission', 'not_verified', 'booking', 'not_verified', 'revenue', 'not_verified')
  ),
  '2026-10-06T03:48:53Z'
)
ON CONFLICT (product_id) DO NOTHING;
