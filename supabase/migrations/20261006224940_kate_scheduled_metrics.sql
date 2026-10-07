-- One inexpensive hourly database routine; no supplier requests or invented outcomes.
CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA pg_catalog;

CREATE OR REPLACE FUNCTION public.kate_collect_metrics()
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_payload jsonb; v_now timestamptz := now();
BEGIN
  v_payload := jsonb_build_object(
    'collected_at', v_now,
    'events', COALESCE((SELECT jsonb_object_agg(t.event_type, t.n)
      FROM (SELECT event_type, count(*) AS n FROM public.events
        WHERE occurred_at >= v_now - interval '24 hours' GROUP BY event_type) t), '{}'::jsonb),
    'clicks_by_product', COALESCE((SELECT jsonb_object_agg(t.product_id, t.n)
      FROM (SELECT product_id, count(*) AS n FROM public.affiliate_clicks
        WHERE clicked_at >= v_now - interval '24 hours' GROUP BY product_id) t), '{}'::jsonb),
    'total_conversions', (SELECT count(*) FROM public.conversions),
    'recorded_revenue_by_currency', COALESCE((SELECT jsonb_object_agg(t.currency, t.amount)
      FROM (SELECT currency, sum(amount) AS amount FROM public.revenue GROUP BY currency) t), '{}'::jsonb),
    'scope', '24-hour activity; lifetime evidence-backed commercial outcomes. No profit or costs inferred.'
  );
  INSERT INTO public.business_memory(key, value, updated_at)
    VALUES ('scheduled_metrics_latest', v_payload::text, v_now)
    ON CONFLICT (key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at;
  INSERT INTO public.agent_runs(id, task, status, started_at, finished_at, outcome_note)
    VALUES ('metrics:' || to_char(v_now AT TIME ZONE 'UTC', 'YYYY-MM-DD-HH24'),
      'scheduled_metrics', 'completed', v_now, v_now,
      'Stored actual activity and supplier-report outcomes. Deterministic database routine; no AI inference.')
    ON CONFLICT (id) DO NOTHING;
  RETURN v_payload;
END;
$$;
REVOKE ALL ON FUNCTION public.kate_collect_metrics() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.kate_collect_metrics() TO service_role;
SELECT cron.schedule('kate-hourly-metrics', '10 * * * *', 'SELECT public.kate_collect_metrics();');
