/**
 * Google Maps iframe埋め込み (APIキー不要)
 *
 * ピンを正確に表示するロジック:
 *   1. 緯度経度がある → loc:LAT,LNG(NAME) で正確なピン
 *   2. 緯度経度がない → 住所のみで検索 (施設名は含めない方がマッチ精度が高い)
 */
export function MapEmbed({
  address,
  facilityName,
  latitude,
  longitude,
  height = 300,
}: {
  address: string;
  facilityName?: string;
  latitude?: number | null;
  longitude?: number | null;
  height?: number;
}) {
  let query: string;
  let zoom: number;

  if (latitude != null && longitude != null) {
    // 緯度経度ベース: ピンが正確に立つ
    const label = facilityName ? `(${facilityName})` : '';
    query = `${latitude},${longitude}${label}`;
    zoom = 17;
  } else {
    // 住所のみ: 施設名なし(マッチ精度向上のため)
    query = address;
    zoom = 17;
  }

  const src = `https://maps.google.com/maps?q=${encodeURIComponent(query)}&z=${zoom}&output=embed`;
  const externalUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
    latitude != null && longitude != null
      ? `${latitude},${longitude}`
      : `${facilityName ?? ''} ${address}`,
  )}`;

  return (
    <div className="rounded-lg overflow-hidden border border-gray-200">
      <iframe
        src={src}
        width="100%"
        height={height}
        style={{ border: 0 }}
        loading="lazy"
        referrerPolicy="no-referrer-when-downgrade"
        title={`${facilityName ?? '施設'}の地図`}
      />
      <a
        href={externalUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="block bg-gray-50 hover:bg-gray-100 text-center text-sm py-2 text-brand-700 font-medium border-t border-gray-200"
      >
        Google Mapsで開く（経路案内）→
      </a>
    </div>
  );
}
