/**
 * notes フィールドのレンダリングユーティリティ
 *
 * notes に含まれる以下の表現を自動変換:
 *   1. facility_code (例: TEN-021) → 施設名+リンク
 *   2. 絶対URL (例: https://...) → クリック可能リンク
 *   3. 長野市公式サイトの相対パス (例: /documents/3172/football.pdf) → 絶対URL+リンク
 */
import Link from 'next/link';
import { Fragment, type ReactNode } from 'react';

// 例: "TEN-021", "SOC-007", "NAG-TEN-019" にマッチ
const FACILITY_CODE_PATTERN = /(?:NAG-)?(?:TEN|SOC)-\d{3}/g;

// 絶対URL (HTTP/HTTPS)
const URL_PATTERN = /https?:\/\/[^\s)）、。]+/g;

// 長野市公式サイトの相対パス
const NAGANO_PATH_PATTERN = /\/(?:documents|uploaded)\/[^\s)）、。]+/g;
const NAGANO_BASE_URL = 'https://www.city.nagano.nagano.jp';

export type FacilityNameLookup = Map<string, string>;

/** notes 内のfacility_codeを全件抽出 */
export function extractFacilityCodes(notes: string | null | undefined): string[] {
  if (!notes) return [];
  const matches = Array.from(notes.matchAll(FACILITY_CODE_PATTERN));
  const codes = matches.map((m) =>
    m[0].startsWith('NAG-') ? m[0] : `NAG-${m[0]}`,
  );
  return Array.from(new Set(codes));
}

type Match = {
  start: number;
  end: number;
  kind: 'facility' | 'url' | 'naganoPath';
  value: string;
};

/** 全パターンのマッチを取得して、位置順・重複なしで返す */
function findAllMatches(notes: string): Match[] {
  const matches: Match[] = [];

  for (const m of notes.matchAll(FACILITY_CODE_PATTERN)) {
    matches.push({
      start: m.index!,
      end: m.index! + m[0].length,
      kind: 'facility',
      value: m[0],
    });
  }
  for (const m of notes.matchAll(URL_PATTERN)) {
    matches.push({
      start: m.index!,
      end: m.index! + m[0].length,
      kind: 'url',
      value: m[0],
    });
  }
  for (const m of notes.matchAll(NAGANO_PATH_PATTERN)) {
    matches.push({
      start: m.index!,
      end: m.index! + m[0].length,
      kind: 'naganoPath',
      value: m[0],
    });
  }

  // 開始位置でソート
  matches.sort((a, b) => a.start - b.start);

  // 重複・包含を除去 (絶対URL内の/documents/... 等は外側を優先)
  const filtered: Match[] = [];
  for (const m of matches) {
    const overlaps = filtered.some(
      (f) => m.start < f.end && m.end > f.start,
    );
    if (!overlaps) {
      filtered.push(m);
    }
  }

  return filtered;
}

/** 詳細ページ用: notes をリンク付きで描画 */
export function renderNotesWithLinks(
  notes: string | null | undefined,
  lookup: FacilityNameLookup,
): ReactNode {
  if (!notes) return null;

  const matches = findAllMatches(notes);
  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;

  for (const m of matches) {
    if (m.start > lastIndex) {
      parts.push(notes.slice(lastIndex, m.start));
    }

    if (m.kind === 'facility') {
      const fullCode = m.value.startsWith('NAG-') ? m.value : `NAG-${m.value}`;
      const name = lookup.get(fullCode);
      if (name) {
        parts.push(
          <Link
            key={`f-${key++}`}
            href={`/facilities/${fullCode}`}
            className="text-brand-700 hover:text-brand-900 underline decoration-dotted"
          >
            {name}
          </Link>,
        );
      } else {
        parts.push(m.value);
      }
    } else if (m.kind === 'url') {
      parts.push(
        <a
          key={`u-${key++}`}
          href={m.value}
          target="_blank"
          rel="noopener noreferrer"
          className="text-brand-700 hover:text-brand-900 underline break-all"
        >
          {m.value}
        </a>,
      );
    } else if (m.kind === 'naganoPath') {
      const fullUrl = NAGANO_BASE_URL + m.value;
      parts.push(
        <a
          key={`p-${key++}`}
          href={fullUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-brand-700 hover:text-brand-900 underline break-all"
        >
          {m.value}
        </a>,
      );
    }

    lastIndex = m.end;
  }

  if (lastIndex < notes.length) {
    parts.push(notes.slice(lastIndex));
  }

  return parts.map((p, i) => <Fragment key={i}>{p}</Fragment>);
}

/**
 * カード表示用: codeを含む括弧表現を丸ごと除去 (リンク化されないため)
 * URLは線形リンクとして見せるとカードでは煩雑なので、PDFリンクも除去
 */
export function stripFacilityCodes(notes: string | null | undefined): string {
  if (!notes) return '';
  return notes
    // "(TEN-XXXと同敷地)" 形式の括弧ごと除去
    .replace(/[(（]\s*(?:NAG-)?(?:TEN|SOC)-\d{3}[^)）]*[)）]/g, '')
    // "TEN-XXXと同敷地" (括弧なし) を除去
    .replace(/(?:NAG-)?(?:TEN|SOC)-\d{3}と同敷地/g, '')
    // "詳細PDF: /documents/..." または "料金PDF: /documents/..." を除去
    .replace(/(?:詳細|料金)?PDF:?\s*\/(?:documents|uploaded)\/\S+/g, '')
    // 絶対URLも除去
    .replace(/https?:\/\/\S+/g, '')
    // 残った相対パスも除去
    .replace(/\/(?:documents|uploaded)\/\S+/g, '')
    // 連続する句読点・空白を整理
    .replace(/[。、]\s*[。、]/g, '。')
    .replace(/\s+/g, ' ')
    .trim();
}
