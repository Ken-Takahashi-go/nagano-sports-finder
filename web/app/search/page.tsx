import type { Metadata } from 'next';
import Link from 'next/link';
import { FacilityCard } from '@/components/FacilityCard';
import { SearchBox } from '@/components/SearchBox';
import { searchFacilities } from '@/lib/queries';
import type { SearchFilters, SportType, SurfaceType } from '@/lib/types';

export const revalidate = 60;

export const metadata: Metadata = {
  title: '施設検索',
  description:
    '長野県(長野市・松本市)の公共スポーツ施設を条件で絞り込み検索。競技・サーフェス・ナイター可否・屋内/屋外・料金・市町村で絞り込めます。',
  // 検索ページは無限のクエリの組み合わせがあるため、検索結果はnoindex推奨
  robots: { index: false, follow: true },
};

type SearchParams = {
  sport?: string;
  surface?: string;
  lighting?: string;
  indoor?: string;
  free?: string;
  municipality?: string;
  q?: string;
};

export default async function SearchPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const filters: SearchFilters = {
    sport: searchParams.sport as SportType | undefined,
    surface: searchParams.surface as SurfaceType | undefined,
    lighting: searchParams.lighting === 'true' ? true : undefined,
    indoor: searchParams.indoor === 'true' ? true : undefined,
    free: searchParams.free === 'true' ? true : undefined,
    municipality: searchParams.municipality || undefined,
    q: searchParams.q || undefined,
  };

  const facilities = await searchFacilities(filters);

  // フィルタタグの表示用
  const activeFilters: string[] = [];
  if (filters.q) activeFilters.push(`「${filters.q}」を含む`);
  if (filters.municipality) activeFilters.push(filters.municipality);
  if (filters.sport === 'tennis') activeFilters.push('テニス');
  if (filters.sport === 'soccer') activeFilters.push('サッカー');
  if (filters.sport === 'futsal') activeFilters.push('フットサル');
  if (filters.surface) activeFilters.push(filters.surface);
  if (filters.lighting) activeFilters.push('ナイター可');
  if (filters.indoor) activeFilters.push('屋内');
  if (filters.free) activeFilters.push('無料');

  return (
    <div className="container mx-auto px-4 py-6 max-w-6xl">
      <h1 className="text-2xl font-bold mb-4">施設検索</h1>

      {/* テキスト検索ボックス */}
      <div className="mb-4 max-w-xl">
        <SearchBox
          defaultQuery={searchParams.q ?? ''}
          preserveParams={{
            sport: searchParams.sport,
            surface: searchParams.surface,
            lighting: searchParams.lighting,
            indoor: searchParams.indoor,
            free: searchParams.free,
            municipality: searchParams.municipality,
          }}
        />
      </div>

      {activeFilters.length > 0 && (
        <div className="bg-brand-50 border-2 border-brand-300 rounded-lg p-3 mb-4 flex flex-wrap items-center gap-2">
          <span className="text-sm font-bold text-brand-800 flex items-center gap-1">
            🔍 適用中のフィルタ
          </span>
          {activeFilters.map((label) => (
            <span
              key={label}
              className="text-xs bg-white text-brand-700 border border-brand-300 px-3 py-1 rounded-full font-medium"
            >
              {label}
            </span>
          ))}
          <Link
            href="/search"
            className="ml-auto inline-flex items-center gap-1 text-sm bg-red-600 hover:bg-red-700 text-white px-4 py-1.5 rounded-full font-bold shadow-sm transition"
            aria-label="すべてのフィルタをクリア"
          >
            <span aria-hidden="true">✕</span>
            すべてクリア
          </Link>
        </div>
      )}

      {/* クイックフィルタ */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6 space-y-2">
        {/* 市町村 */}
        <div className="flex flex-wrap gap-2 text-sm items-center">
          <span className="text-xs text-gray-500 mr-1">市町村:</span>
          <FilterLink current={searchParams} param="municipality" value="長野市" label="長野市" />
          <FilterLink current={searchParams} param="municipality" value="松本市" label="松本市" />
          <FilterLink current={searchParams} param="municipality" value="塩尻市" label="塩尻市" />
          <FilterLink current={searchParams} param="municipality" value="茅野市" label="茅野市" />
          <FilterLink current={searchParams} param="municipality" value="諏訪市" label="諏訪市" />
          <FilterLink current={searchParams} param="municipality" value="岡谷市" label="岡谷市" />
        </div>
        {/* 競技・属性 */}
        <div className="flex flex-wrap gap-2 text-sm">
          <FilterLink current={searchParams} param="sport" value="tennis" label="テニス" />
          <FilterLink current={searchParams} param="sport" value="soccer" label="サッカー" />
          <FilterLink current={searchParams} param="sport" value="futsal" label="フットサル" />
          <span className="border-r border-gray-300 mx-1"></span>
          <FilterLink current={searchParams} param="lighting" value="true" label="🌙 ナイター可" />
          <FilterLink current={searchParams} param="indoor" value="true" label="🏟️ 屋内" />
          <FilterLink current={searchParams} param="free" value="true" label="💰 無料" />
          <span className="border-r border-gray-300 mx-1"></span>
          <FilterLink current={searchParams} param="surface" value="砂入り人工芝" label="砂入り人工芝" />
          <FilterLink current={searchParams} param="surface" value="人工芝" label="人工芝" />
          <FilterLink current={searchParams} param="surface" value="クレー" label="クレー" />
          <FilterLink current={searchParams} param="surface" value="全天候型舗装" label="全天候型舗装" />
        </div>
      </div>

      <p className="text-sm text-gray-600 mb-4">
        {facilities.length}件の施設が見つかりました
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {facilities.map((f) => (
          <FacilityCard key={f.id} facility={f} />
        ))}
      </div>

      {facilities.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          条件に合う施設が見つかりませんでした。条件を変えてお試しください。
        </div>
      )}
    </div>
  );
}

/** フィルタトグル用リンク (現在のURL paramsを保持して特定paramだけ切り替え) */
function FilterLink({
  current,
  param,
  value,
  label,
}: {
  current: SearchParams;
  param: keyof SearchParams;
  value: string;
  label: string;
}) {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(current)) {
    if (v && k !== param) params.set(k, v as string);
  }
  const isActive = current[param] === value;
  if (!isActive) params.set(param, value);

  return (
    <Link
      href={`/search?${params.toString()}`}
      className={`px-3 py-1.5 rounded border transition ${
        isActive
          ? 'bg-brand-600 text-white border-brand-600'
          : 'bg-white text-gray-700 border-gray-300 hover:border-brand-400'
      }`}
    >
      {label}
    </Link>
  );
}
