import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { FacilityCard } from '@/components/FacilityCard';
import { searchFacilities } from '@/lib/queries';
import {
  LANDING_SPORTS,
  MUNICIPALITY_SLUGS,
  SLUG_TO_MUNICIPALITY,
  SPORT_FACILITY_NOUN,
  isLandingSport,
} from '@/lib/areas';
import { SPORT_LABEL, type FacilityWithSports, type SportType } from '@/lib/types';

export const revalidate = 60;

const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL || 'https://nagano-sports-finder.vercel.app';

type Params = { municipality: string; sport: string };

// =====================================================================
// 静的パラメータ: 施設が1件以上ある (市町村 × 競技) の組み合わせのみ生成
// =====================================================================
export async function generateStaticParams(): Promise<Params[]> {
  const all = await searchFacilities();
  const combos = new Set<string>();
  for (const f of all) {
    const slug = MUNICIPALITY_SLUGS[f.municipality];
    if (!slug) continue;
    for (const s of f.sports) {
      if (isLandingSport(s)) combos.add(`${slug}/${s}`);
    }
  }
  return Array.from(combos).map((c) => {
    const [municipality, sport] = c.split('/');
    return { municipality, sport };
  });
}

function resolve(params: Params): { municipalityJa: string; sport: SportType } | null {
  const municipalityJa = SLUG_TO_MUNICIPALITY[params.municipality];
  if (!municipalityJa || !isLandingSport(params.sport)) return null;
  return { municipalityJa, sport: params.sport };
}

// =====================================================================
// 動的メタデータ (SEO: 市町村×競技ごとに固有の title/description)
// =====================================================================
export async function generateMetadata({
  params,
}: {
  params: Params;
}): Promise<Metadata> {
  const r = resolve(params);
  if (!r) return { title: '該当ページが見つかりません' };
  const noun = SPORT_FACILITY_NOUN[r.sport];
  const all = await searchFacilities();
  const facilities = filterFacilities(all, r.municipalityJa, r.sport);
  const n = facilities.length;
  const night = facilities.filter((f) => f.lighting_available).length;

  const title = `${r.municipalityJa}の${noun}一覧・空き状況（${n}施設）`;
  const description =
    `${r.municipalityJa}の公共${noun}を一覧で比較。${n}施設` +
    `${night > 0 ? `（うちナイター可${night}施設）` : ''}` +
    `の空き状況・面数・サーフェス・利用料金をまとめて確認できます。長野県公共施設ナビ。`;
  const url = `${SITE_URL}/area/${params.municipality}/${params.sport}`;

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      url,
      siteName: '長野県公共施設ナビ',
      locale: 'ja_JP',
      type: 'website',
    },
    twitter: { card: 'summary', title, description },
    alternates: { canonical: url },
  };
}

function filterFacilities(
  all: FacilityWithSports[],
  municipalityJa: string,
  sport: SportType,
): FacilityWithSports[] {
  return all.filter(
    (f) => f.municipality === municipalityJa && f.sports.includes(sport),
  );
}

