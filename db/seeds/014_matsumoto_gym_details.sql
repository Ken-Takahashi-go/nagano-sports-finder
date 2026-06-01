-- =====================================================================
-- Seed: 松本市 中山間地15体育館の詳細属性反映 + フットサル対応1施設追加
-- Date: 2026-05-29
-- 経緯:
--   seed 013 で簡易マスタ(data_confidence='C')として登録した15施設を
--   公式詳細ページからの取得情報で B 評価まで昇格
-- 重要発見:
--   - 島内体育館(MAT-GYM-015) もフットサル対応 → 松本のフットサル可は4施設に
--   - 梓川・波田は柔道/剣道場併設の大型施設
-- =====================================================================

begin;

-- MAT-GYM-011 内田体育館
update facilities set
  address = '松本市内田758-1',
  operating_hours = '8:30-21:00',
  closed_days = '通年無休',
  parking = 'あり',
  fee_text = '基本620円/h、照明260円/h、高校生以下/障がい者50%',
  notes = 'バスケ1面/バレー2面/バドミントン4面/テニス1面。AED設置・指定避難所。窓口/当日電話/インターネット予約。',
  data_confidence = 'B', last_verified_at = '2026-05-29'
where facility_code = 'MAT-GYM-011';

-- MAT-GYM-012 岡田体育館
update facilities set
  address = '松本市岡田町488-3',
  operating_hours = '8:30-21:00',
  closed_days = '通年無休',
  parking = 'あり',
  fee_text = '基本620円/h、照明260円/h、高校生以下/障がい者50%',
  notes = 'バスケ1面/バレー2面/バドミントン4面/テニス1面/卓球2台。窓口/当日電話/インターネット予約。',
  data_confidence = 'B', last_verified_at = '2026-05-29'
where facility_code = 'MAT-GYM-012';

-- MAT-GYM-013 神林体育館
update facilities set
  address = '松本市神林1558',
  operating_hours = '8:30-21:00',
  closed_days = '通年無休',
  parking = 'あり',
  fee_text = '基本620円/h、照明260円/h、高校生以下/障がい者50%',
  notes = 'バスケ1面/バレー2面/バドミントン4面/卓球1台。テニス非対応。',
  data_confidence = 'B', last_verified_at = '2026-05-29'
where facility_code = 'MAT-GYM-013';

-- MAT-GYM-014 里山辺体育館
update facilities set
  address = '松本市里山辺2920-3',
  operating_hours = '8:30-21:00',
  closed_days = '通年無休',
  parking = 'あり',
  fee_text = '基本680円/h、照明310円/h、高校生以下/障がい者50%',
  notes = 'バスケ1面/バレー2面/バドミントン4面/テニス2面/卓球。ボール/ラケット類は持参必要。',
  data_confidence = 'B', last_verified_at = '2026-05-29'
where facility_code = 'MAT-GYM-014';

-- MAT-GYM-015 島内体育館 (★フットサル対応)
update facilities set
  address = '松本市島内1666-700',
  operating_hours = '8:30-21:00',
  closed_days = '通年無休',
  parking = 'あり',
  fee_text = '基本680円/h、照明260円/h、高校生以下/障がい者50%',
  notes = 'バスケ1面/バレー2面/バドミントン4面/**フットサル1面**/テニス1面。フットサル明示対応。',
  data_confidence = 'B', last_verified_at = '2026-05-29'
where facility_code = 'MAT-GYM-015';

-- MAT-GYM-016 島立体育館
update facilities set
  address = '松本市島立3298-2',
  operating_hours = '8:30-21:00',
  closed_days = '通年無休',
  parking = 'あり',
  fee_text = '基本620円/h、照明260円/h、高校生以下/障がい者50%',
  notes = 'バスケ1面/バレー2面/バドミントン6面/テニス1面/卓球2台。AED・指定避難所。',
  data_confidence = 'B', last_verified_at = '2026-05-29'
where facility_code = 'MAT-GYM-016';

-- MAT-GYM-017 芳川体育館
update facilities set
  address = '松本市野溝東2-10-1',
  operating_hours = '8:30-21:00',
  closed_days = '通年無休',
  parking = 'あり',
  fee_text = '基本620円/h、照明260円/h、高校生以下/障がい者50%',
  notes = 'バスケ1面/バレー2面/バドミントン4面/テニス1面/卓球。',
  data_confidence = 'B', last_verified_at = '2026-05-29'
where facility_code = 'MAT-GYM-017';

-- MAT-GYM-018 臨空工業団地体育館
update facilities set
  address = '松本市和田4010-26',
  operating_hours = '8:30-21:00',
  closed_days = '通年無休',
  parking = 'あり',
  fee_text = '基本620円/h、照明260円/h、高校生以下/障がい者50%',
  notes = 'バスケ1面/バレー2面/バドミントン4面。テニス非対応。',
  data_confidence = 'B', last_verified_at = '2026-05-29'
where facility_code = 'MAT-GYM-018';

