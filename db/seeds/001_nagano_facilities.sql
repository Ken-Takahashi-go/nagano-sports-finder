-- =====================================================================
-- Seed: 長野市公共スポーツ施設 32件 (Phase 1 初期データ)
-- Date: 2026-05-23
-- Source: 既存XLSX「施設マスタ」シート、長野市公式ページ
-- 注意:
--   - 緯度経度・サーフェス・面数・ナイター・料金・電話番号は Phase 1 Week 1 で
--     現地調査して埋める想定。本SEEDでは初期値（NULL or 要確認）を投入。
--   - data_confidence: テニス施設=B (公式一覧から名称・住所確定済)
--                    : サッカー/多目的施設=C (候補登録段階)
-- =====================================================================

-- 既存データを念のため削除（再実行時用）
delete from facility_sports where facility_id in (select id from facilities where municipality = '長野市');
delete from availability_current where facility_id in (select id from facilities where municipality = '長野市');
delete from availability_snapshots where facility_id in (select id from facilities where municipality = '長野市');
delete from facilities where municipality = '長野市';

-- ----------------------------------------------------------
-- facilities INSERT (32件)
-- ----------------------------------------------------------
insert into facilities (
  facility_code, facility_name, municipality, address,
  indoor_outdoor, surface_type,
  booking_method, registration_required, nonresident_policy, same_day_booking,
  official_url, notes, data_confidence, last_verified_at
) values
-- ===== テニスコート (24件) =====
('NAG-TEN-001', '長野市営城山テニスコート',                      '長野市', '長野市箱清水一丁目10番41号',
 '屋外', '要確認', '予約不要', '不要', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 '現地管理棟受付。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-002', '長野市営古里テニスコート',                      '長野市', '長野市大字下駒沢23番地',
 '屋外', '要確認', 'Web', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 'Web予約。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-003', '長野市営緑ケ丘テニスコート',                    '長野市', '長野市神楽橋39番地2',
 '屋外', '要確認', 'Web', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 'Web予約。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-004', '長野市営大豆島テニスコート',                    '長野市', '長野市大字大豆島4330番地',
 '屋外', '要確認', 'Web', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 'Web予約。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-005', '長野市営昭和の森公園テニスコート',              '長野市', '長野市上野二丁目120番地13',
 '屋外', '要確認', 'Web', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 'Web予約。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-006', '長野市営篠ノ井テニスコート',                    '長野市', '長野市篠ノ井塩崎4720番地',
 '屋外', '要確認', 'Web', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 'Web予約。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-007', '長野市営川柳テニスコート',                      '長野市', '長野市篠ノ井石川1523番地の2',
 '屋外', '要確認', 'Web', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 'Web予約。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-008', '長野市営若穂中央公園テニスコート',              '長野市', '長野市若穂川田427番地1',
 '屋外', '要確認', '予約不要', '不要', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 '現地受付。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-009', '長野市営御厨テニスコート',                      '長野市', '長野市川中島町御厨562番地',
 '屋外', '要確認', 'Web', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 'Web予約。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-010', '長野市営豊野テニスコート',                      '長野市', '長野市豊野町豊野820番地1',
 '屋外', '要確認', 'Web', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 'Web予約。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-011', '長野市営鬼無里テニスコート',                    '長野市', '長野市鬼無里147番地2',
 '屋外', '要確認', 'Web', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 'Web予約。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-012', '長野市営西和田テニスコート',                    '長野市', '長野市西和田二丁目26番1号',
 '屋外', '要確認', '予約不要', '不要', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 '現地管理棟受付。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-013', '長野市営茶臼山テニスコート',                    '長野市', '長野市篠ノ井岡田2052番地4',
 '屋外', '要確認', 'Web', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 'Web予約。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-014', '長野市営青垣公園テニスコート',                  '長野市', '長野市松代町西条3860番地',
 '屋外', '要確認', '予約不要', '不要', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 '現地受付簿。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-015', '長野市営真島テニスコート',                      '長野市', '長野市真島町真島2268番地1',
 '屋外', '要確認', 'Web', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 'Web予約。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-016', '長野市営三輪テニスコート',                      '長野市', '長野市三輪3-816',
 '屋外', '要確認', '予約不要', '不要', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 '現地受付簿。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-017', '長野市営小松原運動場テニスコート',              '長野市', '長野市篠ノ井小松原1398-2',
 '屋外', '要確認', '予約不要', '不要', '要確認', '可',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 '受付なし/当日空き利用。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-018', '長野市営長野運動公園総合運動場テニスコート',    '長野市', '長野市吉田5丁目1番地19号',
 '屋外', '要確認', 'Web', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 'Web予約。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-019', '長野市営南長野運動公園総合運動場テニスコート',  '長野市', '長野市篠ノ井東福寺320番地',
 '屋外', '要確認', 'Web', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 'Web予約。サーフェス/照明/料金は個別ページまたは電話確認', 'B', '2026-05-21'),

