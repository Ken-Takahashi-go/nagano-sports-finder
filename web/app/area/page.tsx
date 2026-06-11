import type { Metadata } from 'next';
import Link from 'next/link';
import { searchFacilities } from '@/lib/queries';
import {
  LANDING_SPORTS,
  MUNICIPALITY_SLUGS,
  SPORT_FACILITY_NOUN,
} from '@/lib/areas';
import type { FacilityWithSports, SportType } from '@/lib/types';

export const revalidate = 60;

const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL || 'https://nagano-sports-finder.vercel.app';

export const metadata: Metadata = {
  title: 'エリア別の公共スポーツ施設一覧（市町村×競技）',
  description:
    '長野県15市町村ごとの公共テニスコート・サッカー場・フットサルコートを一覧で。市町村×競技別に空き状況・面数・ナイター可否をまとめて確認できます。',
  alternates: { canonical: `${SITE_URL}/area` },
};

export default async function AreaIndexPage() {
  const all = await searchFacilities();

  // 市町村ごとに (競技 → 施設数) を集計
  const byCity = new Map<string, Map<SportType, number>>();
  for (const f of all) {
    if (!MUNICIPALITY_SLUGS[f.municipality]) continue;
    const m = byCity.get(f.municipality) ?? new Map<SportType, number>();
    for (const s of f.sports) {
      if ((LANDING_SPORTS as readonly SportType[]).includes(s)) {
        m.set(s, (m.get(s) ?? 0) + 1);
      }
    }
    byCity.set(f.municipality, m);
  }

  // 表示順は MUNICIPALITY_SLUGS の定義順 (人口上位順)
  const cities = Object.keys(MUNICIPALITY_SLUGS).filter((c) => byCity.has(c));

  return (
    <div className="container mx-auto px-4 py-6 max-w-6xl">
      <nav className="text-sm text-gray-500 mb-4" aria-label="パンくず">
        <Link href="/" className="hover:underline">
          TOP
        </Link>
        <span className="mx-1">›</span>
        <span className="text-gray-700">エリア別</span>
      </nav>

      <h1 className="text-2xl md:text-3xl font-bold mb-2">
        エリア別の公共スポーツ施設一覧
      </h1>
      <p className="text-gray-700 mb-6">
        長野県{cities.length}市町村の公共テニスコート・サッカー場・フットサルコートを、
        市町村×競技別に一覧できます。気になるエリアと競技を選んでください。
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {cities.map((city) => {
          const slug = MUNICIPALITY_SLUGS[city];
          const sportCounts = byCity.get(city)!;
          return (
            <div
              key={city}
              className="bg-white border border-gray-200 rounded-lg p-4"
            >
              <h2 className="font-bold text-gray-900 mb-3">{city}</h2>
              <div className="flex flex-col gap-1.5">
                {LANDING_SPORTS.map((s) => {
                  const count = sportCounts.get(s) ?? 0;
                  if (count === 0) return null;
                  return (
                    <Link
                      key={s}
                      href={`/area/${slug}/${s}`}
                      className="flex items-center justify-between text-sm border border-gray-200 hover:border-brand-400 hover:bg-brand-50 rounded px-3 py-2 transition"
                    >
                      <span className="font-medium text-gray-800">
                        {SPORT_FACILITY_NOUN[s]}
                      </span>
                      <span className="text-xs text-gray-500">{count}施設 →</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
