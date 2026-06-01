-- =====================================================================
-- Seed: 松本市 37施設の初期データ投入
-- Date: 2026-05-29
-- 内訳:
--   テニス 10施設 (MAT-TEN-001 〜 MAT-TEN-010)
--   サッカー 2施設 (MAT-SOC-001, MAT-SOC-002)
--   体育館 25施設 (MAT-GYM-001 〜 MAT-GYM-025)
--      うち詳細あり 10、簡易マスタ(data_confidence=C) 15
-- 前提: migration 008 適用済 (external_system カラム存在)
-- 注: external_facility_id (webR内ID) は段階3スクレイパー実装時に紐付け
-- =====================================================================

begin;

-- =================================================================
-- テニス 10施設
-- =================================================================
insert into facilities (
  facility_code, facility_name, municipality, address,
  indoor_outdoor, surface_type, court_count, lighting_available,
  operating_hours, closed_days,
  fee_text,
  booking_method, registration_required, nonresident_policy, same_day_booking,
  phone_number, official_url, reservation_url,
  data_confidence, last_verified_at, notes,
  external_system
) values

('MAT-TEN-001', '沢村庭球場', '松本市', '松本市沢村2-1824-2',
 '屋外', '要確認', NULL, true,
 '8:30-日没 (シーズン券17時〜可)', '年末年始(12/29-1/3)',
 '個人100円/回、回数券1000円(12枚)、専用620円/h、シーズン券9900円(日中)/6600円(夕方)',
 '複合', '団体登録', '可', '可',
 '0263-35-0149', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5746.html',
 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'B', '2026-05-29', '夜間照明あり。窓口/当日電話/インターネット予約。',
 'matsumoto_webR'),

('MAT-TEN-002', '開智公園運動場(庭球場)', '松本市', '松本市開智2-4-12',
 '屋外', 'クレー', 4, false,
 '8:30-日没(早朝6:00-シーズン券)', '冬季(12-3月)閉場',
 '個人100円(大人)/50円(高校生以下)、専用520円/h、シーズン券6600円(日中)',
 '予約不要', '不要', '可', '可',
 '0263-35-0461', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5739.html',
 NULL,
 'B', '2026-05-29', '事前予約不可・当日券のみ。指定管理TOYBOX。開場4-11月。',
 NULL),  -- 予約不要なので external_system 不要

('MAT-TEN-003', '新村庭球場', '松本市', '松本市新村240-1',
 '屋外', 'クレー', 2, false,
 '8:30-日没(早朝6:00-シーズン券)', '第1・3木曜、年末年始、冬季(12-3月)閉場',
 '個人100円/h、専用520円/h〜',
 '予約不要', '不要', '可', '可',
 '0263-91-1211', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5743.html',
 NULL,
 'B', '2026-05-29', '事前予約不可・当日空き利用。開場4-11月。波田扇子田運動公園で利用券購入。',
 NULL),

('MAT-TEN-004', '浅間温泉庭球公園(オムニコート浅間温泉テニスパーク)', '松本市', '松本市浅間温泉1-9-2',
 '屋外', '砂入り人工芝', 20, true,
 '8:30-21:00(早朝6時-シーズン券)', '年末年始(12/29-1/3)',
 '個人100円(大人)/50円(高校生以下)、シーズン券6600-9900円',
 '複合', '団体登録', '可', '可',
 '0263-46-6398', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5738.html',
 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'B', '2026-05-29', '松本市最大20面のオムニコート。うち6面がナイター対応。',
 'matsumoto_webR'),

('MAT-TEN-005', '臨空工業団地庭球場', '松本市', '松本市和田3967-4',
 '屋外', '全天候型舗装', 4, false,
 '6:00-日没(個人は8:30-日没)', '通年無休',
 '個人100円(大人)/50円(高校生以下)、専用520円/h(大人)/200円/h(高校生以下)',
 '電話', '不要', '可', '可',
 '0263-48-0726', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5745.html',
 NULL,
 'B', '2026-05-29', '臨空工業団地管理組合(0263-48-0726)に問合せ予約。土日祝休。',
 NULL),

('MAT-TEN-006', '奈川木曽路原庭球場', '松本市', '松本市奈川1044-6',
 '屋外', '全天候型舗装', 6, false,
 '8:30-日没', '開場5-11月、奈川支所窓口は土日祝・年末年始休',
 '個人50-100円/回、専用200-520円/h',
 '電話', '不要', '可', '可',
 '0263-79-2121', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5741.html',
 NULL,
 'B', '2026-05-29', '奈川支所窓口予約。当日のみ電話可。中山間地。',
 NULL),

