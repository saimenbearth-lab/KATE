-- Basic-access supplier previews are catalogue results, not date/party availability confirmations.
-- Service-role-only functions keep refresh limits and tracked handoffs atomic.
CREATE OR REPLACE FUNCTION public.claim_viator_search()
RETURNS boolean LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_claimed boolean;
BEGIN
  INSERT INTO public.business_memory(key, value, updated_at)
  VALUES ('viator_search_lease', 'Rate limit for on-demand supplier previews', now())
  ON CONFLICT (key) DO UPDATE SET updated_at = now()
    WHERE public.business_memory.updated_at < now() - interval '5 seconds'
  RETURNING true INTO v_claimed;
  RETURN COALESCE(v_claimed, false);
END;
$$;
REVOKE ALL ON FUNCTION public.claim_viator_search() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_viator_search() TO service_role;

CREATE OR REPLACE FUNCTION public.record_catalogue_click(
  p_product_id text, p_clicked_at timestamptz, p_page text
) RETURNS text LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_url text; v_click_id bigint;
BEGIN
  IF p_page NOT IN ('/mara', '/planner') OR p_page IS NULL THEN
    RAISE EXCEPTION 'invalid_page' USING ERRCODE = 'P0001';
  END IF;
  SELECT affiliate_url INTO v_url FROM public.products
  WHERE product_id = p_product_id AND provider = 'Viator' AND affiliate_state = 'approved'
    AND snapshot_context->>'catalogue_status' = 'ACTIVE'
    AND snapshot_context->>'catalogue_source' = 'viator_products_search'
    AND snapshot_context->>'approved_pid' = 'P00323912'
    AND source_last_checked <= now()
    AND source_last_checked > now() - interval '15 minutes'
  FOR SHARE;
  -- Reject malformed destinations before writing either the click or event.
  IF v_url IS NULL OR length(v_url) > 4096
    OR v_url !~ '^https://(www[.])?viator[.]com/tours/[^[:space:]#@]+$'
    OR v_url !~ '[?&]pid=P00323912(&|$)'
    OR regexp_count(v_url, '[?&]pid=') <> 1 THEN
    RAISE EXCEPTION 'no_verified_affiliate' USING ERRCODE = 'P0001';
  END IF;
  INSERT INTO public.affiliate_clicks(product_id, destination_url, clicked_at)
    VALUES (p_product_id, v_url, p_clicked_at) RETURNING id INTO v_click_id;
  INSERT INTO public.events(event_type, source, page, intent, product_id, position, occurred_at)
    VALUES ('affiliate_click', 'product_card', p_page, 'mara_3d_decision', p_product_id, v_click_id::text, p_clicked_at);
  RETURN v_url;
END;
$$;
REVOKE ALL ON FUNCTION public.record_catalogue_click(text, timestamptz, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.record_catalogue_click(text, timestamptz, text) TO service_role;
