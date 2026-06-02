import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { AvailabilitySection } from '@/components/AvailabilitySection';
import { MapEmbed } from '@/components/MapEmbed';
import {
  getAvailabilityByFacilityId,
  getFacilityByCode,
  getFacilityNameLookup,
} from '@/lib/queries';
import { extractFacilityCodes, renderNotesWithLinks } from '@/lib/notes';
import { SPORT_LABEL, type FacilityWithSports } from '@/lib/types';

export const revalidate = 60;

// =====================================================================
// 動的メタデータ生成 (SEO)
// =====================================================================
export async function generateMetadata({
  params,
}: {
  params: { code: string };
}): Promise<Metadata> {
  const f = await getFacilityByCode(params.code);
  if (!f) {
    return { title: '施設が見つかりません' };
  }

  const sportsLabel = f.sports.map((s) => SPORT_LABEL[s]).join('・');
  const features: string[] = [];
  if (f.court_count) features.push(`${f.court_count}面`);
  if (f.surface_type && f.surface_type !== '要確認') features.push(f.surface_type);
  if (f.lighting_available) features.push('ナイター可');
  if (f.indoor_outdoor === '屋内') features.push('屋内');
  if (f.fee_text === '無料') features.push('利用無料');

  const title = `${f.facility_name} - ${f.municipality}の${sportsLabel}施設`;
  const description = `${f.facility_name}（${f.municipality}${f.address ? '、' + f.address : ''}）の施設情報。${features.join(' / ')}${f.phone_number ? ` / TEL: ${f.phone_number}` : ''}。長野県公共施設ナビ。`;
  const siteUrl =
    process.env.NEXT_PUBLIC_SITE_URL || 'https://nagano-sports-finder.vercel.app';
  const url = `${siteUrl}/facilities/${f.facility_code}`;

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
    twitter: {
      card: 'summary',
      title,
      description,
    },
    alternates: { canonical: url },
  };
}

