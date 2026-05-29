'use client';

import { useFormState, useFormStatus } from 'react-dom';
import { submitContactMessage, type ContactFormResult } from './actions';

const INITIAL_STATE: ContactFormResult | null = null;

export function ContactForm() {
  const [state, formAction] = useFormState(submitContactMessage, INITIAL_STATE);

  // 送信成功時
  if (state?.ok) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
        <p className="text-2xl mb-3">✓</p>
        <p className="text-green-800 font-bold mb-2">送信完了しました</p>
        <p className="text-sm text-gray-700">
          お問い合わせいただきありがとうございました。
          <br />
          メールアドレスをご記入いただいた場合のみ、内容に応じて返信させていただきます。
        </p>
      </div>
    );
  }

  return (
    <form action={formAction} className="space-y-4">
      {state?.error && (
        <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-800">
          {state.error}
        </div>
      )}

      <Field label="お名前" name="name" hint="任意。匿名OK" />
      <Field
        label="メールアドレス"
        name="email"
        type="email"
        hint="任意。返信が必要な場合のみご記入ください"
      />
      <Field label="件名" name="subject" hint="任意" />
      <Field
        label="本文"
        name="body"
        textarea
        required
        hint="ご意見・ご要望・データ訂正など (5〜2000文字)"
      />

      {/* honeypot: 人間には見えない隠しフィールド。bot は埋めがちなのでspam判定 */}
      <div className="hidden" aria-hidden="true">
        <label>
          ホームページ (記入しないでください)
          <input type="text" name="website" tabIndex={-1} autoComplete="off" />
        </label>
      </div>

      <SubmitButton />
    </form>
  );
}

/** 送信中状態を表示するボタン (useFormStatusはformの子で使う必要があるため別コンポーネント) */
function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="w-full md:w-auto bg-brand-600 hover:bg-brand-700 disabled:bg-gray-400 text-white font-bold px-8 py-3 rounded-lg transition"
    >
      {pending ? '送信中...' : '送信する'}
    </button>
  );
}

function Field({
  label,
  name,
  type = 'text',
  textarea,
  required,
  hint,
}: {
  label: string;
  name: string;
  type?: string;
  textarea?: boolean;
  required?: boolean;
  hint?: string;
}) {
  return (
    <div>
      <label
        htmlFor={name}
        className="block text-sm font-medium text-gray-800 mb-1"
      >
        {label}
        {required && <span className="text-red-600 ml-1">*</span>}
      </label>
      {textarea ? (
        <textarea
          id={name}
          name={name}
          required={required}
          rows={6}
          maxLength={2000}
          className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-sm"
        />
      ) : (
        <input
          id={name}
          name={name}
          type={type}
          required={required}
          className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-sm"
        />
      )}
      {hint && <p className="text-xs text-gray-500 mt-1">{hint}</p>}
    </div>
  );
}
