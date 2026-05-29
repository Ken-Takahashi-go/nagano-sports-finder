-- =====================================================================
-- Seed: 優先度A サッカー系施設の完了 (球技場詳細情報を補完)
-- Date: 2026-05-23
-- Source: 公式ホームページ複数 + フットボール場PDF
-- =====================================================================

begin;

-- =================================================================
-- NAG-SOC-001 南長野運動公園球技場 (長野Uスタジアム = AC長野パルセイロホーム)
-- =================================================================
update facilities set
  facility_name = '南長野運動公園球技場(長野Uスタジアム)',
  address = '長野市篠ノ井東福寺320',
  court_count = 5,  -- フットボール場A(ラグビー兼用),B,C,D,E の計5面
  parking = 'あり(874台)',
  phone_number = '026-293-4818',
  notes = '長野Uスタジアム。J3 AC長野パルセイロのホームスタジアム。FIFA基準準拠。フットボール場5面構成(A=ラグビー・フットボール兼用、B=東面川側、C=西面土手側、D=北面上流側、E=北面下流側)。長野IC車5分。国スポ女子サッカー会場。詳細PDF: /documents/3172/football.pdf',
  data_confidence = 'B',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-SOC-001';

-- =================================================================
-- NAG-SOC-002 長野運動公園球技場
-- =================================================================
update facilities set
  facility_name = '長野運動公園総合運動場(球技場)',
  address = '長野市吉田5-1-19',
  phone_number = '026-241-4200',
  notes = '長野運動公園内の球技場。テニスコート(TEN-018と同敷地)もあり。サッカー面数とサーフェスは公式公開情報からは確定できず。電話確認推奨',
  data_confidence = 'C',  -- 詳細未確定のためC
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-SOC-002';

-- =================================================================
-- NAG-SOC-003 北部スポレクパーク (屋外サッカー1面の追加情報)
-- =================================================================
update facilities set
  notes = '屋内多目的施設。テニス4面/フットサル2面/ゲートボール6面。県内希少な屋内テニス施設。同公園内には屋外運動広場もあり(サッカー1面、午前8:30-21:00)',
  last_verified_at = '2026-05-23'
where facility_code = 'NAG-SOC-003';

commit;

-- =================================================================
-- 全体最終確認クエリ
-- =================================================================

-- 全施設のステータス確認
-- select data_confidence, count(*) from facilities group by data_confidence;
-- 期待: B | 30, C | 1 (SOC-002のみ)

-- ★ナイター可能テニス施設 (最終: 6施設、41面)
-- select f.facility_code, f.facility_name, f.court_count
-- from facilities f join facility_sports fs on fs.facility_id=f.id
-- where fs.sport='tennis' and f.lighting_available=true
-- order by f.court_count desc;

-- 全テニス施設の面数合計
-- select sum(court_count) as total_courts, count(*) as facility_count
-- from facilities f join facility_sports fs on fs.facility_id=f.id
-- where fs.sport='tennis';

-- 無料テニス施設
-- select facility_code, facility_name, court_count
-- from facilities f join facility_sports fs on fs.facility_id=f.id
-- where fs.sport='tennis' and f.fee_text='無料';

-- サッカー/フットサル可能施設
-- select f.facility_code, f.facility_name, f.court_count, f.surface_type, f.fee_text
-- from facilities f join facility_sports fs on fs.facility_id=f.id
-- where fs.sport in ('soccer','futsal')
-- order by facility_code;
