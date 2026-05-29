import type { Metadata } from 'next';
import { ContactForm } from './ContactForm';

export const metadata: Metadata = {
  title: 'お問い合わせ',
  description: '長野県公共施設ナビへのご意見・ご要望・データ訂正依頼などを受け付けています。',
  robots: { index: false, follow: false }, // 問い合わせページはnoindex
};

export default function ContactPage() {
  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <h1 className="text-2xl font-bold mb-3">お問い合わせ</h1>
      <p className="text-sm text-gray-700 mb-6 leading-relaxed">
        長野県公共施設ナビへのご意見・ご要望・データ訂正依頼などを受け付けています。
        匿名のフィードバックでもOKです（メール返信が必要な場合のみメールアドレスをご記入ください）。
      </p>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6 text-sm">
        <p className="font-medium text-amber-900 mb-1">⚠️ 施設の予約・空き状況に関するお問い合わせ</p>
        <p className="text-amber-800">
          本サイトでは予約や空き確認の代行はできません。
          実際の予約・キャンセル等は各施設の公式予約サイト（まちかぎリモート等）で直接お手続きください。
        </p>
      </div>

      <ContactForm />

      <div className="mt-10 pt-6 border-t border-gray-200 text-xs text-gray-500 space-y-1">
        <p>※ 投稿いただいた内容は、サービス改善の目的で利用させていただきます。</p>
        <p>※ メールアドレスをご記入いただいた場合のみ、内容に応じて返信させていただくことがあります。</p>
        <p>※ 返信を保証するものではありませんのでご了承ください。</p>
      </div>
    </div>
  );
}
