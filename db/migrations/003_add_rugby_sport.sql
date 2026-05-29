-- =====================================================================
-- Migration: 003
-- Date: 2026-05-23
-- 目的: facility_sports.sport に 'rugby' を追加
--       千曲川リバーフロントスポーツガーデンがラグビー兼用施設のため
-- =====================================================================

alter table facility_sports drop constraint if exists facility_sports_sport_check;

alter table facility_sports add constraint facility_sports_sport_check
  check (sport in (
    'tennis',
    'soccer',
    'futsal',
    'rugby',
    'multi',
    'baseball',
    'basketball',
    'volleyball'
  ));
