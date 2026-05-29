-- =====================================================================
-- Seed: 優先度A施設の詳細属性（11件）を反映
-- Date: 2026-05-23
-- Source: 長野市公式個別ページ (p003058〜p003066, p003009, p003010, p003100)
-- 前提: migration 002 (surface_type に全天候型舗装を追加) が適用済
-- =====================================================================

begin;

-- ===== NAG-TEN-001 城山 =====
update facilities set
  court_count = 3,
  surface_type = '砂入り人工芝',
  lighting_available = true,
  operating_hours = '夏季(5-9月) 6:30-21:00 / 春秋(4,10-11月) 8:30-21:00 / 冬季(1-3,12月) 8:30-17:00',
  phone_number = '026-235-5144',
  notes = '城山公園内。砂入り人工芝3面・ナイター可。料金PDF: /documents/3266/119446.pdf',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-001';

-- ===== NAG-TEN-002 古里 =====
update facilities set
  court_count = 2,
  surface_type = 'クレー',
  operating_hours = '夏季(5-9月) 6:30-日没 / 春秋(4,10-11月) 8:30-日没',
  closed_days = '冬季(12-3月)閉場の可能性あり・要確認',
  phone_number = '026-295-9707',
  notes = '古里公民館管理。クレーコート2面。料金PDF: /documents/3267/119446.pdf',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-002';

-- ===== NAG-TEN-003 緑ケ丘 =====
update facilities set
  court_count = 3,
  surface_type = '砂入り人工芝',
  operating_hours = '夏季(5-10月) 7:00-日没 / 冬季(1-4,11-12月) 8:30-日没',
  phone_number = '026-224-5083',
  notes = '砂入り人工芝3面。ナイター要確認。料金PDF: /documents/3268/119446.pdf',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-003';

-- ===== NAG-TEN-004 大豆島 =====
update facilities set
  court_count = 4,
  surface_type = '砂入り人工芝',
  operating_hours = '夏季(5-10月) 7:00-日没 / 冬季(1-4,11-12月) 8:30-日没',
  phone_number = '026-224-5083',
  notes = '砂入り人工芝4面。ナイター要確認。料金PDF: /documents/3269/119446.pdf',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-004';

-- ===== NAG-TEN-005 昭和の森 =====
update facilities set
  court_count = 2,
  surface_type = 'クレー',
  operating_hours = '4-11月 8:30-日没',
  closed_days = '冬季(12-3月)閉場の可能性大・要確認',
  phone_number = '026-295-3055',
  notes = '昭和の森公園内。クレー2面。予約取消連絡先=026-295-3055、スポーツ課=026-224-5083。料金PDF: /documents/3270/119446.pdf',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-005';

-- ===== NAG-TEN-006 篠ノ井 =====
update facilities set
  court_count = 3,
  surface_type = '全天候型舗装',
  operating_hours = '通年 8:30-日没',
  phone_number = '026-292-2121',
  notes = '篠ノ井交流センター管理。全天候型舗装3面。料金PDF: /documents/3271/119446.pdf',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-006';

-- ===== NAG-TEN-007 川柳 =====
update facilities set
  court_count = 3,
  surface_type = 'クレー',
  operating_hours = '4-11月 8:30-日没',
  closed_days = '冬季(12-3月)閉場の可能性大・要確認',
  phone_number = '026-292-2121',
  notes = '篠ノ井交流センター管理。クレー3面。料金PDF: /documents/3272/119446.pdf',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-007';

-- ===== NAG-TEN-009 御厨 =====
update facilities set
  court_count = 2,
  surface_type = '全天候型舗装',
  lighting_available = false,
  operating_hours = '夏季(5-9月) 6:30-日没 / 冬季(10-4月) 8:30-日没',
  phone_number = '026-224-5083',
  notes = '全天候型舗装2面。ナイターなし(日没まで)。料金PDF: /documents/3274/119446.pdf',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-009';

-- ===== NAG-TEN-018 長野運動公園総合運動場 (テニス10面) =====
update facilities set
  court_count = 10,
  surface_type = '砂入り人工芝',
  lighting_available = true,
  phone_number = '026-241-4200',
  notes = '長野運動公園内。砂入り人工芝10面・ナイター可。長野市の主力テニス施設の一つ。テニスコート管理事務所直通電話',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-018';

-- ===== NAG-TEN-019 南長野運動公園総合運動場 (テニス16面 ★主力) =====
update facilities set
  court_count = 16,
  surface_type = '砂入り人工芝',
  lighting_available = true,
  phone_number = '026-293-4818',
  notes = '南長野運動公園内。砂入り人工芝16面・ナイター可。長野市最大級のテニス施設。長野Uスタジアム併設',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-TEN-019';

-- ===== NAG-SOC-003 北部スポーツ・レクリエーションパーク屋内運動場 =====
update facilities set
  facility_name = '北部スポーツ・レクリエーションパーク屋内運動場',
  indoor_outdoor = '屋内',
  court_count = 4,            -- テニス換算で4面、フットサルなら2面
  surface_type = '砂入り人工芝',
  lighting_available = true,
  operating_hours = '通年 8:30-21:00',
  fee_text = '個人利用2時間1,220円〜 / 照明全面810円/h(半面400円/h)、テニスコート1面200円/h / 市民大会午前2,130円・午後3,050円 / 市外大会午前6,410円・午後9,160円',
  phone_number = '026-266-0582',
  address = '長野市大字三才1981-1',
  notes = '屋内多目的施設。テニス4面 / フットサル2面 / ゲートボール6面。長野県内では希少な屋内テニス施設',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-SOC-003';

-- ===== NAG-SOC-003 に tennis 競技も追加 =====
insert into facility_sports (facility_id, sport)
select id, 'tennis' from facilities where facility_code = 'NAG-SOC-003'
on conflict do nothing;

commit;

-- ----------------------------------------------------------
-- 確認クエリ
-- ----------------------------------------------------------
-- 反映確認: 優先度A施設の主要属性が埋まったか
-- select facility_code, facility_name, court_count, surface_type, lighting_available, phone_number, data_confidence
-- from facilities
-- where facility_code in (
--   'NAG-TEN-001','NAG-TEN-002','NAG-TEN-003','NAG-TEN-004','NAG-TEN-005',
--   'NAG-TEN-006','NAG-TEN-007','NAG-TEN-009','NAG-TEN-018','NAG-TEN-019',
--   'NAG-SOC-003'
-- ) order by facility_code;

-- ナイター可能なテニス施設(主要訴求ポイント)
-- select facility_code, facility_name, court_count, surface_type
-- from facilities f
-- join facility_sports fs on fs.facility_id = f.id
-- where fs.sport='tennis' and f.lighting_available=true
-- order by court_count desc;
