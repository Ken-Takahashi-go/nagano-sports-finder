-- =====================================================================
-- Migration: 008
-- Date: 2026-05-29
-- 目的: facilities テーブルに自治体予約システム汎用化カラムを追加
-- 経緯:
--   Phase 1 では machikagi_facility_id (長野市まちかぎリモート専用) のみ
--   Phase 1.5 で松本市(webR)対応 → 汎用化が必要
--   Phase 1.6 以降 (安曇野・上田等) でも同じ仕組みで拡張可能
--
-- 設計:
--   external_system: 予約システム識別子 ('nagano_machikagi', 'matsumoto_webR', 'azumino_pf489' 等)
--   external_facility_id: 各システム内の施設ID (text型で文字列も数値も対応)
--   既存の machikagi_facility_id は互換性のため残す (Phase 2でdeprecate予定)
-- =====================================================================

-- カラム追加
alter table facilities
  add column if not exists external_system text,
  add column if not exists external_facility_id text;

comment on column facilities.external_system is
  '予約システム識別子。例: nagano_machikagi, matsumoto_webR, azumino_pf489';
comment on column facilities.external_facility_id is
  '予約システム内の施設ID (テキスト)。スクレイパーで /{system}/facilities/{id} 等へアクセスする際に使用';

-- 既存長野市データを汎用カラムに移行
update facilities set
  external_system = 'nagano_machikagi',
  external_facility_id = machikagi_facility_id::text
where machikagi_facility_id is not null
  and external_system is null;  -- 冪等性のため

-- インデックス (スクレイパーが (system, id) で検索する)
create index if not exists idx_facilities_external
  on facilities(external_system, external_facility_id)
  where external_facility_id is not null;

-- 確認用ビュー (任意)
-- 各 external_system の件数
-- select external_system, count(*)
-- from facilities
-- where external_facility_id is not null
-- group by external_system;
