// =====================================================================
// DB型定義 — schema_v2 に対応
// =====================================================================

export type SportType =
  | 'tennis'
  | 'soccer'
  | 'futsal'
  | 'rugby'
  | 'multi'
  | 'baseball'
  | 'basketball'
  | 'volleyball';

export const SPORT_LABEL: Record<SportType, string> = {
  tennis: 'テニス',
  soccer: 'サッカー',
  futsal: 'フットサル',
  rugby: 'ラグビー',
  multi: '多目的',
  baseball: '野球',
  basketball: 'バスケットボール',
  volleyball: 'バレーボール',
};

export type SurfaceType =
  | '砂入り人工芝'
  | '人工芝'
  | '天然芝'
  | 'クレー'
  | 'ハード'
  | '全天候型舗装'
  | '土'
  | '体育館床'
  | '要確認';

export type IndoorOutdoor = '屋内' | '屋外' | '屋根付き' | '要確認';

export type BookingMethod = 'Web' | '電話' | '窓口' | '予約不要' | '複合' | '要確認';

export type DataConfidence = 'A' | 'B' | 'C';

export type Facility = {
  id: string;
  facility_code: string;
  facility_name: string;
  official_name: string | null;
  municipality: string;
  address: string | null;
  latitude: number | null;
  longitude: number | null;
  indoor_outdoor: IndoorOutdoor | null;
  surface_type: SurfaceType | null;
  court_count: number | null;
  lighting_available: boolean | null;
  operating_hours: string | null;
  closed_days: string | null;
  parking: string | null;
  changing_shower: string | null;
  fee_text: string | null;
  fee_structure: Record<string, unknown> | null;
  booking_method: BookingMethod | null;
  registration_required: string | null;
  nonresident_policy: string | null;
  same_day_booking: string | null;
  phone_number: string | null;
  official_url: string | null;
  reservation_url: string | null;
  availability_url: string | null;
  data_confidence: DataConfidence;
  last_verified_at: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type FacilitySport = {
  facility_id: string;
  sport: SportType;
};

export type FacilityWithSports = Facility & {
  sports: SportType[];
};

// 空き状況 (availability_current テーブル対応)
export type AvailabilityStatus = '空き' | '一部空き' | '満' | '不明' | '休館';

export const AVAILABILITY_LABEL: Record<AvailabilityStatus, string> = {
  '空き': '空き',
  '一部空き': '一部空き',
  '満': '満',
  '不明': '未取得',
  '休館': '休館',
};

export type AvailabilitySlot = {
  id: number;
  facility_id: string;
  court_name: string;        // 設備(コート)名。単一コート/非対応施設は ''
  target_date: string;       // YYYY-MM-DD
  start_time: string;        // HH:MM:SS
  end_time: string;          // HH:MM:SS
  availability_status: AvailabilityStatus;
  available_court_count: number | null;
  total_court_count: number | null;
  fee_min_yen: number | null;
  fee_max_yen: number | null;
  source: 'scrape' | 'manual' | 'api';
  last_checked_at: string;
};

// 検索フィルタ
export type SearchFilters = {
  sport?: SportType;
  surface?: SurfaceType;
  lighting?: boolean;
  indoor?: boolean;
  municipality?: string;
  free?: boolean;
  q?: string; // 施設名のあいまい検索 (例: "城山")
};
