-- =====================================================================
-- Seed: NAG-SOC-001 の住所文字化け修正
-- Date: 2026-05-23
-- 問題: seed 004 の Write 時に "ノ" が U+FFFD (置換文字) に化けていた
--      "長野市篠�井東福寺320" → "長野市篠ノ井東福寺320"
-- =====================================================================

begin;

update facilities set
  address = '長野市篠ノ井東福寺320'
where facility_code = 'NAG-SOC-001';

commit;

-- 確認
-- select facility_code, address from facilities where facility_code = 'NAG-SOC-001';
-- 期待: 長野市篠ノ井東福寺320 (「ノ」が正しく表示される)
