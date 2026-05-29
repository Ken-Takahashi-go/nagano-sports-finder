-- =====================================================================
-- Seed: 千曲川リバーフロントスポーツガーデン 新規追加 + NAG-SOC-001 誤情報修正
-- Date: 2026-05-23
-- 重要修正:
--   - フットボール場5面構成(A〜E)情報は実は千曲川リバーフロントの情報だった
--   - 南長野運動公園球技場(NAG-SOC-001)は長野Uスタジアム=1球技場のみ
-- 前提: migration 003 (rugby を sport enum に追加) が適用済
-- =====================================================================

begin;

-- =================================================================
-- 1. NAG-SOC-001 南長野運動公園球技場(長野Uスタジアム) を正確な情報に修正
--    (フットボール場5面の情報を削除、Uスタジアム1面に修正)
-- =================================================================
update facilities set
  facility_name = '南長野運動公園球技場(長野Uスタジアム)',
  address = '長野市篠ノ井東福寺320',
  court_count = 1,  -- Uスタジアム1面 (5面構成情報は千曲川リバーフロントの誤情報だった)
  surface_type = '天然芝',  -- 球技専用スタジアム=天然芝
  lighting_available = true,
  parking = 'あり(874台)',
  phone_number = '026-293-4818',
  notes = '長野Uスタジアム。J3 AC長野パルセイロのホームスタジアム。FIFA基準準拠の球技専用スタジアム、収容15,491人。天然芝1面。長野IC車5分。国スポ女子サッカー会場。なお(仮称)南長野運動公園フットボール場(天然芝1+人工芝2の計3面)は2028年供用開始予定で別事業。',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-SOC-001';

-- =================================================================
-- 2. NAG-SOC-009 千曲川リバーフロントスポーツガーデン 新規追加
--    (フットボール場5面構成の本当の主)
-- =================================================================
insert into facilities (
  facility_code, facility_name, municipality, address,
  indoor_outdoor, surface_type, court_count, lighting_available,
  operating_hours, closed_days, parking,
  booking_method, registration_required, nonresident_policy, same_day_booking,
  phone_number, official_url, reservation_url,
  data_confidence, last_verified_at, notes
) values (
  'NAG-SOC-009',
  '千曲川リバーフロントスポーツガーデン',
  '長野市',
  '長野市大字屋島3572',
  '屋外',
  '天然芝',
  5,  -- ラグビー兼用1面 + サッカー4面 = 計5面
  null,  -- ナイター情報未確認
  null,  -- 利用時間情報未確認
  '冬季(1-2月)閉場 / 営業期間: 3月-12月末',
  null,  -- 駐車場記載なし(現地確認要)
  '複合',
  '要確認',
  '要確認',
  '要確認',
  '026-259-5588',
  'https://www.city.nagano.nagano.jp/n155400/contents/p003039.html',
  'https://city.nagano.nagano.machikagi-remote.jp/',
  'B',
  '2026-05-23',
  '千曲川河川敷の大型スポーツ施設。フットボール場5面構成(A=ラグビー・フットボール兼用、B=東面川側、C=西面土手側、D=北面上流側、E=北面下流側)+多目的広場。スポーツ振興くじ(toto)助成で天然芝整備。AC長野パルセイロの公式練習場。運営公式: https://www.r-sportsgarden.com/'
);

-- =================================================================
-- 3. facility_sports に NAG-SOC-009 の競技を登録
-- =================================================================
insert into facility_sports (facility_id, sport)
select id, 'soccer' from facilities where facility_code = 'NAG-SOC-009';

insert into facility_sports (facility_id, sport)
select id, 'rugby' from facilities where facility_code = 'NAG-SOC-009';

insert into facility_sports (facility_id, sport)
select id, 'multi' from facilities where facility_code = 'NAG-SOC-009';

commit;

-- =================================================================
-- 確認クエリ
-- =================================================================

-- 全体件数
-- select municipality, count(*) from facilities group by municipality;
-- 期待: 長野市 | 32 (31 + 千曲川 1件)

-- 新規追加施設の確認
-- select facility_code, facility_name, court_count, surface_type, phone_number
-- from facilities where facility_code = 'NAG-SOC-009';

-- NAG-SOC-001 の修正確認 (court_count=1 になっているか)
-- select facility_code, facility_name, court_count, surface_type
-- from facilities where facility_code = 'NAG-SOC-001';

-- ラグビー対応施設
-- select f.facility_code, f.facility_name from facilities f
-- join facility_sports fs on fs.facility_id = f.id
-- where fs.sport = 'rugby';
