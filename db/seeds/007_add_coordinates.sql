-- =====================================================================
-- Seed: 緯度経度を追加 (判明している施設のみ)
-- Date: 2026-05-23
-- 取得方法: NAVITIME, Wikipedia, 公式ホームページ
-- 注: Phase 2 で Google Geocoding API 等で残り全件を一括処理予定
-- =====================================================================

begin;

-- NAG-TEN-019 / NAG-SOC-001 南長野運動公園 (長野Uスタジアム)
-- 出典: NAVITIME / Wikipedia
update facilities set latitude = 36.579937, longitude = 138.169914
where facility_code in ('NAG-TEN-019', 'NAG-SOC-001');

-- NAG-SOC-003 北部スポーツ・レクリエーションパーク (三才1981-1)
-- 出典: NAVITIME / Yahoo!マップ
update facilities set latitude = 36.689042, longitude = 138.243953
where facility_code = 'NAG-SOC-003';

commit;

-- 確認
-- select facility_code, facility_name, latitude, longitude
-- from facilities
-- where latitude is not null
-- order by facility_code;
