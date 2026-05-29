-- =====================================================================
-- Migration: 002
-- Date: 2026-05-23
-- 目的: surface_type に「全天候型舗装」を追加
--       長野市公式の御厨・篠ノ井で実際に使われている表記であり、独自カテゴリ
--       (ハードコートとは異なる、塗膜系の表面)として扱う
-- =====================================================================

alter table facilities drop constraint if exists facilities_surface_type_check;

alter table facilities add constraint facilities_surface_type_check
  check (surface_type in (
    '砂入り人工芝',
    '人工芝',
    '天然芝',
    'クレー',
    'ハード',
    '全天候型舗装',
    '土',
    '体育館床',
    '要確認'
  ));
