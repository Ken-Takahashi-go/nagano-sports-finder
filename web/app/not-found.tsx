import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="container mx-auto px-4 py-16 max-w-md text-center">
      <h1 className="text-3xl font-bold mb-4">404 - 見つかりません</h1>
      <p className="text-gray-600 mb-6">
        お探しの施設・ページは存在しないか、移動した可能性があります。
      </p>
      <Link
        href="/"
        className="inline-block bg-brand-600 hover:bg-brand-700 text-white px-6 py-3 rounded font-medium"
      >
        TOPに戻る
      </Link>
    </div>
  );
}
