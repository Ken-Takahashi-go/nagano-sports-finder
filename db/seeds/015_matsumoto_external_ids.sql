-- =====================================================================
-- Seed: 015_matsumoto_external_ids
-- Date: 2026-06-02
-- 目的: Stage M3 で取得した webR の checkShisetsu value (=external_facility_id) を
--       既存の MAT-GYM facility に紐付け
-- 経緯:
--   Stage M3 で zenshisetsu 画面の体育館 10件のみ取得
--   Stage M3-fix v2 でテニス・サッカー含む全件取得中 (別途)
--   ひとまずカレンダー取得可能な体育館 10件を紐付け、Stage M5 で空き状況を投入できる状態にする
-- 対応表:
--   webR 202001 = 総合体育館       → MAT-GYM-001 (エア・ウォーターアリーナ松本)
--   webR 202002 = 南部体育館       → MAT-GYM-005
--   webR 202003 = 岡田体育館       → MAT-GYM-012
--   webR 202004 = 芳川体育館       → MAT-GYM-017
--   webR 202005 = 島内体育館       → MAT-GYM-015
--   webR 202006 = 庄内体育館       → MAT-GYM-006
--   webR 202007 = 芝沢体育館       → MAT-GYM-008
--   webR 202008 = 神林体育館       → MAT-GYM-013
--   webR 202009 = 里山辺体育館     → MAT-GYM-014
--   webR 202010 = 鎌田体育館       → MAT-GYM-009
-- =====================================================================

begin;

update facilities set external_system = 'matsumoto_webR', external_facility_id = '202001' where facility_code = 'MAT-GYM-001';
update facilities set external_system = 'matsumoto_webR', external_facility_id = '202002' where facility_code = 'MAT-GYM-005';
update facilities set external_system = 'matsumoto_webR', external_facility_id = '202003' where facility_code = 'MAT-GYM-012';
update facilities set external_system = 'matsumoto_webR', external_facility_id = '202004' where facility_code = 'MAT-GYM-017';
update facilities set external_system = 'matsumoto_webR', external_facility_id = '202005' where facility_code = 'MAT-GYM-015';
update facilities set external_system = 'matsumoto_webR', external_facility_id = '202006' where facility_code = 'MAT-GYM-006';
update facilities set external_system = 'matsumoto_webR', external_facility_id = '202007' where facility_code = 'MAT-GYM-008';
update facilities set external_system = 'matsumoto_webR', external_facility_id = '202008' where facility_code = 'MAT-GYM-013';
update facilities set external_system = 'matsumoto_webR', external_facility_id = '202009' where facility_code = 'MAT-GYM-014';
update facilities set external_system = 'matsumoto_webR', external_facility_id = '202010' where facility_code = 'MAT-GYM-009';

commit;

-- 確認
-- select facility_code, facility_name, external_system, external_facility_id
-- from facilities
-- where municipality = '松本市' and external_facility_id is not null
-- order by external_facility_id;
-- 期待: 10件
