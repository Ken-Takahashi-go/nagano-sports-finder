-- =====================================================================
-- Seed: 既存テニス併設運動場 5施設に soccer/futsal/multi タグ追加
-- Date: 2026-05-28
-- 経緯:
--   machikagiリモートで「○○運動場」として登録 = 多目的利用可
--   これまでテニスタグのみ付与していたが、サッカー検索でもヒットすべき
-- =====================================================================

begin;

-- ===== NAG-TEN-008 若穂中央公園 =====
insert into facility_sports (facility_id, sport)
select id, s from facilities
cross join unnest(array['soccer', 'futsal', 'multi']) as s
where facility_code = 'NAG-TEN-008'
on conflict do nothing;

-- ===== NAG-TEN-014 青垣公園 =====
insert into facility_sports (facility_id, sport)
select id, s from facilities
cross join unnest(array['soccer', 'multi']) as s
where facility_code = 'NAG-TEN-014'
on conflict do nothing;

-- ===== NAG-TEN-017 小松原運動場 =====
insert into facility_sports (facility_id, sport)
select id, s from facilities
cross join unnest(array['soccer', 'multi']) as s
where facility_code = 'NAG-TEN-017'
on conflict do nothing;

-- ===== NAG-TEN-023 西寺尾運動場 =====
insert into facility_sports (facility_id, sport)
select id, s from facilities
cross join unnest(array['soccer', 'baseball', 'multi']) as s
where facility_code = 'NAG-TEN-023'
on conflict do nothing;

-- ===== NAG-TEN-024 七二会運動場 =====
insert into facility_sports (facility_id, sport)
select id, s from facilities
cross join unnest(array['soccer', 'multi']) as s
where facility_code = 'NAG-TEN-024'
on conflict do nothing;

commit;

-- 確認
-- select f.facility_code, f.facility_name, array_agg(fs.sport order by fs.sport) as sports
-- from facilities f
-- join facility_sports fs on fs.facility_id = f.id
-- where f.facility_code in ('NAG-TEN-008','NAG-TEN-014','NAG-TEN-017','NAG-TEN-023','NAG-TEN-024')
-- group by f.facility_code, f.facility_name
-- order by f.facility_code;