('MAT-TEN-007', '乗鞍テニスコート', '松本市', '松本市安曇4017-4',
 '屋外', '全天候型舗装', 4, false,
 '8:30-日没', '開場5-11月期間中無休',
 '個人100円(大人)/50円(高校生以下)、専用520円/h(大人)/200円/h(高校生以下)',
 '電話', '不要', '可', '不可',
 '0263-93-2613', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5744.html',
 NULL,
 'B', '2026-05-29', '高嶺荘で電話予約。当日キャンセル不可。山岳リゾート地。',
 NULL),

('MAT-TEN-008', '波田扇子田運動公園テニスコート', '松本市', '松本市波田230-1',
 '屋外', '砂入り人工芝', 5, true,
 '9:00-21:00', '第1・3木曜、年末年始',
 'テニス620円/h、屋内アリーナ全面1670円/h、運動広場260円/h',
 '複合', '団体登録', '可', '可',
 '0263-91-1211', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5709.html',
 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'B', '2026-05-29', '波田扇子田運動公園内テニス5面砂入り人工芝・ナイター付。屋内アリーナにテニス2面+フットサル1面+ゲートボール2面も併設(別レコードGYM-005参照)。',
 'matsumoto_webR'),

('MAT-TEN-009', '美須々屋内運動場', '松本市', '松本市美須々1-1',
 '屋内', '砂入り人工芝', 4, true,
 '6:00-21:00', '年末年始、第1・3月曜(整備日)',
 '個人150円/h(大人)/100円(高校生以下)、専用830-1670円/h、照明310円/h',
 '複合', '団体登録', '可', '可',
 '0263-34-0200', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5740.html',
 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'B', '2026-05-29', '屋内テニス4面砂入り人工芝。雨天可。エア・ウォーターアリーナ松本(美須々5-1)に隣接。',
 'matsumoto_webR'),

('MAT-TEN-010', '南部屋内運動場', '松本市', '松本市野溝東2-10-1',
 '屋内', '砂入り人工芝', 4, true,
 '6:00-21:00', '第2・4月曜(整備日)、年末年始',
 '個人150円(大人)/100円(高校生以下)、専用830-1670円/h、照明200-410円/h',
 '複合', '団体登録', '可', '可',
 '0263-57-8152', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5742.html',
 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'B', '2026-05-29', '屋内テニス4面砂入り人工芝。雨天可。',
 'matsumoto_webR');

-- =================================================================
-- サッカー 2施設
-- =================================================================
insert into facilities (
  facility_code, facility_name, municipality, address,
  indoor_outdoor, surface_type, court_count, lighting_available,
  operating_hours, closed_days,
  fee_text,
  booking_method, registration_required, nonresident_policy, same_day_booking,
  phone_number, official_url, reservation_url,
  data_confidence, last_verified_at, notes,
  external_system
) values
('MAT-SOC-001', '松本市サッカー場(今井)', '松本市', '松本市大字今井7037-7',
 '屋外', '天然芝', 1, true,
 '平日8:00-22:00、土日6:00-22:00', '年末年始',
 '全面3140円/h、半面1570円/h、照明料別途',
 '複合', '団体登録', '可', '可',
 '0263-57-5099', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5699.html',
 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'B', '2026-05-29', '天然芝1面(少年なら2面利用可)。LED 8基ナイター。あがた運動公園管理棟管理。',
 'matsumoto_webR'),

('MAT-SOC-002', '信州グリーンフィールドかりがね', '松本市', '松本市大字惣社325',
 '屋外', '人工芝', 5, true,
 '人工芝/多目的: 平日8:00-21:00 休日6:00-21:00 / 天然芝: 平日9-18 休日8-18', '年末年始',
 '料金PDF確認要',
 '複合', '団体登録', '可', '可',
 '0263-32-3230', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5703.html',
 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'B', '2026-05-29', 'AC長野パルセイロが利用するレベルの大型施設。天然芝1+人工芝1+少年人工芝2+フットサル1+ゲートボール1。人工芝コートLED6基、多目的広場LED照明。',
 'matsumoto_webR');

-- =================================================================
-- 体育館 25施設 (詳細あり10 + 簡易15)
-- =================================================================

-- ===== 詳細あり 10施設 =====
insert into facilities (
  facility_code, facility_name, municipality, address,
  indoor_outdoor, court_count,
  operating_hours, closed_days,
  fee_text,
  booking_method, registration_required, nonresident_policy, same_day_booking,
  phone_number, official_url, reservation_url,
  data_confidence, last_verified_at, notes,
  external_system
) values

