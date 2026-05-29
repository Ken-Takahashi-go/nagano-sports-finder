// =====================================================================
// DB クエリ関数集約
// 全ページから呼び出して使う
// =====================================================================
import { supabase } from './supabase';
import type {
  AvailabilitySlot,
  Facility,
  FacilityWithSports,
  SearchFilters,
  SportType,
} from './types';

/** 施設+対応競技 を取得 (検索用) */
export async function searchFacilities(
  filters: SearchFilters = {},
): Promise<FacilityWithSports[]> {
  let query = supabase
    .from('facilities')
    .select('*, facility_sports(sport)')
    .order('court_count', { ascending: false, nullsFirst: false });

  if (filters.municipality) {
    query = query.eq('municipality', filters.municipality);
  }
  if (filters.surface) {
    query = query.eq('surface_type', filters.surface);
  }
  if (filters.lighting !== undefined) {
    query = query.eq('lighting_available', filters.lighting);
  }
  if (filters.indoor) {
    query = query.eq('indoor_outdoor', '屋内');
  }
  if (filters.free) {
    query = query.eq('fee_text', '無料');
  }
  if (filters.q) {
    // 施設名のあいまい検索 (大文字小文字区別なし。% は ilike エスケープ)
    const escaped = filters.q.replace(/[%_]/g, (m) => `\\${m}`);
    query = query.ilike('facility_name', `%${escaped}%`);
  }

  const { data, error } = await query;
  if (error) throw error;

  let facilities = (data ?? []).map((row) => ({
    ...row,
    sports: (row.facility_sports as { sport: SportType }[]).map(
      (s) => s.sport,
    ),
  })) as FacilityWithSports[];

  // sport フィルタはクライアント側で適用 (Postgres配列含むため)
  if (filters.sport) {
    facilities = facilities.filter((f) => f.sports.includes(filters.sport!));
  }

  return facilities;
}

/** facility_code のリストから { code → 施設名 } のマップを取得 (notes内リンク用) */
export async function getFacilityNameLookup(
  codes: string[],
): Promise<Map<string, string>> {
  if (codes.length === 0) return new Map();
  const { data, error } = await supabase
    .from('facilities')
    .select('facility_code, facility_name')
    .in('facility_code', codes);
  if (error) throw error;
  return new Map((data ?? []).map((f) => [f.facility_code, f.facility_name]));
}

/** facility_code で単一施設取得 (詳細ページ用) */
export async function getFacilityByCode(
  code: string,
): Promise<FacilityWithSports | null> {
  const { data, error } = await supabase
    .from('facilities')
    .select('*, facility_sports(sport)')
    .eq('facility_code', code)
    .single();

  if (error) {
    if (error.code === 'PGRST116') return null; // not found
    throw error;
  }
  if (!data) return null;

  return {
    ...data,
    sports: (data.facility_sports as { sport: SportType }[]).map(
      (s) => s.sport,
    ),
  } as FacilityWithSports;
}

/** ナイター可能テニス施設 TOPページ訴求用 */
export async function getNightTennisFacilities(): Promise<FacilityWithSports[]> {
  return searchFacilities({ sport: 'tennis', lighting: true });
}

/**
 * 今夜(18:00以降)に空きがあるテニス施設一覧
 * TOPページで「今夜空きあり」訴求に使用
 */
export async function getTonightAvailableTennisFacilities(): Promise<
  Array<FacilityWithSports & { tonightSlots: AvailabilitySlot[] }>
> {
  const today = new Date().toISOString().slice(0, 10);

  // 今日18:00以降に空き or 一部空きのスロット
  const { data: slots, error } = await supabase
    .from('availability_current')
    .select('*')
    .eq('target_date', today)
    .gte('start_time', '18:00:00')
    .in('availability_status', ['空き', '一部空き'])
    .order('start_time', { ascending: true });

  if (error) throw error;
  if (!slots || slots.length === 0) return [];

  // facility_id ごとにグループ化
  const byFacility = new Map<string, AvailabilitySlot[]>();
  for (const slot of slots as AvailabilitySlot[]) {
    const list = byFacility.get(slot.facility_id) ?? [];
    list.push(slot);
    byFacility.set(slot.facility_id, list);
  }

  // 施設情報を取得
  const facilityIds = Array.from(byFacility.keys());
  const { data: facilities } = await supabase
    .from('facilities')
    .select('*, facility_sports(sport)')
    .in('id', facilityIds);

  if (!facilities) return [];

  // テニス対応のみフィルタ+結合
  return facilities
    .map((f) => ({
      ...f,
      sports: (f.facility_sports as { sport: SportType }[]).map((s) => s.sport),
      tonightSlots: byFacility.get(f.id) ?? [],
    }))
    .filter((f) => f.sports.includes('tennis')) as Array<
    FacilityWithSports & { tonightSlots: AvailabilitySlot[] }
  >;
}

/** 指定施設の空き状況 (今日以降30日分まで) */
export async function getAvailabilityByFacilityId(
  facilityId: string,
  daysAhead: number = 30,
): Promise<AvailabilitySlot[]> {
  const today = new Date().toISOString().slice(0, 10);
  const future = new Date();
  future.setDate(future.getDate() + daysAhead);
  const futureStr = future.toISOString().slice(0, 10);

  const { data, error } = await supabase
    .from('availability_current')
    .select('*')
    .eq('facility_id', facilityId)
    .gte('target_date', today)
    .lte('target_date', futureStr)
    .order('target_date', { ascending: true })
    .order('start_time', { ascending: true });

  if (error) throw error;
  return (data ?? []) as AvailabilitySlot[];
}

/** 施設統計 (TOPページ等で件数表示) */
export async function getStats(): Promise<{
  totalFacilities: number;
  totalCourts: number;
  nightTennisFacilities: number;
}> {
  const [total, tennis] = await Promise.all([
    supabase.from('facilities').select('court_count'),
    searchFacilities({ sport: 'tennis' }),
  ]);

  const totalCourts = (total.data ?? []).reduce(
    (sum, f) => sum + (f.court_count ?? 0),
    0,
  );
  const nightTennisFacilities = tennis.filter((f) => f.lighting_available).length;

  return {
    totalFacilities: total.data?.length ?? 0,
    totalCourts,
    nightTennisFacilities,
  };
}
