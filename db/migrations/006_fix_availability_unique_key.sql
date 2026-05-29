-- =====================================================================
-- Migration: 006
-- Date: 2026-05-28
-- 目的: availability_current の UNIQUE 制約に end_time を含める
-- 経緯: 飯綱高原南グラウンド等で、同じ start_time に対して
--       午前(08:00-12:00)と全日(08:00-17:00)のように end_time が異なる
--       スロットが両方存在する。end_time なしの UNIQUE 制約だと衝突する。
-- =====================================================================

-- 既存の UNIQUE 制約を全部削除 (名前は自動命名なので動的取得)
do $$
declare
  c_name text;
begin
  for c_name in
    select conname from pg_constraint
    where conrelid = 'availability_current'::regclass
      and contype = 'u'
  loop
    execute format('alter table availability_current drop constraint %I', c_name);
  end loop;
end $$;

-- end_time も含めた新 UNIQUE 制約
alter table availability_current
  add constraint availability_current_unique_slot
  unique (facility_id, target_date, start_time, end_time);

comment on constraint availability_current_unique_slot on availability_current is
  '同一(facility, date, start, end)のUPSERT用キー。end_timeも含むことで、同じstart_timeで貸出時間が異なるスロット(午前/全日 等)を共存可能にする。';
