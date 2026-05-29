-- =====================================================================
-- Migration: 004
-- Date: 2026-05-23
-- 目的: facilities にまちかぎリモートのfacility_idを保存するカラムを追加
--       Stage 2 以降のスクレイパーで /facilities/{ID} に直接アクセスするため
-- =====================================================================

alter table facilities
  add column if not exists machikagi_facility_id integer;

comment on column facilities.machikagi_facility_id is
  'まちかぎリモートのfacility_id (例: 75). スクレイパーで /facilities/{ID} へ直接アクセスする際に使用';

create index if not exists idx_facilities_machikagi
  on facilities(machikagi_facility_id)
  where machikagi_facility_id is not null;
