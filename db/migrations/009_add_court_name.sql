-- =====================================================================
-- Migration: 009
-- Date: 2026-06-26
-- 目的: 1施設内の設備(コート/部屋)を区別するため court_name を追加。
--       例: 信州グリーンフィールド = 人工芝コート全面/半面東/半面西/多目的広場…
-- 影響: UNIQUE 制約に court_name を含めるため、全スクレイパーの UPSERT(on_conflict)
--       を court_name 込みに更新する必要がある(コード配備と協調すること)。
-- 後方互換: 既存施設は court_name='' (デフォルト) となり、(facility,'',date,start,end)
--           で従来と同等のキーになる。
-- =====================================================================

-- 1. court_name 列を追加 (既存行は '' )
alter table availability_current
  add column if not exists court_name text not null default '';
alter table availability_snapshots
  add column if not exists court_name text not null default '';

-- 2. availability_current の UNIQUE 制約を court_name 込みに張り替え
--    (既存のUNIQUE制約は名前自動命名のため動的に全削除)
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

alter table availability_current
  add constraint availability_current_unique_slot
  unique (facility_id, court_name, target_date, start_time, end_time);

comment on constraint availability_current_unique_slot on availability_current is
  'UPSERTキー。court_nameを含めることで1施設内の複数コート(全面/半面/多目的広場 等)を共存可能にする。非対応施設は court_name='''' 。';

-- 3. 索引(任意): コート単位の取得を高速化
create index if not exists idx_avail_current_facility_court_date
  on availability_current(facility_id, court_name, target_date);