-- MAT-GYM-019 梓川体育館 (★大型・柔道/剣道場併設)
update facilities set
  address = '松本市梓川梓816',
  operating_hours = '9:00-22:00',
  closed_days = '通年無休',
  parking = 'あり',
  fee_text = 'アリーナ全面940円/h・半面470円/h、柔道/剣道場340円/h、照明520円/260円、50%割引',
  notes = 'バスケ2面/バレー2面/バドミントン6面/テニス1面/卓球18台+3台/柔道1面/剣道1面。中山間地大型施設。',
  data_confidence = 'B', last_verified_at = '2026-05-29'
where facility_code = 'MAT-GYM-019';

-- MAT-GYM-020 安曇体育館
update facilities set
  address = '松本市安曇2742',
  operating_hours = '9:00-22:00',
  closed_days = '通年無休',
  fee_text = '全面780円/h・半面390円/h、照明260円/h、50%割引',
  notes = 'バスケ1面/バレー2面/バドミントン3面/卓球5台。山岳地域(乗鞍/上高地周辺)。',
  data_confidence = 'B', last_verified_at = '2026-05-29'
where facility_code = 'MAT-GYM-020';

-- MAT-GYM-021 乗鞍体育館
update facilities set
  address = '松本市安曇4017-4',
  operating_hours = '9:00-22:00',
  closed_days = '通年無休',
  fee_text = '全面780円/h・半面390円/h、照明260円(全)/130円(半)、50%割引',
  phone_number = '0263-93-2613',
  notes = 'バスケ2面/バレー2面/バドミントン3面/卓球6台。高嶺荘で予約。山岳リゾート地。',
  data_confidence = 'B', last_verified_at = '2026-05-29'
where facility_code = 'MAT-GYM-021';

-- MAT-GYM-022 奈川寄合渡体育館
update facilities set
  address = '松本市奈川980',
  operating_hours = '9:00-22:00',
  closed_days = '通年無休',
  fee_text = '全面520円/h、会議室200円/h、照明150円/h、50%割引',
  phone_number = '0263-79-2121',
  notes = 'バスケ1面/バレー2面/バドミントン2面。奈川地域づくりセンター予約。中山間地。',
  data_confidence = 'B', last_verified_at = '2026-05-29'
where facility_code = 'MAT-GYM-022';

-- MAT-GYM-023 奈川木曽路原体育館
update facilities set
  address = '松本市奈川1044-16',
  operating_hours = '9:00-22:00',
  closed_days = '通年無休',
  fee_text = '全面780円/h・半面390円/h、照明260円/130円、50%割引',
  phone_number = '0263-79-2121',
  notes = 'バスケ1面/バレー2面/バドミントン6面。奈川地域づくりセンター予約。中山間地。',
  data_confidence = 'B', last_verified_at = '2026-05-29'
where facility_code = 'MAT-GYM-023';

-- MAT-GYM-024 四賀体育館
update facilities set
  address = '松本市会田694',
  operating_hours = '9:00-22:00',
  closed_days = '通年無休',
  parking = 'あり',
  fee_text = '全面940円/h・半面470円/h、照明310円/150円、50%割引',
  notes = 'バスケ2面/バレー2面/バドミントン6面/テニス1面。窓口/インターネット予約。',
  data_confidence = 'B', last_verified_at = '2026-05-29'
where facility_code = 'MAT-GYM-024';

-- MAT-GYM-025 波田体育館 (★大型・剣道/柔道室併設)
update facilities set
  address = '松本市波田10098-1',
  operating_hours = '9:00-22:00',
  closed_days = '通年無休',
  parking = 'あり',
  fee_text = 'アリーナ全面940円/h・半面470円/h、剣道場520円/h、50%割引',
  notes = 'バスケ2面/バレー2面/バドミントン8面/剣道場/柔道室/卓球室/身障者老人体育室/研修室。波田地区の大型多目的施設。',
  data_confidence = 'B', last_verified_at = '2026-05-29'
where facility_code = 'MAT-GYM-025';

-- ===== facility_sports タグ追加 =====

-- 島内体育館(MAT-GYM-015): フットサル明示対応 → futsal タグ追加
insert into facility_sports (facility_id, sport)
select id, 'futsal' from facilities where facility_code = 'MAT-GYM-015'
on conflict do nothing;

-- テニス対応体育館にtennisタグ追加 (新規判明: 内田/岡田/里山辺/島内/島立/芳川/梓川/四賀)
insert into facility_sports (facility_id, sport)
select id, 'tennis' from facilities
where facility_code in (
  'MAT-GYM-011','MAT-GYM-012','MAT-GYM-014','MAT-GYM-015',
  'MAT-GYM-016','MAT-GYM-017','MAT-GYM-019','MAT-GYM-024'
)
on conflict do nothing;

commit;

-- 確認
-- select data_confidence, count(*) from facilities where municipality='松本市' group by data_confidence;
-- 期待: B=37 (全件昇格)

-- select count(*) from facility_sports fs
-- join facilities f on f.id=fs.facility_id
-- where f.municipality='松本市' and fs.sport='futsal';
-- 期待: 5 (波田扇子田/かりがね/エアウォ/庄内/芝沢/島内 ← 6になる場合あり)
