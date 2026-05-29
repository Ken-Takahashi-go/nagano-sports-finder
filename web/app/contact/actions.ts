'use server';

import { supabase } from '@/lib/supabase';

export type ContactFormResult = {
  ok: boolean;
  error?: string;
};

/** お問い合わせフォーム送信 Server Action */
export async function submitContactMessage(
  prev: ContactFormResult | null,
  formData: FormData,
): Promise<ContactFormResult> {
  const name = (formData.get('name') as string | null)?.trim() || null;
  const email = (formData.get('email') as string | null)?.trim() || null;
  const subject = (formData.get('subject') as string | null)?.trim() || null;
  const body = (formData.get('body') as string | null)?.trim() || '';
  const honeypot = (formData.get('website') as string | null) || ''; // 隠しフィールド

  // バリデーション
  if (body.length < 5) {
    return { ok: false, error: '本文は5文字以上で入力してください' };
  }
  if (body.length > 2000) {
    return { ok: false, error: '本文は2000文字以内でお願いします' };
  }
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return { ok: false, error: 'メールアドレスの形式が正しくありません' };
  }

  // スパムbot対策: honeypotに値が入ってたら無視 (見せかけ成功でユーザー混乱回避)
  if (honeypot) {
    return { ok: true };
  }

  // DBへ保存
  const { error } = await supabase.from('contact_messages').insert({
    name,
    email,
    subject,
    body,
    honeypot: honeypot || null,
  });

  if (error) {
    console.error('contact submit error:', error);
    return { ok: false, error: '送信に失敗しました。しばらく時間をおいてお試しください。' };
  }

  return { ok: true };
}