('MAT-GYM-001', 'エア・ウォーターアリーナ松本(松本市総合体育館)', '松本市', '松本市美須々5-1',
 '屋内', NULL,
 '8:30-21:00', '火曜、年末年始(12/29-1/3)',
 '主アリーナ2460-7380円/h、高校生以下・障がい者50%割引',
 '複合', '団体登録', '可', '可',
 '0263-32-1818', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5722.html',
 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'B', '2026-05-29', '松本市最大の総合体育館。主アリーナ2535㎡(3,600-7,000人収容)、サブアリーナ1110㎡、トレーニング室2、会議室複数。バドミントン12面・バレー3面相当。フットサル・ハンドボール・柔道・空手・体操等多目的対応。Kissei文化ホール共用駐車場(大型車要予告)。',
 'matsumoto_webR'),

('MAT-GYM-002', '中央体育館', '松本市', '松本市中央1-23-2 Mウィング北棟8F',
 '屋内', NULL,
 '9:00-21:30', '第2・第4水曜',
 '680円/h、高校生以下・障がい者50%',
 '複合', '団体登録', '可', '可',
 '0263-34-1700', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5735.html',
 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'B', '2026-05-29', 'Mウィング8F屋上。バスケ1/バレー2/バドミントン4/テニス1/卓球6台。専用駐車場なし(Mウィング中央駐車場や近隣有料利用)。',
 'matsumoto_webR'),

('MAT-GYM-003', '本郷体育館', '松本市', '松本市浅間温泉1-40-10',
 '屋内', NULL,
 '8:30-21:00', '通年無休',
 '620円/h、照明260円/h、高校生以下・障がい者50%',
 '複合', '団体登録', '可', '可',
 '0263-34-1700', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5717.html',
 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'B', '2026-05-29', 'バスケ1/バレー2/バドミントン4/テニス1/卓球。駐車場あり。',
 'matsumoto_webR'),

('MAT-GYM-004', '今井体育館', '松本市', '松本市今井2231-1',
 '屋内', NULL,
 '8:30-21:00', '通年無休',
 '520円/h、照明150円/h、高校生以下・障がい者50%',
 '複合', '団体登録', '可', '可',
 '0263-34-1700', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5718.html',
 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'B', '2026-05-29', 'バスケ1/バレー1/バドミントン3。駐車場あり。AED設置・指定避難所。',
 'matsumoto_webR'),

('MAT-GYM-005', '南部体育館', '松本市', '松本市芳野4-1',
 '屋内', NULL,
 '8:30-21:00', '通年無休',
 '全面1110円/h、半面550円/h、照明全面520円/h、高校生以下・障がい者50%',
 '複合', '団体登録', '可', '可',
 '0263-34-1700', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5724.html',
 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'B', '2026-05-29', 'バスケ2/バレー2/バドミントン6/テニス2/卓球12台。駐車場あり(R7減少予定)。指定避難所。',
 'matsumoto_webR'),

('MAT-GYM-006', '庄内体育館', '松本市', '松本市出川1-5-9 ゆめひろば庄内3F',
 '屋内', NULL,
 '9:00-21:30', '不定休(月2回程度)、年末年始',
 '620円/h、照明260円/h、暖房2610円/h、高校生以下・障がい者50%',
 '複合', '団体登録', '可', '可',
 '0263-34-1700', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5734.html',
 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'B', '2026-05-29', 'バスケ1/バレー1/バドミントン3/**フットサル1**/テニス1/卓球3台。ゆめひろば庄内3F。フットサル明示対応。',
 'matsumoto_webR'),

('MAT-GYM-007', '寿体育館', '松本市', '松本市寿豊丘424',
 '屋内', NULL,
 '8:30-21:00', '通年無休',
 '620円/h、照明260円/h、高校生以下・障がい者50%',
 '複合', '団体登録', '可', '可',
 '0263-34-1700', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5721.html',
 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'B', '2026-05-29', 'バスケ1/バレー2/バドミントン3/テニス1/卓球2台。駐車場あり。',
 'matsumoto_webR'),

('MAT-GYM-008', '芝沢体育館', '松本市', '松本市和田1050-2',
 '屋内', NULL,
 '8:30-21:00', '通年無休',
 '680円/h、照明260円/h、高校生以下・障がい者50%',
 '複合', '団体登録', '可', '可',
 '0263-34-1700', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5731.html',
 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'B', '2026-05-29', 'バスケ1/バレー2/バドミントン4/**フットサル1**/卓球2台。和田出張所近く。フットサル明示対応。',
 'matsumoto_webR'),

