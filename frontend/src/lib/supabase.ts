import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://qctdtzwvthrtjmgfkdgs.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFjdGR0end2dGhydGptZ2ZrZGdzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTIxMTY5NzQsImV4cCI6MjEwNzY5Mjk3NH0.Qg-LNHoi6rk-8wBG2-YpgY2udgQDvMQs1XEtyt68HDQ';

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});
