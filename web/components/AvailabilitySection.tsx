import type { AvailabilitySlot, AvailabilityStatus } from '@/lib/types';

const WEEKDAY_JA = ['日', '月', '火', '水', '木', '金', '土'];

/** 過去時間帯のスロットを除外 (今日の場合は現時刻以降のみ) */
function filterPastSlots(slots: AvailabilitySlot[]): AvailabilitySlot[] {
  const now = new Date();
  const todayStr = now.toISOString().slice(0, 10);
  const nowHHMM = now.toTimeString().slice(0, 5);

  return slots.filter((slot) => {
    if (slot.target_date > todayStr) return true;
    if (slot.target_date < todayStr) return false;
    return slot.end_time.slice(0, 5) > nowHHMM;
  });
}

/** マトリクス用にデータを整形 */
function buildMatrix(slots: AvailabilitySlot[]) {
  // 日付集合 (昇順)
  const dateSet = new Set(slots.map((s) => s.target_date));
  const dates = Array.from(dateSet).sort();

  // 時間スロット集合 (start_time-end_time のユニークなペア、料金は最頻値)
  type TsEntry = {
    start: string;
    end: string;
    feeCounts: Map<number, number>;
  };
  const tsMap = new Map<string, TsEntry>();
  for (const s of slots) {
    const key = `${s.start_time}|${s.end_time}`;
    if (!tsMap.has(key)) {
      tsMap.set(key, { start: s.start_time, end: s.end_time, feeCounts: new Map() });
    }
    const entry = tsMap.get(key)!;
    if (s.fee_min_yen != null) {
      entry.feeCounts.set(s.fee_min_yen, (entry.feeCounts.get(s.fee_min_yen) ?? 0) + 1);
    }
  }
  const timeSlots = Array.from(tsMap.values())
    .map((t) => {
      // 最頻値の料金を採用
      let topFee: number | null = null;
      let topCount = 0;
      for (const [fee, count] of t.feeCounts) {
        if (count > topCount) {
          topFee = fee;
          topCount = count;
        }
      }
      return { start: t.start, end: t.end, fee: topFee, key: `${t.start}|${t.end}` };
    })
    .sort((a, b) => a.start.localeCompare(b.start));

  // セル: (date, ts.key) → slot
  const cells = new Map<string, AvailabilitySlot>();
  for (const s of slots) {
    cells.set(`${s.target_date}|${s.start_time}|${s.end_time}`, s);
  }

  return { dates, timeSlots, cells };
}