('MAT-GYM-009', '鎌田体育館', '松本市', '松本市両島5-50',
 '屋内', NULL,
 '8:30-21:00', '通年無休',
 '620円/h、照明260円/h、高校生以下・障がい者50%',
 '複合', '団体登録', '可', '可',
 '0263-34-1700', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5729.html',
 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'B', '2026-05-29', '旧西部体育館。バスケ1/バレー2/バドミントン4/テニス1/卓球2台。駐車場あり。指定避難所。',
 'matsumoto_webR'),

('MAT-GYM-010', '寿台体育館', '松本市', '松本市寿台6-2-1',
 '屋内', NULL,
 '8:30-21:00', '通年無休',
 '620円/h、照明260円/h、高校生以下・障がい者50%',
 '複合', '団体登録', '可', '可',
 '0263-34-1700', 'https://www.city.matsumoto.nagano.jp/soshiki/239/5720.html',
 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'B', '2026-05-29', 'バスケ1/バレー2/バドミントン3/テニス1/卓球2台。駐車場あり。AED・指定避難所。',
 'matsumoto_webR');

-- ===== 簡易マスタ 15施設 (data_confidence='C' - 名称・URL・連絡先のみ) =====
insert into facilities (
  facility_code, facility_name, municipality,
  indoor_outdoor,
  booking_method,
  phone_number, official_url, reservation_url,
  data_confidence, last_verified_at, notes,
  external_system
) values
('MAT-GYM-011', '内田体育館', '松本市', '屋内', '複合', '0263-34-1700',
 'https://www.city.matsumoto.nagano.jp/soshiki/239/5736.html', 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'C', '2026-05-29', '詳細属性は公式ページで要確認', 'matsumoto_webR'),

('MAT-GYM-012', '岡田体育館', '松本市', '屋内', '複合', '0263-34-1700',
 'https://www.city.matsumoto.nagano.jp/soshiki/239/5726.html', 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'C', '2026-05-29', '詳細属性は公式ページで要確認', 'matsumoto_webR'),

('MAT-GYM-013', '神林体育館', '松本市', '屋内', '複合', '0263-34-1700',
 'https://www.city.matsumoto.nagano.jp/soshiki/239/5719.html', 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'C', '2026-05-29', '詳細属性は公式ページで要確認', 'matsumoto_webR'),

('MAT-GYM-014', '里山辺体育館', '松本市', '屋内', '複合', '0263-34-1700',
 'https://www.city.matsumoto.nagano.jp/soshiki/239/5728.html', 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'C', '2026-05-29', '詳細属性は公式ページで要確認', 'matsumoto_webR'),

('MAT-GYM-015', '島内体育館', '松本市', '屋内', '複合', '0263-34-1700',
 'https://www.city.matsumoto.nagano.jp/soshiki/239/5733.html', 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'C', '2026-05-29', '詳細属性は公式ページで要確認', 'matsumoto_webR'),

('MAT-GYM-016', '島立体育館', '松本市', '屋内', '複合', '0263-34-1700',
 'https://www.city.matsumoto.nagano.jp/soshiki/239/5732.html', 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'C', '2026-05-29', '詳細属性は公式ページで要確認', 'matsumoto_webR'),

('MAT-GYM-017', '芳川体育館', '松本市', '屋内', '複合', '0263-34-1700',
 'https://www.city.matsumoto.nagano.jp/soshiki/239/5737.html', 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'C', '2026-05-29', '詳細属性は公式ページで要確認', 'matsumoto_webR'),

('MAT-GYM-018', '臨空工業団地体育館', '松本市', '屋内', '複合', '0263-34-1700',
 'https://www.city.matsumoto.nagano.jp/soshiki/239/5727.html', 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'C', '2026-05-29', '詳細属性は公式ページで要確認', 'matsumoto_webR'),

('MAT-GYM-019', '梓川体育館', '松本市', '屋内', '複合', '0263-34-1700',
 'https://www.city.matsumoto.nagano.jp/soshiki/239/5715.html', 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'C', '2026-05-29', '梓川地区。詳細属性は公式ページで要確認', 'matsumoto_webR'),

('MAT-GYM-020', '安曇体育館', '松本市', '屋内', '複合', '0263-34-1700',
 'https://www.city.matsumoto.nagano.jp/soshiki/239/5714.html', 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'C', '2026-05-29', '安曇地区(山岳)。詳細属性は公式ページで要確認', 'matsumoto_webR'),