export default async function FacilityDetailPage({
  params,
}: {
  params: { code: string };
}) {
  const f = await getFacilityByCode(params.code);

  if (!f) {
    notFound();
  }

  const lastVerified = new Date(f.last_verified_at).toLocaleDateString('ja-JP');

  // notes 内のfacility_code参照をリンク変換するための辞書
  const referencedCodes = extractFacilityCodes(f.notes);
  const nameLookup = await getFacilityNameLookup(referencedCodes);

  // 空き状況 (今日以降30日分)
  const availabilitySlots = await getAvailabilityByFacilityId(f.id, 30);

  return (
    <div className="container mx-auto px-4 py-6 max-w-4xl">
      {/* JSON-LD 構造化データ (Google検索リッチリザルト用) */}
      <StructuredData facility={f} />

      {/* パンくず */}
      <nav className="text-sm text-gray-500 mb-4" aria-label="パンくず">
        <Link href="/" className="hover:underline">TOP</Link>
        <span className="mx-2">›</span>
        <Link href="/search" className="hover:underline">施設検索</Link>
        <span className="mx-2">›</span>
        <span className="text-gray-700">{f.facility_name}</span>
      </nav>

      {/* データ信頼度C(詳細未取得)の警告 */}
      {f.data_confidence === 'C' && (
        <div className="mb-4 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-900">
          <strong className="font-bold">情報整備中</strong>
          <span className="ml-2">
            この施設の詳細（住所・料金・営業時間など）は確認中です。
            利用前に公式予約サイトでご確認ください。
          </span>
        </div>
      )}

      {/* タイトル + バッジ */}
      <div className="mb-6">
        <h1 className="text-2xl md:text-3xl font-bold mb-2">{f.facility_name}</h1>
        <div className="flex flex-wrap gap-2">
          {f.sports.map((s) => (
            <span
              key={s}
              className="bg-brand-100 text-brand-700 px-3 py-1 rounded text-sm font-medium"
            >
              {SPORT_LABEL[s]}
            </span>
          ))}
          {f.lighting_available && (
            <span className="bg-amber-100 text-amber-700 px-3 py-1 rounded text-sm font-medium">
              ナイター可
            </span>
          )}
          {f.indoor_outdoor === '屋内' && (
            <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded text-sm font-medium">
              屋内
            </span>
          )}
          {f.fee_text === '無料' && (
            <span className="bg-green-100 text-green-700 px-3 py-1 rounded text-sm font-medium">
              利用無料
            </span>
          )}
        </div>
      </div>

      {/* 主要属性 */}
      <section className="bg-white border border-gray-200 rounded-lg p-5 mb-6">
        <h2 className="text-lg font-bold mb-4 text-gray-900">施設情報</h2>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <InfoRow label="所在地" value={f.address} />
          <InfoRow label="市町村" value={f.municipality} />
          <InfoRow label="屋内/屋外" value={f.indoor_outdoor} />
          <InfoRow label="サーフェス" value={f.surface_type} />
          <InfoRow label="面数" value={f.court_count !== null ? `${f.court_count}面` : null} />
          <InfoRow
            label="ナイター"
            value={
              f.lighting_available === true
                ? 'あり'
                : f.lighting_available === false
                  ? 'なし'
                  : null
            }
          />
          <InfoRow label="利用時間" value={f.operating_hours} />
          <InfoRow label="定休日・休場日" value={f.closed_days} />
          <InfoRow label="駐車場" value={f.parking} />
          <InfoRow label="更衣室/シャワー" value={f.changing_shower} />
          <InfoRow label="基本料金" value={f.fee_text} />
          <InfoRow label="予約方法" value={f.booking_method} />
          <InfoRow label="利用者登録" value={f.registration_required} />
          <InfoRow label="市外利用" value={f.nonresident_policy} />
          <InfoRow label="当日予約" value={f.same_day_booking} />
          <InfoRow label="電話番号" value={f.phone_number} />
        </dl>

        {f.notes && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <div className="text-xs text-gray-500 mb-1">備考</div>
            <p className="text-sm text-gray-700 whitespace-pre-line">
              {renderNotesWithLinks(f.notes, nameLookup)}
            </p>
          </div>
        )}
      </section>

      {/* 空き状況 */}
      <AvailabilitySection
        slots={availabilitySlots}
        officialUrl={f.official_url}
        reservationUrl={f.reservation_url}
        municipality={f.municipality}
        phoneNumber={f.phone_number}
      />

      {/* 地図 */}
      {f.address && (
        <section className="mb-6">
          <h2 className="text-lg font-bold mb-3 text-gray-900">アクセス</h2>
          <MapEmbed
            address={f.address}
            facilityName={f.facility_name}
            latitude={f.latitude}
            longitude={f.longitude}
          />
        </section>
      )}

      {/* 予約導線 */}
      <section className="bg-brand-50 border border-brand-200 rounded-lg p-5 mb-6">
        <h2 className="text-lg font-bold mb-3 text-gray-900">予約・問い合わせ</h2>
        <div className="flex flex-wrap gap-3">
          {f.official_url && (
            <a
              href={f.official_url}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded font-medium text-sm"
            >
              公式ページへ →
            </a>
          )}
          {f.reservation_url && (
            <a
              href={f.reservation_url}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-white border border-brand-600 text-brand-700 hover:bg-brand-50 px-5 py-2.5 rounded font-medium text-sm"
            >
              予約サイトへ →
            </a>
          )}
          {f.phone_number && (
            <a
              href={`tel:${f.phone_number}`}
              className="bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 px-5 py-2.5 rounded font-medium text-sm"
            >
              📞 {f.phone_number}
            </a>
          )}
        </div>
      </section>

      {/* データ鮮度 */}
      <p className="text-xs text-gray-500 text-center">
        最終確認日: {lastVerified} ｜ データ信頼度: {f.data_confidence}
        <br />
        最新の利用条件は公式サイトでご確認ください
      </p>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value || value === '要確認' || value === '記載なし') {
    return (
      <div>
        <dt className="text-xs text-gray-500">{label}</dt>
        <dd className="text-gray-400 italic">未取得</dd>
      </div>
    );
  }
  return (
    <div>
      <dt className="text-xs text-gray-500">{label}</dt>
      <dd className="text-gray-900">{value}</dd>
    </div>
  );
}

/**
 * Schema.org JSON-LD構造化データ
 * SportsActivityLocation: Google検索でリッチリザルト対応
 */
function StructuredData({ facility: f }: { facility: FacilityWithSports }) {
  const sportsLabel = f.sports.map((s) => SPORT_LABEL[s]);
  const siteUrl =
    process.env.NEXT_PUBLIC_SITE_URL || 'https://nagano-sports-finder.vercel.app';
  const url = `${siteUrl}/facilities/${f.facility_code}`;

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'SportsActivityLocation',
    name: f.facility_name,
    description: f.notes ?? `${f.municipality}の${sportsLabel.join('・')}施設`,
    url,
    address: {
      '@type': 'PostalAddress',
      addressLocality: f.municipality,
      streetAddress: f.address ?? undefined,
      addressCountry: 'JP',
    },
    ...(f.latitude && f.longitude
      ? {
          geo: {
            '@type': 'GeoCoordinates',
            latitude: f.latitude,
            longitude: f.longitude,
          },
        }
      : {}),
    ...(f.phone_number ? { telephone: f.phone_number } : {}),
    sport: sportsLabel,
    isAccessibleForFree: f.fee_text === '無料',
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
