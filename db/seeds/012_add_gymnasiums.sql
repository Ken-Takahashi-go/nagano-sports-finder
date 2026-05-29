-- =====================================================================
-- Seed: 主要体育館・屋内運動場 11施設を追加
-- Date: 2026-05-28
-- 内訳:
--   - 大型運動公園内体育館 3施設 (長野メイン/サブ、南長野)
--   - 真島総合スポーツアリーナ 1施設
--   - 屋内運動場 7施設 (茶臼山、豊野、戸隠、鬼無里、大岡、中条、サンマリーン)
--   ※ 北部スポーツ・レクリエーションパーク屋内 (machikagi=35) は
--     既に NAG-SOC-003 として登録済なので追加しない
-- 注: 詳細属性(住所/料金等)は未取得。data_confidence=C で「要追加調査」
-- =====================================================================

begin;

insert into facilities (
  facility_code, facility_name, municipality,
  indoor_outdoor, machikagi_facility_id,
  booking_method, registration_required, nonresident_policy, same_day_booking,
  reservation_url, phone_number,
  data_confidence, last_verified_at, notes
) values
-- 1-XX: 大型運動公園内体育館
('NAG-GYM-001', '長野運動公園総合体育館メインアリーナ', '長野市',
 '屋内', 42, '複合', '要確認', '要確認', '要確認',
 'https://city.nagano.nagano.machikagi-remote.jp/', '026-241-4200',
 'C', '2026-05-28',
 '長野運動公園内のメインアリーナ。バドミントン・バレー・バスケ・フットサル等の多目的利用想定。詳細属性は公式確認要'),

('NAG-GYM-002', '長野運動公園総合体育館サブアリーナ', '長野市',
 '屋内', 92, '複合', '要確認', '要確認', '要確認',
 'https://city.nagano.nagano.machikagi-remote.jp/', '026-241-4200',
 'C', '2026-05-28',
 '長野運動公園内のサブアリーナ。多目的利用想定。詳細属性は公式確認要'),

('NAG-GYM-003', '南長野運動公園総合体育館', '長野市',
 '屋内', 43, '複合', '要確認', '要確認', '要確認',
 'https://city.nagano.nagano.machikagi-remote.jp/', '026-293-4818',
 'C', '2026-05-28',
 '南長野運動公園内の総合体育館。多目的利用想定。詳細属性は公式確認要'),

-- 真島
('NAG-GYM-004', '真島総合スポーツアリーナ サブアリーナ', '長野市',
 '屋内', 94, '複合', '要確認', '要確認', '要確認',
 'https://city.nagano.nagano.machikagi-remote.jp/', '026-283-7977',
 'C', '2026-05-28',
 '真島地区の総合スポーツアリーナ サブアリーナ。詳細属性は公式確認要'),

-- 4-XX: 屋内運動場 (北部スポレクは既登録のため除外)
('NAG-GYM-005', '茶臼山屋内運動場', '長野市',
 '屋内', 41, '複合', '要確認', '要確認', '要確認',
 'https://city.nagano.nagano.machikagi-remote.jp/', '026-292-5443',
 'C', '2026-05-28',
 '茶臼山スポーツ施設管理棟管理。屋内多目的運動場。詳細属性は公式確認要'),

('NAG-GYM-006', '豊野屋内運動場', '長野市',
 '屋内', 40, '複合', '要確認', '要確認', '要確認',
 'https://city.nagano.nagano.machikagi-remote.jp/', '026-224-5083',
 'C', '2026-05-28',
 '豊野地区の屋内運動場。詳細属性は公式確認要'),

('NAG-GYM-007', '戸隠屋内運動場', '長野市',
 '屋内', 39, '複合', '要確認', '要確認', '要確認',
 'https://city.nagano.nagano.machikagi-remote.jp/', '026-224-5083',
 'C', '2026-05-28',
 '戸隠地区の屋内運動場。詳細属性は公式確認要'),

('NAG-GYM-008', '鬼無里屋内運動場', '長野市',
 '屋内', 38, '複合', '要確認', '要確認', '要確認',
 'https://city.nagano.nagano.machikagi-remote.jp/', '026-224-5083',
 'C', '2026-05-28',
 '鬼無里地区の屋内運動場。中山間地。詳細属性は公式確認要'),

('NAG-GYM-009', '大岡屋内運動場', '長野市',
 '屋内', 37, '複合', '要確認', '要確認', '要確認',
 'https://city.nagano.nagano.machikagi-remote.jp/', '026-224-5083',
 'C', '2026-05-28',
 '大岡地区の屋内運動場。詳細属性は公式確認要'),

('NAG-GYM-010', '中条屋内運動場', '長野市',
 '屋内', 36, '複合', '要確認', '要確認', '要確認',
 'https://city.nagano.nagano.machikagi-remote.jp/', '026-224-5083',
 'C', '2026-05-28',
 '中条地区の屋内運動場。詳細属性は公式確認要'),

('NAG-GYM-011', 'サンマリーンながの屋内運動場', '長野市',
 '屋内', 34, '複合', '要確認', '要確認', '要確認',
 'https://city.nagano.nagano.machikagi-remote.jp/', '026-224-5083',
 'C', '2026-05-28',
 'サンマリーンながの併設の屋内運動場。詳細属性は公式確認要');

-- =================================================================
-- facility_sports タグ付け
-- =================================================================
-- 主要4施設 (メインアリーナ・サブアリーナ・南長野体育館・真島サブ):
--   futsal + basketball + volleyball + multi
-- 屋内運動場 7施設: futsal + multi (体育館より単純な多目的フロア想定)
-- =================================================================

-- 主要4施設のタグ
insert into facility_sports (facility_id, sport)
select id, s from facilities
cross join unnest(array['futsal', 'basketball', 'volleyball', 'multi']) as s
where facility_code in ('NAG-GYM-001','NAG-GYM-002','NAG-GYM-003','NAG-GYM-004')
on conflict do nothing;

-- 屋内運動場7施設のタグ
insert into facility_sports (facility_id, sport)
select id, s from facilities
cross join unnest(array['futsal', 'multi']) as s
where facility_code in (
  'NAG-GYM-005','NAG-GYM-006','NAG-GYM-007',
  'NAG-GYM-008','NAG-GYM-009','NAG-GYM-010','NAG-GYM-011'
)
on conflict do nothing;

commit;

-- =================================================================
-- 確認クエリ
-- =================================================================
-- 全施設数 (32→43に増えるはず)
-- select count(*) from facilities where municipality = '長野市';

-- 新規追加体育館のタグ確認
-- select f.facility_code, f.facility_name, array_agg(fs.sport order by fs.sport) as sports
-- from facilities f
-- join facility_sports fs on fs.facility_id = f.id
-- where f.facility_code like 'NAG-GYM-%'
-- group by f.facility_code, f.facility_name
-- order by f.facility_code;

-- フットサル可能施設一覧 (大幅に増えるはず)
-- select f.facility_code, f.facility_name from facilities f
-- join facility_sports fs on fs.facility_id = f.id
-- where fs.sport = 'futsal' order by f.facility_code;