('MAT-GYM-021', '乗鞍体育館', '松本市', '屋内', '複合', '0263-34-1700',
 'https://www.city.matsumoto.nagano.jp/soshiki/239/5725.html', 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'C', '2026-05-29', '乗鞍高原。詳細属性は公式ページで要確認', 'matsumoto_webR'),

('MAT-GYM-022', '奈川寄合渡体育館', '松本市', '屋内', '複合', '0263-34-1700',
 'https://www.city.matsumoto.nagano.jp/soshiki/239/5723.html', 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'C', '2026-05-29', '奈川地区(中山間地)。詳細属性は公式ページで要確認', 'matsumoto_webR'),

('MAT-GYM-023', '奈川木曽路原体育館', '松本市', '屋内', '複合', '0263-34-1700',
 'https://www.city.matsumoto.nagano.jp/soshiki/239/5713.html', 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'C', '2026-05-29', '奈川地区。詳細属性は公式ページで要確認', 'matsumoto_webR'),

('MAT-GYM-024', '四賀体育館', '松本市', '屋内', '複合', '0263-34-1700',
 'https://www.city.matsumoto.nagano.jp/soshiki/239/5730.html', 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'C', '2026-05-29', '四賀地区。詳細属性は公式ページで要確認', 'matsumoto_webR'),

('MAT-GYM-025', '波田体育館', '松本市', '屋内', '複合', '0263-34-1700',
 'https://www.city.matsumoto.nagano.jp/soshiki/239/5716.html', 'https://yoyaku.city.matsumoto.lg.jp/webR/',
 'C', '2026-05-29', '波田地区。詳細属性は公式ページで要確認', 'matsumoto_webR');

-- =================================================================
-- facility_sports タグ付け
-- =================================================================

-- テニス施設にtennisタグ (10件)
insert into facility_sports (facility_id, sport)
select id, 'tennis' from facilities where facility_code like 'MAT-TEN-%'
on conflict do nothing;

-- 波田扇子田はテニス併設の屋内アリーナにフットサル1面あり=multi/futsalも付与
insert into facility_sports (facility_id, sport)
select id, s from facilities
cross join unnest(array['futsal', 'multi']) as s
where facility_code = 'MAT-TEN-008'
on conflict do nothing;

-- サッカー施設
insert into facility_sports (facility_id, sport)
select id, 'soccer' from facilities where facility_code like 'MAT-SOC-%'
on conflict do nothing;

-- かりがね(MAT-SOC-002)はフットサルも明示
insert into facility_sports (facility_id, sport)
select id, s from facilities
cross join unnest(array['futsal', 'multi']) as s
where facility_code = 'MAT-SOC-002'
on conflict do nothing;

-- ===== 体育館の競技タグ =====
-- 詳細あり10施設: バスケ/バレー/バドミントン/テニス (個別差異あり、共通項のみタグ付け)

-- 全体育館 (詳細あり10 + 簡易15) に basketball, volleyball, multi
insert into facility_sports (facility_id, sport)
select id, s from facilities
cross join unnest(array['basketball', 'volleyball', 'multi']) as s
where facility_code like 'MAT-GYM-%'
on conflict do nothing;

-- フットサル明示 3施設 (エア・ウォーターアリーナ松本、庄内、芝沢)
insert into facility_sports (facility_id, sport)
select id, 'futsal' from facilities
where facility_code in ('MAT-GYM-001', 'MAT-GYM-006', 'MAT-GYM-008')
on conflict do nothing;

-- テニス併設体育館 (詳細施設で記載あり) - 中央/本郷/南部/寿/鎌田/寿台
insert into facility_sports (facility_id, sport)
select id, 'tennis' from facilities
where facility_code in ('MAT-GYM-002', 'MAT-GYM-003', 'MAT-GYM-005',
                        'MAT-GYM-006', 'MAT-GYM-007', 'MAT-GYM-009', 'MAT-GYM-010')
on conflict do nothing;

commit;

-- =================================================================
-- 確認クエリ
-- =================================================================

-- 全体件数
-- select municipality, count(*) from facilities group by municipality;
-- 期待: 長野市 | 43, 松本市 | 37

-- 松本市の競技別件数
-- select fs.sport, count(*) from facilities f
-- join facility_sports fs on fs.facility_id = f.id
-- where f.municipality = '松本市'
-- group by fs.sport order by count(*) desc;

-- external_system 別件数
-- select external_system, count(*) from facilities
-- where external_facility_id is not null or external_system is not null
-- group by external_system;