export default async function AreaSportPage({ params }: { params: Params }) {
  const r = resolve(params);
  if (!r) notFound();
  const { municipalityJa, sport } = r;
  const noun = SPORT_FACILITY_NOUN[sport];

  const all = await searchFacilities();
  const facilities = filterFacilities(all, municipalityJa, sport);
  if (facilities.length === 0) notFound();

  // 集計
  const night = facilities.filter((f) => f.lighting_available).length;
  const indoor = facilities.filter((f) => f.indoor_outdoor === '屋内').length;
  const free = facilities.filter((f) => f.fee_text === '無料').length;
  const totalCourts = facilities.reduce((s, f) => s + (f.court_count ?? 0), 0);

  // 内部リンク用: 同市の他競技 / 同競技の他市 (施設が存在するもののみ)
  const otherSportsInCity = LANDING_SPORTS.filter(
    (s) => s !== sport && filterFacilities(all, municipalityJa, s).length > 0,
  );
  const otherCitiesForSport = Object.entries(MUNICIPALITY_SLUGS)
    .filter(
      ([ja]) => ja !== municipalityJa && filterFacilities(all, ja, sport).length > 0,
    )
    .map(([ja, slug]) => ({ ja, slug }));

  const url = `${SITE_URL}/area/${params.municipality}/${params.sport}`;

  // JSON-LD: パンくず + 施設リスト
  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'TOP', item: SITE_URL },
          { '@type': 'ListItem', position: 2, name: 'エリア別', item: `${SITE_URL}/area` },
          {
            '@type': 'ListItem',
            position: 3,
            name: `${municipalityJa}の${noun}`,
            item: url,
          },
        ],
      },
      {
        '@type': 'ItemList',
        name: `${municipalityJa}の${noun}一覧`,
        numberOfItems: facilities.length,
        itemListElement: facilities.map((f, i) => ({
          '@type': 'ListItem',
          position: i + 1,
          name: f.facility_name,
          url: `${SITE_URL}/facilities/${f.facility_code}`,
        })),
      },
    ],
  };

  return (
    <div className="container mx-auto px-4 py-6 max-w-6xl">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* パンくず */}
      <nav className="text-sm text-gray-500 mb-4" aria-label="パンくず">
        <Link href="/" className="hover:underline">
          TOP
        </Link>
        <span className="mx-1">›</span>
        <Link href="/area" className="hover:underline">
          エリア別
        </Link>
        <span className="mx-1">›</span>
        <span className="text-gray-700">
          {municipalityJa}の{noun}
        </span>
      </nav>

      {/* 見出し */}
      <h1 className="text-2xl md:text-3xl font-bold mb-2">
        {municipalityJa}の{noun}一覧・空き状況
      </h1>
      <p className="text-gray-700 mb-5 leading-relaxed">
        {municipalityJa}内の公共{noun}
        <strong>全{facilities.length}施設</strong>を一覧で比較できます。
        {night > 0 && `ナイター対応${night}施設、`}
        {indoor > 0 && `屋内${indoor}施設、`}
        {free > 0 && `無料${free}施設。`}
        面数・サーフェス・利用料金・本日以降の空き状況をまとめて確認できます。
      </p>

      {/* 統計 */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Stat label="施設数" value={facilities.length} />
        <Stat label="合計面数" value={totalCourts} />
        <Stat label="ナイター可" value={night} accent />
        <Stat label="無料" value={free} />
      </section>

      {/* 施設一覧 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        {facilities.map((f) => (
          <FacilityCard key={f.id} facility={f} />
        ))}
      </div>

      {/* 内部リンク: 同市の他競技 */}
      {otherSportsInCity.length > 0 && (
        <section className="mb-6">
          <h2 className="text-lg font-bold mb-3">{municipalityJa}の他の施設</h2>
          <div className="flex flex-wrap gap-2">
            {otherSportsInCity.map((s) => (
              <Link
                key={s}
                href={`/area/${params.municipality}/${s}`}
                className="bg-white border border-gray-300 hover:border-brand-400 rounded-lg px-4 py-2 text-sm font-medium transition"
              >
                {municipalityJa}の{SPORT_FACILITY_NOUN[s]} →
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* 内部リンク: 同競技の他市 */}
      {otherCitiesForSport.length > 0 && (
        <section className="mb-6">
          <h2 className="text-lg font-bold mb-3">他の市町村の{noun}</h2>
          <div className="flex flex-wrap gap-2">
            {otherCitiesForSport.map(({ ja, slug }) => (
              <Link
                key={slug}
                href={`/area/${slug}/${sport}`}
                className="bg-white border border-gray-300 hover:border-brand-400 rounded-lg px-3 py-1.5 text-sm transition"
              >
                {ja}
              </Link>
            ))}
          </div>
        </section>
      )}

      <p className="text-xs text-gray-500 mt-8 pt-4 border-t border-gray-100">
        空き状況は最終確認時刻のスナップショットです。予約時は各施設の公式予約サイトで必ずご確認ください。
        {SPORT_LABEL[sport]}施設の条件をさらに絞り込むには
        <Link href={`/search?sport=${sport}&municipality=${encodeURIComponent(municipalityJa)}`} className="text-brand-700 hover:underline mx-1">
          詳細検索
        </Link>
        をご利用ください。
      </p>
    </div>
  );
}

function Stat({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: number;
  accent?: boolean;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3 text-center">
      <div
        className={`text-2xl font-bold ${accent ? 'text-amber-600' : 'text-brand-600'}`}
      >
        {value}
      </div>
      <div className="text-xs text-gray-600 mt-0.5">{label}</div>
    </div>
  );
}
