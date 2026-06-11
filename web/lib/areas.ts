// =====================================================================
// 市町村 × 競技 ランディングページ用の定義
// SEO: 「松本市 テニスコート 空き」等のローカル検索意図に対応する
//      クロール可能な静的ページの基盤。/search? はrobotsで遮断しているため、
//      ここで実URL (/area/[slug]/[sport]) を提供する。
// =====================================================================
import type { SportType } from './types';

/** 市町村名(日本語) → romaji スラッグ (URL用) */
export const MUNICIPALITY_SLUGS: Record<string, string> = {
  長野市: 'nagano',
  松本市: 'matsumoto',
  上田市: 'ueda',
  須坂市: 'suzaka',
  千曲市: 'chikuma',
  伊那市: 'ina',
  安曇野市: 'azumino',
  塩尻市: 'shiojiri',
  茅野市: 'chino',
  諏訪市: 'suwa',
  岡谷市: 'okaya',
  駒ヶ根市: 'komagane',
  東御市: 'tomi',
  大町市: 'omachi',
  箕輪町: 'minowa',
};

/** romaji スラッグ → 市町村名(日本語) */
export const SLUG_TO_MUNICIPALITY: Record<string, string> = Object.fromEntries(
  Object.entries(MUNICIPALITY_SLUGS).map(([ja, slug]) => [slug, ja]),
);

/**
 * ランディングページを生成する競技。
 * 実際の検索意図が「施設カテゴリ」として成立する3競技に絞る
 * (例: 「○○市 テニスコート」。体育館系の basketball/volleyball は別意図のため除外)
 */
export const LANDING_SPORTS: readonly SportType[] = ['tennis', 'soccer', 'futsal'];

/** 競技 → 施設カテゴリ名詞 (見出し・本文・タイトル用) */
export const SPORT_FACILITY_NOUN: Record<string, string> = {
  tennis: 'テニスコート',
  soccer: 'サッカー場',
  futsal: 'フットサルコート',
};

export function isLandingSport(s: string): s is SportType {
  return (LANDING_SPORTS as readonly string[]).includes(s);
}

export function municipalitySlug(ja: string): string | undefined {
  return MUNICIPALITY_SLUGS[ja];
}
