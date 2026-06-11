import type { MetadataRoute } from 'next';
import { searchFacilities } from '@/lib/queries';
import { MUNICIPALITY_SLUGS, isLandingSport } from '@/lib/areas';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://nagano-sports-finder.vercel.app';

export const revalidate = 3600; // 1時間ごとにsitemapを再生成

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const facilities = await searchFacilities();

  // 静的ページ
  const staticPages: MetadataRoute.Sitemap = [
    {
      url: SITE_URL,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1.0,
    },
    {
      url: `${SITE_URL}/area`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.9,
    },
    {
      url: `${SITE_URL}/search?sport=tennis`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.8,
    },
    {
      url: `${SITE_URL}/search?sport=soccer`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.8,
    },
    {
      url: `${SITE_URL}/search?sport=futsal`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.8,
    },
    {
      url: `${SITE_URL}/search?sport=tennis&lighting=true`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.7,
    },
  ];

  // 市町村×競技ランディングページ (施設が存在する組み合わせのみ)
  const comboSet = new Set<string>();
  for (const f of facilities) {
    const slug = MUNICIPALITY_SLUGS[f.municipality];
    if (!slug) continue;
    for (const s of f.sports) {
      if (isLandingSport(s)) comboSet.add(`${slug}/${s}`);
    }
  }
  const areaPages: MetadataRoute.Sitemap = Array.from(comboSet).map((c) => ({
    url: `${SITE_URL}/area/${c}`,
    lastModified: new Date(),
    changeFrequency: 'daily',
    priority: 0.8,
  }));

  // 施設詳細ページ (動的)
  const facilityPages: MetadataRoute.Sitemap = facilities.map((f) => ({
    url: `${SITE_URL}/facilities/${f.facility_code}`,
    lastModified: new Date(f.last_verified_at),
    changeFrequency: 'weekly',
    priority: 0.6,
  }));

  return [...staticPages, ...areaPages, ...facilityPages];
}
