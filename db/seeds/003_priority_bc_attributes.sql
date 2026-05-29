-- =====================================================================
-- Seed: 優先度B/C施設の詳細属性 + データ修正
-- Date: 2026-05-23
-- Source: 長野市公式個別ページ各種
-- 重要変更:
--   1. NAG-SOC-004 若穂多目的広場 = 実はグライダー場 → 削除
--   2. NAG-SOC-005 飯綱高原南グラウンド = Jリーグキャンプ実績の本格サッカー場
--   3. ナイター施設追加: NAG-TEN-008(若穂中央公園), NAG-TEN-012(西和田)
-- 前提: migration 002 (全天候型舗装enum追加) が適用済
-- =====================================================================

begin;

-- =================================================================
-- 1. データ修正: NAG-SOC-004 はスポーツ施設ではないため削除
--    (若穂多目的広場 = 実態はグライダー場 / 長野グライダー協会管理)
-- =================================================================
delete from facility_sports where facility_id in (
  select id from facilities where facility_code = 'NAG-SOC-004'
);
delete from facilities where facility_code = 'NAG-SOC-004';

-- =================================================================
-- 2. 優先度B施設 (7件)
-- =================================================================

-- NAG-TEN-008 若穂中央公園 (★ナイター追加)
update facilities set
  court_count = 4,
  surface_type = '砂入り人工芝',
  lighting_available = true,
  operating_hours = '夏季(5-9月) 6:30-21:00 / 冬季(1-3,12月) 8:30-17:00',
  phone_number = '026-282-2095',
  notes = '若穂中央公園内。砂入り人工芝4面・ナイター可。料金PDF: /documents/3273/119446.pdf',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-008';

-- NAG-TEN-010 豊野
update facilities set
  court_count = 2,
  surface_type = 'クレー',
  lighting_available = false,
  operating_hours = '4-11月 8:30-18:00',
  closed_days = '冬季(12-3月)閉場',
  fee_text = '無料',
  phone_number = '026-224-5083',
  notes = '豊野町。クレー2面。夜間照明使用不可。利用無料',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-010';

-- NAG-TEN-012 西和田 (★ナイター追加)
update facilities set
  court_count = 4,
  surface_type = '砂入り人工芝',
  lighting_available = true,
  operating_hours = '夏季(5-9月) 6:30-21:00 / 冬季(1-3,12月) 8:30-17:00',
  address = '長野市大字西和田49-4',
  phone_number = '026-244-8667',
  notes = '砂入り人工芝4面・ナイター可。管理事務所直通電話',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-012';

-- NAG-TEN-013 茶臼山
update facilities set
  court_count = 3,
  surface_type = '砂入り人工芝',
  operating_hours = '通年 8:30-日没',
  phone_number = '026-292-5443',
  notes = '茶臼山スポーツ施設管理棟管理。砂入り人工芝3面。料金PDF: /documents/3279/119446.pdf',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-013';

-- NAG-TEN-014 青垣公園
update facilities set
  court_count = 1,  -- 表記は2面だが1面使用不可のため実質1面
  surface_type = 'クレー',
  operating_hours = '4-11月 8:30-日没',
  closed_days = '冬季(12-3月)閉場',
  fee_text = '無料',
  phone_number = '026-224-5083',
  notes = '松代町。クレー(表記は2面だが1面使用不可で実質1面)。利用無料',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-014';

-- NAG-TEN-015 真島
update facilities set
  court_count = 1,
  surface_type = '全天候型舗装',
  operating_hours = '8:30-日没',
  phone_number = '026-283-7977',
  notes = '真島総合スポーツアリーナ管理。全天候型舗装1面。料金PDF: /documents/3281/342106.pdf',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-015';

-- NAG-TEN-016 三輪
update facilities set
  court_count = 1,
  surface_type = 'クレー',
  operating_hours = '4-11月 8:30-日没',
  closed_days = '冬季(12-3月)閉場',
  parking = 'なし',
  fee_text = '無料',
  phone_number = '026-224-5083',
  notes = '三輪。クレー1面。駐車場なし。常時開放、利用受付簿に記入',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-016';

-- =================================================================
-- 3. 優先度C施設 (テニス系 7件 + サッカー系 4件)
-- =================================================================

-- NAG-TEN-011 鬼無里
update facilities set
  court_count = 2,
  surface_type = '砂入り人工芝',
  operating_hours = '4-11月 8:30-日没',
  closed_days = '冬季(12-3月)閉場',
  fee_text = '無料',
  phone_number = '026-224-5083',
  notes = '鬼無里。砂入り人工芝2面。中山間地・遠方。利用無料',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-011';

-- NAG-TEN-017 小松原
update facilities set
  court_count = 1,
  fee_text = '無料',
  phone_number = '026-224-5083',
  notes = '篠ノ井小松原。テニス1面。自由使用(受付なし・当日空き利用)。利用無料',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-017';

-- NAG-TEN-020 犀川第一運動場テニスコート
update facilities set
  court_count = 2,
  operating_hours = '日の出〜日没',
  fee_text = '無料',
  phone_number = '026-224-5083',
  notes = '犀川第一運動場内テニス2面。河川敷。受付なし・当日空き利用。利用無料。同敷地内にフットボール場1面、野球場4面、少年野球場1面、マレットゴルフ18ホールあり',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-020';