/** 空き状況マトリクス (詳細ページ用) */
export function AvailabilitySection({
  slots,
  officialUrl,
  reservationUrl,
}: {
  slots: AvailabilitySlot[];
  officialUrl?: string | null;
  reservationUrl?: string | null;
}) {
  const futureSlots = filterPastSlots(slots);

  if (futureSlots.length === 0) {
    return (
      <section className="mb-6 bg-white border border-gray-200 rounded-lg p-5">
        <h2 className="text-lg font-bold mb-3 text-gray-900">空き状況</h2>
        <p className="text-sm text-gray-600 mb-3">
          この施設の空き状況は現在自動取得していません。公式予約サイトでご確認ください。
        </p>
        <div className="flex flex-wrap gap-2 text-sm">
          {reservationUrl && (
            <a
              href={reservationUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded font-medium"
            >
              予約サイトで確認 →
            </a>
          )}
          {officialUrl && (
            <a
              href={officialUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 px-4 py-2 rounded"
            >
              公式ページ →
            </a>
          )}
        </div>
      </section>
    );
  }

  const { dates, timeSlots, cells } = buildMatrix(futureSlots);

  // 最終確認時刻
  const lastChecked = futureSlots.reduce(
    (latest, s) => (s.last_checked_at > latest ? s.last_checked_at : latest),
    futureSlots[0].last_checked_at,
  );
  const lastCheckedJa = new Date(lastChecked).toLocaleString('ja-JP', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <section className="mb-6 bg-white border border-gray-200 rounded-lg p-5">
      <div className="flex flex-wrap items-baseline justify-between mb-3 gap-2">
        <h2 className="text-lg font-bold text-gray-900">空き状況</h2>
        <span className="text-xs text-gray-500">
          最終確認: {lastCheckedJa} ・ 出典: 長野市まちかぎリモート
        </span>
      </div>

      {/* 凡例 */}
      <div className="flex flex-wrap gap-3 mb-3 text-xs text-gray-600">
        <span className="flex items-center gap-1">
          <StatusBadge status="空き" /> 全コート空き
        </span>
        <span className="flex items-center gap-1">
          <StatusBadge status="一部空き" /> 一部のみ空き
        </span>
        <span className="flex items-center gap-1">
          <StatusBadge status="満" /> 全コート予約済
        </span>
      </div>

      {/* マトリクス表 (横スクロール対応) */}
      <div className="overflow-x-auto -mx-5 px-5">
        <table className="min-w-full text-sm border-collapse">
          <thead>
            <tr className="border-b-2 border-gray-200">
              <th className="sticky left-0 bg-white z-10 text-left text-xs font-medium text-gray-600 px-2 py-2 min-w-[80px]">
                日付
              </th>
              {timeSlots.map((ts) => (
                <th
                  key={ts.key}
                  className="text-center text-xs font-medium text-gray-600 px-1 py-2 min-w-[72px]"
                >
                  <div className="font-mono">
                    {ts.start.slice(0, 5)}
                    <br />
                    {ts.end.slice(0, 5)}
                  </div>
                  {ts.fee != null && (
                    <div className="text-amber-700 mt-1 font-medium">
                      ¥{ts.fee.toLocaleString()}
                    </div>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dates.map((date) => {
              const d = new Date(date + 'T00:00:00');
              const dow = WEEKDAY_JA[d.getDay()];
              const dayClass =
                d.getDay() === 0
                  ? 'text-red-600'
                  : d.getDay() === 6
                    ? 'text-blue-600'
                    : 'text-gray-800';
              return (
                <tr key={date} className="border-b border-gray-100">
                  <td
                    className={`sticky left-0 bg-white z-10 px-2 py-2 font-medium whitespace-nowrap ${dayClass}`}
                  >
                    {d.getMonth() + 1}/{d.getDate()} ({dow})
                  </td>
                  {timeSlots.map((ts) => {
                    const cell = cells.get(`${date}|${ts.start}|${ts.end}`);
                    return (
                      <td key={ts.key} className="text-center px-1 py-2">
                        {cell ? <CellContent slot={cell} ts={ts} /> : <span className="text-gray-300">−</span>}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-500 mt-4 pt-3 border-t border-gray-100">
        最新の空き状況は公式予約サイトで必ずご確認ください。
        {reservationUrl && (
          <>
            {' '}
            <a
              href={reservationUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-700 hover:underline"
            >
              予約サイトを開く →
            </a>
          </>
        )}
      </p>
    </section>
  );
}

/** 1セル内の表示 */
function CellContent({
  slot,
  ts,
}: {
  slot: AvailabilitySlot;
  ts: { fee: number | null };
}) {
  // 残少時 (空きが30%以下) は強調
  const isScarce =
    slot.availability_status === '一部空き' &&
    slot.available_court_count != null &&
    slot.total_court_count != null &&
    slot.available_court_count / slot.total_court_count <= 0.3;

  // セル料金が時間帯標準料金と違う場合は差分表示
  const cellFee = slot.fee_min_yen;
  const isDifferentFee = cellFee != null && ts.fee != null && cellFee !== ts.fee;

  return (
    <div className="flex flex-col items-center gap-0.5">
      <StatusBadge status={slot.availability_status} small />
      {slot.available_court_count != null && slot.total_court_count != null && (
        <span className="text-sm text-gray-800 font-mono font-semibold leading-tight">
          {slot.available_court_count}/{slot.total_court_count}
        </span>
      )}
      {isDifferentFee && (
        <span className="text-[10px] text-amber-700 font-medium">
          ¥{cellFee!.toLocaleString()}
        </span>
      )}
      {isScarce && <span className="text-xs text-red-600 leading-tight">🔥</span>}
    </div>
  );
}

/** 空き状況バッジ */
function StatusBadge({
  status,
  small = false,
}: {
  status: AvailabilityStatus;
  small?: boolean;
}) {
  const styles: Record<AvailabilityStatus, string> = {
    '空き': 'bg-green-100 text-green-700 border-green-300',
    '一部空き': 'bg-amber-100 text-amber-700 border-amber-300',
    '満': 'bg-gray-100 text-gray-500 border-gray-300',
    '不明': 'bg-gray-50 text-gray-400 border-gray-200',
    '休館': 'bg-gray-100 text-gray-500 border-gray-300',
  };
  const symbol: Record<AvailabilityStatus, string> = {
    '空き': '○',
    '一部空き': '△',
    '満': '×',
    '不明': '?',
    '休館': '休',
  };
  const sizeClass = small ? 'w-6 h-6 text-xs' : 'w-7 h-7 text-sm';
  return (
    <span
      className={`inline-flex items-center justify-center font-bold rounded border ${sizeClass} ${styles[status]}`}
      title={status}
    >
      {symbol[status]}
    </span>
  );
}
