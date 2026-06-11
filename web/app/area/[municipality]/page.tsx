import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { searchFacilities } from '@/lib/queries';
import {
  LANDING_SPORTS,
  MUNICIPALITY_SLUGS,
  SLUG_TO_MUNICIPALITY,
  SPORT_FACILITY_NOUN,
} from '@/lib/areas';
import type { FacilityWithSports, SportType } from '@/lib/types';

export const revalidate = 60;

const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL || 'https://nagano-sports-finder.vercel.app';

type Params = { municipality: string };

export async function generateStaticParams(): Promise<Params[]> {
  const all = await searchFacilities();
  const slugs = new Set<string>();
  for (const f of all) {
    const slug = MUNICIPALITY_SLUGS[f.municipality];
    if (slug) slugs.add(slug);
  }
  return Array.from(slugs).map((municipality) => ({ municipality }));
}

export async function generateMetadata({
  params,
}: {
  params: Params;
}): Promise<Metadata> {
  const municipalityJa = SLUG_TO_MUNICIPALITY[params.municipality];
  if (!municipalityJa) return { title: '該当ページが見つかりません' };
  const title = `${municipalityJa}の公共スポーツ施設（テニス・サッカー・フットサル）`;
  const description = `${municipalityJa}の公共テニスコート・サッカー場・フットサルコートを競技別に一覧。空き状況・面数・ナイター可否をまとめて確認できます。長野県公共施設ナビ。`;
  const url = `${SITE_URL}/area/${params.municipality}`;
  return {
    title,
    description,
    openGraph: { title, description, url, siteName: '長野県公共施設ナビ', locale: 'ja_JP', type: 'website' },
    twitter: { card: 'summary', title, description },
    alternates: { canonical: url },
  };
}

export default async function AreaCityPage({ params }: { params: Params }) {
  const municipalityJa = SLUG_TO_MUNICIPALITY[params.municipality];
  if (!municipalityJa) notFound();

  const all = await searchFacilities();
  const cityFacilities = all.filter(
    (f: FacilityWithSports) => f.municipality === municipalityJa,
  );
  if (cityFacilities.length === 0) notFound();

  const sportCounts = new Map<SportType, number>();
  for (const f of cityFacilities) {
    for (const s of f.sports) {
      if ((LANDING_SPORTS as readonly SportType[]).includes(s)) {
        sportCounts.set(s, (sportCounts.get(s) ?? 0) + 1);
      }
    }
  }
  const availableSports = LANDING_SPORTS.filter((s) => (sportCounts.get(s) ?? 0) > 0);

  return (
    <div className="container mx-auto px-4 py-6 max-w-5xl">
      <nav className="text-sm text-gray-500 mb-4" aria-label="パンくず">
        <Link href="/" className="hover:underline">TOP</Link>
        <span className="mx-1">›</span>
        <Link href="/area" className="hover:underline">エリア別</Link>
        <span className="mx-1">›</span>
        <span className="text-gray-700">{municipalityJa}</span>
      </nav>

      <h1 className="text-2xl md:text-3xl font-bold mb-2">
        {municipalityJa}の公共スポーツ施設
      </h1>
      <p className="text-gray-700 mb-6">
        {municipalityJa}内の公共スポーツ施設を競技別に一覧できます。
        テニス・サッカー・フットサルから選んでください。
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {availableSports.map((s) => (
          <Link
            key={s}
            href={`/area/${params.municipality}/${s}`}
            className="bg-white border border-gray-200 hover:border-brand-400 hover:bg-brand-50 rounded-lg p-5 transition flex items-center justify-between"
          >
            <span className="font-bold text-gray-900">
              {municipalityJa}の{SPORT_FACILITY_NOUN[s]}
            </span>
            <span className="text-sm text-gray-500 shrink-0 ml-2">
              {sportCounts.get(s)}施設 →
            </span>
          </Link>
        ))}
      </div>

      <p className="text-sm text-gray-600 mt-8">
        他の市町村は
        <Link href="/area" className="text-brand-700 hover:underline mx-1">
          エリア別一覧
        </Link>
        から。
      </p>
    </div>
  );
}