-- NAG-TEN-021 犀川第二運動場テニスコート
update facilities set
  court_count = 2,
  operating_hours = '日の出〜日没',
  closed_days = '冬期(12-3月)予約受付なし',
  fee_text = '無料',
  phone_number = '026-224-5083',
  notes = '犀川第二運動場内テニス2面。河川敷。受付なし・当日空き利用。同敷地内にフットボール場3面、野球5面、ソフトボール4面、少年野球2面、ゲートボール5面、馬場2面、マレットゴルフ36ホール等あり',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-021';

-- NAG-TEN-022 犀川南運動場テニスコート
update facilities set
  court_count = 3,
  operating_hours = '日の出〜日没',
  closed_days = '冬期(12-3月)予約受付なし',
  fee_text = '無料',
  phone_number = '026-224-5083',
  notes = '犀川南運動場内テニス3面。河川敷。受付なし・当日空き利用',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-022';

-- NAG-TEN-023 西寺尾運動場テニスコート
update facilities set
  court_count = 3,
  operating_hours = '日の出〜日没',
  closed_days = '冬期(12-3月)予約受付なし',
  fee_text = '無料',
  phone_number = '026-224-5083',
  notes = '西寺尾運動場内テニス3面。河川敷。同敷地内に野球場2面あり',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-023';

-- NAG-TEN-024 七二会運動場テニスコート
update facilities set
  court_count = 1,
  operating_hours = '日の出〜日没',
  fee_text = '無料',
  phone_number = '026-224-5083',
  notes = '七二会運動場内テニス1面',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-024';

-- =================================================================
-- 4. サッカー系C施設
-- =================================================================

-- NAG-SOC-005 飯綱高原南グラウンド (★Jリーグキャンプ実績の本格サッカー場)
update facilities set
  facility_name = '飯綱高原南グラウンド',
  address = '長野市大字上ケ屋2471-84',
  court_count = 1,  -- 大人サッカー1面分(少年なら2面相当)
  operating_hours = '8:00-17:00 (午前8:00-12:00 / 午後12:00-17:00 / 全日8:00-17:00)',
  parking = 'あり(利用時間内)',
  fee_text = '午前16,900円 / 午後20,000円 / 全日33,900円 (グラウンド+管理棟)',
  phone_number = '090-3143-2084',
  booking_method = '複合',
  notes = '飯綱高原観光協会管理。標高1000m超の高地。Jリーグ・いわきFC等プロチームのキャンプ実績あり。市内中心部から車25分。長野市予約システムまたは観光協会で予約',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-SOC-005';

-- NAG-SOC-006 犀川第一運動場(サッカー側)
update facilities set
  facility_name = '犀川第一運動場(フットボール場)',
  court_count = 1,
  operating_hours = '日の出〜日没',
  fee_text = '無料',
  phone_number = '026-224-5083',
  notes = '犀川第一運動場内フットボール場1面。河川敷。同敷地内にテニス2面、野球場4面、少年野球場1面、マレットゴルフ18ホールあり(TEN-020と同敷地)',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-SOC-006';

-- NAG-SOC-007 犀川第二運動場(サッカー側)
update facilities set
  facility_name = '犀川第二運動場(フットボール場)',
  court_count = 3,
  operating_hours = '日の出〜日没',
  closed_days = '冬期(12-3月)予約受付なし',
  fee_text = '無料',
  phone_number = '026-224-5083',
  notes = '犀川第二運動場内フットボール場3面。河川敷。長野市最大級の多目的運動場(TEN-021と同敷地)',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-SOC-007';

-- NAG-SOC-008 犀川南運動場(サッカー側)
update facilities set
  facility_name = '犀川南運動場',
  operating_hours = '日の出〜日没',
  closed_days = '冬期(12-3月)予約受付なし',
  fee_text = '無料',
  phone_number = '026-224-5083',
  notes = '犀川南運動場。河川敷。テニス3面とサッカー利用(TEN-022と同敷地)。サッカー面数は公式ページに明記なし',
  data_confidence = 'C',  -- サッカー面数不明のためCのまま
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-SOC-008';

commit;

-- =================================================================
-- 確認クエリ
-- =================================================================

-- 全体の埋まり方
-- select data_confidence, count(*) from facilities group by data_confidence;
-- 期待: B | 30, C | 1 (SOC-008のみ残る)

-- ★ナイター可能テニス施設(主要訴求)
-- select f.facility_code, f.facility_name, f.court_count, f.surface_type
-- from facilities f
-- join facility_sports fs on fs.facility_id = f.id
-- where fs.sport='tennis' and f.lighting_available=true
-- order by f.court_count desc;
-- 期待結果: 6件 (TEN-019:16面, TEN-018:10面, TEN-008:4, TEN-012:4, SOC-003:4, TEN-001:3)

-- 無料テニス施設一覧
-- select facility_code, facility_name, court_count, surface_type
-- from facilities f
-- join facility_sports fs on fs.facility_id = f.id
-- where fs.sport='tennis' and f.fee_text='無料'
-- order by facility_code;

-- サーフェス別集計
-- select surface_type, count(*) from facilities
-- join facility_sports fs on fs.facility_id = facilities.id
-- where fs.sport='tennis'
-- group by surface_type order by count(*) desc;
