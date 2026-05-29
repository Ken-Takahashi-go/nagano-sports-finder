-- =====================================================================
-- Migration: 005
-- Date: 2026-05-28
-- 目的: availability テーブルに集約データ用カラム追加
--       - total_court_count: 総コート数 (集約のため)
--       - fee_min_yen / fee_max_yen: 料金帯 (時間帯による変動)
-- =====================================================================

alter table availability_current
  add column if not exists total_court_count int,
  add column if not exists fee_min_yen int,
  add column if not exists fee_max_yen int;

alter table availability_snapshots
  add column if not exists total_court_count int,
  add column if not exists fee_min_yen int,
  add column if not exists fee_max_yen int;

comment on column availability_current.total_court_count is '総コート数 (集約データ用。例: 16面中3面空き なら 16)';
comment on column availability_current.available_court_count is '空きコート数 (集約データ用。例: 16面中3面空き なら 3)';
comment on column availability_current.fee_min_yen is '当該時間帯のコート料金の最小値 (円)';
comment on column availability_current.fee_max_yen is '当該時間帯のコート料金の最大値 (円)';
