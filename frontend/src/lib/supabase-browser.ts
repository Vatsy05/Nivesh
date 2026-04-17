import { createClient } from "@supabase/supabase-js";

/**
 * Browser-side Supabase client using the anon (public) key.
 * Safe to use in client components.
 */
export function createBrowserClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
  return createClient(url, key);
}
