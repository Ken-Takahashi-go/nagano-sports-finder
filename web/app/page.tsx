import type { Metadata } from 'next';
import Link from 'next/link';
import { FacilityCard } from '@/components/FacilityCard';
import { SearchBox } from '@/components/SearchBox';
import {
  getNightTennisFacilities,
  getStats,
  getTonightAvailableTennisFacilities,
} from '@/lib/queries';

// 静的生成を回避して常に最新データを取得
export const revalidate = 60;

export const metadata: Metadata = {
  title: '長野県15市町村(長野・松本・上田ほか)の公共スポーツ施設を横断検索',
  description:
    '長野県15市町村(長野・松本・上田・須坂・千曲・伊那・安曇野ほか)の公共テニスコート・サッカー場・フットサル場・体育館325施設を横断検索。ナイター可能テニス、屋内施設、無料施設、市町村などで絞り込み。',
};

export default async function HomePage() {
  const [nightTennis, stats, tonightAvailable] = await Promise.all([
    getNightTennisFacilities(),
    getStats(),
    getTonightAvailableTennisFacilities(),
  ]);

  // Schema.org JSON-LD (WebSite + 検索アクション)
  const siteUrl =
    process.env.NEXT_PUBLIC_SITE_URL || 'https://nagano-sports-finder.vercel.app';
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: '長野県公共施設ナビ',
    url: siteUrl,
    description:
      '長野県15市町村の公共テニスコート・サッカー場・フットサル場・体育館を横断検索できるデータベース。',
    potentialAction: {
      '@type': 'SearchAction',
      target: {
        '@type': 'EntryPoint',
        urlTemplate: `${siteUrl}/search?q={search_term_string}`,
      },
      'query-input': 'required name=search_term_string',
    },
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      {/* ヒーロー */}
      <section className="bg-gradient-to-br from-brand-500 to-brand-700 text-white rounded-2xl px-6 py-10 md:px-10 md:py-14 mb-10">
        <h1 className="text-3xl md:text-4xl font-bold mb-3 leading-tight">
          長野県の公共スポーツ施設を<br />横断検索
        </h1>
        <p className="text-brand-50 mb-2 text-sm md:text-base">
          テニス・サッカー・フットサル・体育館の空き状況を、ひとつのサイトで比較
        </p>
        <p className="text-brand-100 text-xs md:text-sm mb-6">
          ※現在対応地域：長野県15市町村（長野・松本・上田ほか） ／ 随時追加
        </p>

        {/* 検索ボックス */}
        <div className="max-w-xl mb-5">
          <SearchBox size="large" placeholder="施設名で検索 (例: 城山、南長野、エア・ウォーター、波田扇子田)" />
        </div>

        {/* 競技別クイック導線 */}
        <div className="flex flex-wrap gap-3">
          <Link
            href="/search?sport=tennis"
            className="inline-flex items-center gap-2 bg-white text-brand-700 px-5 py-2.5 rounded-lg font-bold shadow hover:bg-brand-50 transition"
          >
            🎾 テニス
          </Link>
          <Link
            href="/search?sport=soccer"
            className="inline-flex items-center gap-2 bg-white text-brand-700 px-5 py-2.5 rounded-lg font-bold shadow hover:bg-brand-50 transition"
          >
            ⚽ サッカー
          </Link>
          <Link
            href="/search?sport=futsal"
            className="inline-flex items-center gap-2 bg-white text-brand-700 px-5 py-2.5 rounded-lg font-bold shadow hover:bg-brand-50 transition"
          >
            🥅 フットサル
          </Link>
        </div>

        {/* 市町村別クイック導線 */}
        <div className="flex flex-wrap gap-3 mt-3">
          <Link
            href="/search?municipality=長野市"
            className="inline-flex items-center gap-2 bg-brand-800/30 hover:bg-brand-800/50 text-white border border-white/40 px-5 py-2 rounded-lg font-medium text-sm transition"
          >
            📍 長野市の施設
          </Link>
          <Link
            href="/search?municipality=松本市"
            className="inline-flex items-center gap-2 bg-brand-800/30 hover:bg-brand-800/50 text-white border border-white/40 px-5 py-2 rounded-lg font-medium text-sm transition"
          >
            📍 松本市の施設
          </Link>
          <Link
            href="/search?municipality=塩尻市"
            className="inline-flex items-center gap-2 bg-brand-800/30 hover:bg-brand-800/50 text-white border border-white/40 px-5 py-2 rounded-lg font-medium text-sm transition"
          >
            📍 塩尻市の施設
          </Link>
          <Link
            href="/search?municipality=茅野市"
            className="inline-flex items-center gap-2 bg-brand-800/30 hover:bg-brand-800/50 text-white border border-white/40 px-5 py-2 rounded-lg font-medium text-sm transition"
          >
            📍 茅野市の施設
          </Link>
          <Link
            href="/search?municipality=諏訪市"
            className="inline-flex items-center gap-2 bg-brand-800/30 hover:bg-brand-800/50 text-white border border-white/40 px-5 py-2 rounded-lg font-medium text-sm transition"
          >
            📍 諏訪市の施設
          </Link>
          <Link
            href="/search?municipality=岡谷市"
            className="inline-flex items-center gap-2 bg-brand-800/30 hover:bg-brand-800/50 text-white border border-white/40 px-5 py-2 rounded-lg font-medium text-sm transition"
          >
            📍 岡谷市の施設
          </Link>
        </div>
      </section>

      {/* 統計 */}
      <section className="grid grid-cols-3 gap-4 mb-10">
        <div className="bg-white border border-gray-200 rounded-lg p-4 text-center">
          <div className="text-2xl md:text-3xl font-bold text-brand-600">
            {stats.totalFacilities}
          </div>
          <div className="text-xs md:text-sm text-gray-600 mt-1">登録施設数</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4 text-center">
          <div className="text-2xl md:text-3xl font-bold text-brand-600">
            {stats.totalCourts}
          </div>
          <div className="text-xs md:text-sm text-gray-600 mt-1">合計コート面数</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4 text-center">
          <div className="text-2xl md:text-3xl font-bold text-amber-600">
            {stats.nightTennisFacilities}
          </div>
          <div className="text-xs md:text-sm text-gray-600 mt-1">ナイター可テニス</div>
        </div>
      </section>

      {/* クイック導線 */}
      <section className="mb-10">
        <h2 className="text-xl font-bold mb-4">条件で探す</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Link
            href="/search?sport=tennis&lighting=true"
            className="bg-amber-50 border border-amber-200 hover:bg-amber-100 rounded-lg p-4 text-center"
          >
            <div className="text-2xl mb-1">🌙</div>
            <div className="font-medium text-sm">ナイターテニス</div>
          </Link>
          <Link
            href="/search?sport=tennis&surface=砂入り人工芝"
            className="bg-emerald-50 border border-emerald-200 hover:bg-emerald-100 rounded-lg p-4 text-center"
          >
            <div className="text-2xl mb-1">🎾</div>
            <div className="font-medium text-sm">砂入り人工芝テニス</div>
          </Link>
          <Link
            href="/search?indoor=true"
            className="bg-blue-50 border border-blue-200 hover:bg-blue-100 rounded-lg p-4 text-center"
          >
            <div className="text-2xl mb-1">🏟️</div>
            <div className="font-medium text-sm">屋内施設</div>
          </Link>
          <Link
            href="/search?free=true"
            className="bg-green-50 border border-green-200 hover:bg-green-100 rounded-lg p-4 text-center"
          >
            <div className="text-2xl mb-1">💰</div>
            <div className="font-medium text-sm">無料施設</div>
          </Link>
        </div>
      </section>

      {/* 今夜空きあり (テニス) */}
      <section className="mb-10">
        <div className="flex items-baseline justify-between mb-4">
          <h2 className="text-xl font-bold">
            🌙 今夜空きあり {tonightAvailable.length > 0 && `(${tonightAvailable.length}施設)`}
          </h2>
          <Link
            href="/search?sport=tennis"
            className="text-sm text-brand-600 hover:underline"
          >
            テニス施設一覧 →
          </Link>
        </div>
        {tonightAvailable.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {tonightAvailable.slice(0, 6).map((f) => {
              const earliestSlot = f.tonightSlots[0];
              return (
                <Link
                  key={f.id}
                  href={`/facilities/${f.facility_code}`}
                  className="block bg-white border border-amber-300 rounded-lg p-4 shadow-sm hover:shadow-lg hover:border-amber-500 hover:-translate-y-0.5 transition-all duration-150"
                >
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-bold text-gray-900 leading-tight">
                      {f.facility_name}
                    </h3>
                    <span className="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded font-medium shrink-0 ml-2">
                      今夜空きあり
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 mb-2">
                    {f.municipality}
                    {f.court_count != null && ` ・ ${f.court_count}面`}
                    {f.surface_type && f.surface_type !== '要確認' && ` ・ ${f.surface_type}`}
                  </div>
                  <div className="text-xs text-gray-700">
                    最早:{' '}
                    <span className="font-mono">
                      {earliestSlot.start_time.slice(0, 5)}-
                      {earliestSlot.end_time.slice(0, 5)}
                    </span>
                    {' / '}
                    今夜 {f.tonightSlots.length}枠
                  </div>
                </Link>
              );
            })}
          </div>
        ) : (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-5">
            <p className="text-amber-800 font-medium mb-1">
              今夜（18:00以降）に空きのあるテニス施設はありません
            </p>
            <p className="text-sm text-gray-600">
              明日以降の空きは
              <Link
                href="/search?sport=tennis"
                className="text-brand-700 hover:underline mx-1"
              >
                テニス施設一覧
              </Link>
              から各施設の詳細ページで確認できます。
            </p>
          </div>
        )}
      </section>

      {/* ナイター可能テニス施設 */}
      <section>
        <div className="flex items-baseline justify-between mb-4">
          <h2 className="text-xl font-bold">ナイター可能テニス施設</h2>
          <Link
            href="/search?sport=tennis&lighting=true"
            className="text-sm text-brand-600 hover:underline"
          >
            すべて見る →
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {nightTennis.slice(0, 6).map((f) => (
            <FacilityCard key={f.id} facility={f} />
          ))}
        </div>
      </section>
    </div>
  );
}
