import { createClient } from "npm:@supabase/supabase-js@2";
import { createHandler } from "./handler.js";

const env = (name) => Deno.env.get(name);
function dbFactory() {
  const url = env("SUPABASE_URL");
  const serviceKey = env("SUPABASE_SERVICE_ROLE_KEY");
  if (!url || !serviceKey) throw new Error("server_configuration_missing");
  return createClient(url, serviceKey, { auth: { persistSession: false, autoRefreshToken: false } });
}

Deno.serve(createHandler({ dbFactory, env }));