('NAG-TEN-020', '長野市営犀川第一運動場テニスコート',            '長野市', '長野市大字安茂里1605番地の2地先（河川敷）',
 '屋外', '要確認', '予約不要', '不要', '要確認', '可',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 '受付なし/当日空き利用。河川敷', 'B', '2026-05-21'),

('NAG-TEN-021', '長野市営犀川第二運動場テニスコート',            '長野市', '長野市青木島町青木島乙954番地の2（河川敷）',
 '屋外', '要確認', '予約不要', '不要', '要確認', '可',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 '受付なし/当日空き利用。河川敷', 'B', '2026-05-21'),

('NAG-TEN-022', '長野市営犀川南運動場テニスコート',              '長野市', '長野市丹波島三丁目1052番地（河川敷）',
 '屋外', '要確認', '予約不要', '不要', '要確認', '可',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 '受付なし/当日空き利用。河川敷', 'B', '2026-05-21'),

('NAG-TEN-023', '長野市営西寺尾運動場テニスコート',              '長野市', '長野市松代町東寺尾1276番地（河川敷）',
 '屋外', '要確認', '予約不要', '不要', '要確認', '可',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 '受付なし/当日空き利用。河川敷', 'B', '2026-05-21'),

('NAG-TEN-024', '長野市営七二会運動場テニスコート',              '長野市', '長野市七二会己989番地のナ',
 '屋外', '要確認', '予約不要', '不要', '要確認', '可',
 'https://www.city.nagano.nagano.jp/n155400/contents/p003057.html',
 '受付なし/当日空き利用', 'B', '2026-05-21'),

-- ===== サッカー/フットサル/多目的 (8件) =====
('NAG-SOC-001', '南長野運動公園総合運動場',          '長野市', NULL,
 '屋外', '要確認', '複合', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/menu/5/3/3/index.html',
 '芝種別/スパイク可否/半面利用を要確認', 'C', '2026-05-21'),

('NAG-SOC-002', '長野運動公園総合運動場',            '長野市', NULL,
 '屋外', '要確認', '複合', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/menu/5/3/3/index.html',
 '芝種別/スパイク可否/半面利用を要確認', 'C', '2026-05-21'),

('NAG-SOC-003', '北部スポーツ・レクリエーションパーク', '長野市', NULL,
 '屋外', '要確認', '複合', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/menu/5/3/3/index.html',
 '芝種別/スパイク可否/半面利用を要確認', 'C', '2026-05-21'),

('NAG-SOC-004', '若穂多目的広場',                    '長野市', NULL,
 '屋外', '要確認', '複合', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/menu/5/3/3/index.html',
 '芝種別/スパイク可否/半面利用を要確認', 'C', '2026-05-21'),

('NAG-SOC-005', '飯綱高原南グラウンド',              '長野市', NULL,
 '屋外', '要確認', '複合', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/menu/5/3/3/index.html',
 '芝種別/スパイク可否/半面利用を要確認', 'C', '2026-05-21'),

('NAG-SOC-006', '犀川第一運動場',                    '長野市', NULL,
 '屋外', '要確認', '複合', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/menu/5/3/3/index.html',
 '芝種別/スパイク可否/半面利用を要確認。テニスコートと同敷地', 'C', '2026-05-21'),

('NAG-SOC-007', '犀川第二運動場',                    '長野市', NULL,
 '屋外', '要確認', '複合', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/menu/5/3/3/index.html',
 '芝種別/スパイク可否/半面利用を要確認。テニスコートと同敷地', 'C', '2026-05-21'),

('NAG-SOC-008', '犀川南運動場',                      '長野市', NULL,
 '屋外', '要確認', '複合', '要確認', '要確認', '要確認',
 'https://www.city.nagano.nagano.jp/menu/5/3/3/index.html',
 '芝種別/スパイク可否/半面利用を要確認。テニスコートと同敷地', 'C', '2026-05-21');

-- ----------------------------------------------------------
-- facility_sports INSERT (40件: テニス24 + サッカー8 + フットサル8)
-- ----------------------------------------------------------
insert into facility_sports (facility_id, sport)
select id, 'tennis' from facilities
where facility_code like 'NAG-TEN-%';

insert into facility_sports (facility_id, sport)
select id, 'soccer' from facilities
where facility_code like 'NAG-SOC-%';

insert into facility_sports (facility_id, sport)
select id, 'futsal' from facilities
where facility_code like 'NAG-SOC-%';

-- ----------------------------------------------------------
-- 確認クエリ (実行後に件数チェック)
-- ----------------------------------------------------------
-- select municipality, count(*) from facilities group by municipality;  -- 長野市 | 32
-- select sport, count(*) from facility_sports group by sport;            -- tennis 24, soccer 8, futsal 8
-- select * from facilities where data_confidence='B' order by facility_code limit 5;
