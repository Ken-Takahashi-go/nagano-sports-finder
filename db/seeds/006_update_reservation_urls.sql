-- =====================================================================
-- Seed: reservation_url を「まちかぎリモート」に紐付け
-- Date: 2026-05-23
-- 注: 個別施設のmachikagi内ページIDは Phase 1 Week 2 のスクレイパーPoCで紐付け
--     現段階では一旦「まちかぎリモート」トップに導線を貼る
-- =====================================================================

begin;

-- Web予約 または 複合(Web+電話) のテニス・サッカー系施設
update facilities set
  reservation_url = 'https://city.nagano.nagano.machikagi-remote.jp/'
where municipality = '長野市'
  and booking_method in ('Web', '複合')
  and reservation_url is null;

-- 飯綱高原南グラウンドは観光協会経由予約も可能
update facilities set
  reservation_url = 'https://city.nagano.nagano.machikagi-remote.jp/',
  notes = notes  -- notes 既存維持
where facility_code = 'NAG-SOC-005';

-- ※予約不要施設(booking_method='予約不要')は reservation_url を意図的にNULLのまま残す

commit;

-- 確認: 予約URLが入った件数
-- select count(*) from facilities where reservation_url is not null;
-- 期待: 20件前後 (Web/複合の施設)

-- select facility_code, facility_name, booking_method, reservation_url
-- from facilities order by facility_code;
