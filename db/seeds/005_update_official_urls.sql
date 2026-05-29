-- =====================================================================
-- Seed: 各施設の official_url を個別ページへ更新
-- Date: 2026-05-23
-- 理由: 全施設が「テニスコート一覧」総合ページに飛んでいたため、
--       各施設の個別ページに直接遷移するよう修正
-- =====================================================================

begin;

-- テニスコート 24件
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003058.html' where facility_code = 'NAG-TEN-001';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003059.html' where facility_code = 'NAG-TEN-002';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003060.html' where facility_code = 'NAG-TEN-003';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003061.html' where facility_code = 'NAG-TEN-004';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003062.html' where facility_code = 'NAG-TEN-005';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003063.html' where facility_code = 'NAG-TEN-006';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003064.html' where facility_code = 'NAG-TEN-007';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003065.html' where facility_code = 'NAG-TEN-008';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003066.html' where facility_code = 'NAG-TEN-009';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003067.html' where facility_code = 'NAG-TEN-010';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003068.html' where facility_code = 'NAG-TEN-011';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003070.html' where facility_code = 'NAG-TEN-012';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003071.html' where facility_code = 'NAG-TEN-013';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003072.html' where facility_code = 'NAG-TEN-014';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003073.html' where facility_code = 'NAG-TEN-015';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003074.html' where facility_code = 'NAG-TEN-016';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003022.html' where facility_code = 'NAG-TEN-017';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003009.html' where facility_code = 'NAG-TEN-018';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003010.html' where facility_code = 'NAG-TEN-019';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003016.html' where facility_code = 'NAG-TEN-020';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003026.html' where facility_code = 'NAG-TEN-021';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003025.html' where facility_code = 'NAG-TEN-022';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003023.html' where facility_code = 'NAG-TEN-023';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003029.html' where facility_code = 'NAG-TEN-024';

-- サッカー/フットサル/多目的 7件 (SOC-004は削除済)
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003010.html' where facility_code = 'NAG-SOC-001';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003009.html' where facility_code = 'NAG-SOC-002';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003100.html' where facility_code = 'NAG-SOC-003';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n150800/contents/p003109.html' where facility_code = 'NAG-SOC-005';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003016.html' where facility_code = 'NAG-SOC-006';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003026.html' where facility_code = 'NAG-SOC-007';
update facilities set official_url = 'https://www.city.nagano.nagano.jp/n155400/contents/p003025.html' where facility_code = 'NAG-SOC-008';

commit;

-- 確認: 各施設のURL末尾(末番号)が個別ページになっているか
-- select facility_code, facility_name, official_url from facilities order by facility_code;
