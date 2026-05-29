-- =====================================================================
-- 長野県公共施設ナビ — Initial schema (Phase 1 MVP)
-- Migration: 001
-- Date: 2026-05-23
-- Supabase / PostgreSQL 15+
-- =====================================================================

-- Required extensions ---------------------------------------------------
create extension if not exists pgcrypto;     -- gen_random_uuid()
create extension if not exists cube;          -- earthdistance prerequisite
create extension if not exists earthdistance; -- 距離計算 (optional)

-- =====================================================================
-- 1. facilities ─ 施設マスタ
-- =====================================================================
create table facilities (
  id uuid primary key default gen_random_uuid(),
  facility_code        text unique not null,
  facility_name        text not null,
  official_name        text,
  municipality         text not null,
  address              text,  -- nullable: Phase 1 では候補登録段階で住所未取得の施設あり
  latitude             numeric(9,6),
  longitude            numeric(9,6),
  indoor_outdoor       text check (indoor_outdoor in ('屋内','屋外','屋根付き','要確認')),
  surface_type         text check (surface_type in ('砂入り人工芝','人工芝','天然芝','クレー','ハード','土','体育館床','要確認')),
  court_count          int,
  lighting_available   boolean,
  operating_hours      text,
  closed_days          text,
  parking              text,
  changing_shower      text,
  fee_text             text,
  fee_structure        jsonb,
  booking_method       text check (booking_method in ('Web','電話','窓口','予約不要','複合','要確認')),
  registration_required text check (registration_required in ('不要','必要','団体登録','市内限定','要確認')),
  nonresident_policy   text check (nonresident_policy in ('可','不可','制限あり','要確認')),
  same_day_booking     text check (same_day_booking in ('可','不可','電話のみ','要確認')),
  phone_number         text,
  official_url         text,
  reservation_url      text,
  availability_url     text,
  data_confidence      text not null default 'C' check (data_confidence in ('A','B','C')),
  last_verified_at     timestamptz not null default now(),
  notes                text,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now()
);

create index idx_facilities_municipality on facilities(municipality);
create index idx_facilities_indoor on facilities(municipality, indoor_outdoor);
create index idx_facilities_surface on facilities(surface_type);
create index idx_facilities_lighting on facilities(lighting_available);
-- 距離検索用 (使う場合のみ)
-- create index idx_facilities_geo on facilities using gist (ll_to_earth(latitude, longitude));

-- updated_at 自動更新トリガ
create or replace function set_updated_at() returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_facilities_updated_at
  before update on facilities
  for each row execute function set_updated_at();

-- =====================================================================
-- 2. facility_sports ─ 施設×競技 (多対多)
-- =====================================================================
create table facility_sports (
  facility_id uuid not null references facilities(id) on delete cascade,
  sport text not null check (sport in ('tennis','soccer','futsal','multi','baseball','basketball','volleyball')),
  primary key (facility_id, sport)
);
create index idx_facility_sports_sport on facility_sports(sport);

-- =====================================================================
-- 3. availability_current ─ 最新空き状況 (表示用)
-- =====================================================================
create table availability_current (
  id bigserial primary key,
  facility_id uuid not null references facilities(id) on delete cascade,
  target_date date not null,
  start_time time not null,
  end_time time not null,
  availability_status text not null check (availability_status in ('空き','一部空き','満','不明','休館')),
  available_court_count int,
  source text not null check (source in ('scrape','manual','api')),
  last_checked_at timestamptz not null default now(),
  unique (facility_id, target_date, start_time)
);
create index idx_avail_current_date_status on availability_current(target_date, availability_status);
create index idx_avail_current_facility_date on availability_current(facility_id, target_date);

-- =====================================================================
-- 4. availability_snapshots ─ 時系列蓄積 (分析用)
-- =====================================================================
create table availability_snapshots (
  id bigserial primary key,
  facility_id uuid not null references facilities(id) on delete cascade,
  target_date date not null,
  start_time time not null,
  end_time time not null,
  availability_status text not null check (availability_status in ('空き','一部空き','満','不明','休館')),
  available_court_count int,
  source text not null check (source in ('scrape','manual','api')),
  snapshot_at timestamptz not null default now()
);
create index idx_snap_facility_history on availability_snapshots(facility_id, target_date, snapshot_at desc);
create index idx_snap_snapshot_at on availability_snapshots(snapshot_at);
-- 容量が膨らんだら snapshot_at の月単位パーティション化を検討

-- =====================================================================
-- 5. scraping_jobs ─ 取得ログ
-- =====================================================================
create table scraping_jobs (
  id bigserial primary key,
  municipality text not null,
  sport text,
  scraper_name text not null,
  scraper_version text not null,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null check (status in ('running','success','partial','error')),
  records_fetched int,
  error_message text
);
create index idx_scraping_jobs_status on scraping_jobs(status, started_at desc);
create index idx_scraping_jobs_scraper on scraping_jobs(scraper_name, started_at desc);

-- =====================================================================
-- Row Level Security (Supabase推奨)
-- =====================================================================
alter table facilities enable row level security;
alter table facility_sports enable row level security;
alter table availability_current enable row level security;
alter table availability_snapshots enable row level security;
alter table scraping_jobs enable row level security;

-- 読み取りは公開、書き込みは認証済み (service_role) のみ
create policy "read facilities" on facilities for select using (true);
create policy "read facility_sports" on facility_sports for select using (true);
create policy "read availability_current" on availability_current for select using (true);
-- snapshots と scraping_jobs は管理者のみ
-- INSERT/UPDATE は service_role キー経由で行う想定 (RLSはバイパスされる)
