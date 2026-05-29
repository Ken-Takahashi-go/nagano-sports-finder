// =====================================================================
// Supabase クライアント
// =====================================================================
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    'Supabase URL/anon key が未設定です。web/.env.local を確認してください。',
  );
}

// 公開キー使用のクライアント (RLS有効。読み取り専用想定)
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: false, // Phase1ではログイン不要
  },
});
