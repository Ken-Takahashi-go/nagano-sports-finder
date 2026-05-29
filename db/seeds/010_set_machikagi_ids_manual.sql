-- =====================================================================
-- Seed: machikagi_facility_id を手動確定版で設定
-- Date: 2026-05-23
-- 経緯: stage1_5 の自動マッチで誤マッチが多かったため、
--       inspect_machikagi.py の出力を見ながら人間が手動確定
-- 前提: migration 004 (machikagi_facility_id カラム追加) 適用済
-- =====================================================================

begin;

-- ===== テニス専用ID (5-XX シリーズ) =====
update facilities set machikagi_facility_id = 77 where facility_code = 'NAG-TEN-002';  -- 5-08 古里
update facilities set machikagi_facility_id = 72 where facility_code = 'NAG-TEN-003';  -- 5-03 緑ヶ丘 (字違い)
update facilities set machikagi_facility_id = 44 where facility_code = 'NAG-TEN-004';  -- 5-04 大豆島
update facilities set machikagi_facility_id = 78 where facility_code = 'NAG-TEN-005';  -- 5-09 昭和の森公園
update facilities set machikagi_facility_id = 89 where facility_code = 'NAG-TEN-006';  -- 5-06 篠ノ井
update facilities set machikagi_facility_id = 76 where facility_code = 'NAG-TEN-007';  -- 5-07 川柳
update facilities set machikagi_facility_id = 73 where facility_code = 'NAG-TEN-009';  -- 5-05 御厨
update facilities set machikagi_facility_id = 79 where facility_code = 'NAG-TEN-010';  -- 5-10 豊野
update facilities set machikagi_facility_id = 80 where facility_code = 'NAG-TEN-011';  -- 5-11 鬼無里
update facilities set machikagi_facility_id = 71 where facility_code = 'NAG-TEN-013';  -- 5-02 茶臼山
update facilities set machikagi_facility_id = 88 where facility_code = 'NAG-TEN-015';  -- 5-01 真島

-- ===== 大型運動公園 (1-XX シリーズ) =====
update facilities set machikagi_facility_id = 75 where facility_code = 'NAG-TEN-018';  -- 1-04 長野運動公園テニス
update facilities set machikagi_facility_id = 84 where facility_code = 'NAG-TEN-019';  -- 1-07 南長野運動公園テニス
update facilities set machikagi_facility_id = 85 where facility_code = 'NAG-SOC-002';  -- 1-08 オリンピックスタジアム (要確認: 球技場として運用されているか)
update facilities set machikagi_facility_id = 86 where facility_code = 'NAG-SOC-001';  -- 1-09 長野Uスタジアム

-- ===== 多目的運動場 (3-XX シリーズ) — テニス・サッカー共通敷地 =====
update facilities set machikagi_facility_id = 30 where facility_code = 'NAG-TEN-020';  -- 3-01 犀川第一運動場(テニス)
update facilities set machikagi_facility_id = 30 where facility_code = 'NAG-SOC-006';  -- 3-01 犀川第一運動場(サッカー)
update facilities set machikagi_facility_id = 31 where facility_code = 'NAG-TEN-021';  -- 3-02 犀川第二運動場(テニス)
update facilities set machikagi_facility_id = 31 where facility_code = 'NAG-SOC-007';  -- 3-02 犀川第二運動場(サッカー)
update facilities set machikagi_facility_id = 62 where facility_code = 'NAG-TEN-022';  -- 3-11 犀川南運動場(テニス)
update facilities set machikagi_facility_id = 62 where facility_code = 'NAG-SOC-008';  -- 3-11 犀川南運動場(サッカー)
update facilities set machikagi_facility_id = 60 where facility_code = 'NAG-TEN-024';  -- 3-13 七二会運動場
update facilities set machikagi_facility_id = 56 where facility_code = 'NAG-TEN-023';  -- 3-17 西寺尾運動場
update facilities set machikagi_facility_id = 47 where facility_code = 'NAG-TEN-008';  -- 3-26 若穂中央公園運動場
update facilities set machikagi_facility_id = 46 where facility_code = 'NAG-TEN-014';  -- 3-27 青垣公園運動場

-- ===== その他 =====
update facilities set machikagi_facility_id = 35 where facility_code = 'NAG-SOC-003';  -- 4-07 北部スポーツ・レクリエーションパーク屋内
update facilities set machikagi_facility_id = 102 where facility_code = 'NAG-SOC-005'; -- 3-29 飯綱高原南

-- ===== machikagi未登録 (NULL のまま) =====
-- NAG-TEN-001 城山      — 予約不要施設 (現地受付)
-- NAG-TEN-012 西和田    — machikagiリスト未確認 (要追加調査)
-- NAG-TEN-016 三輪      — 予約不要 (常時開放/受付簿)
-- NAG-TEN-017 小松原    — 予約不要 (自由使用)
-- NAG-SOC-009 千曲川リバーフロント — 観光協会管理(要追加調査)

commit;

-- 確認クエリ
-- select count(*) filter (where machikagi_facility_id is not null) as matched,
--        count(*) filter (where machikagi_facility_id is null) as unmatched
-- from facilities;
-- 期待: matched=27, unmatched=5
