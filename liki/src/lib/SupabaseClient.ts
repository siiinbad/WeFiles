import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    'Missing Supabase env vars. Copy .env.example to .env.local and fill in VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY.'
  );
}

// Only the anon key is ever used here. The service_role key must never
// appear in frontend code — real authorization is enforced by RLS policies
// on the Supabase side, not by anything in this client.
export const supabase = createClient(supabaseUrl, supabaseAnonKey);