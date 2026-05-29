-- =====================================================================
-- Migration: 007
-- Date: 2026-05-28
-- 目的: 問い合わせメッセージ保存テーブル
-- =====================================================================

create table contact_messages (
  id uuid primary key default gen_random_uuid(),
  name text,                                      -- 名前(任意)
  email text,                                     -- メール(任意・返信不要なら空)
  subject text,                                   -- 件名(任意)
  body text not null,                             -- 本文(必須)
  user_agent text,                                -- ブラウザUA(デバッグ用)
  honeypot text,                                  -- スパムbot対策(隠しフィールドに値が入ったらspam判定)
  is_spam boolean not null default false,         -- 管理者がスパム判定したもの
  responded boolean not null default false,       -- 対応済フラグ
  notes text,                                     -- 管理メモ
  created_at timestamptz not null default now()
);

create index idx_contact_messages_unresponded
  on contact_messages(created_at desc)
  where responded = false and is_spam = false;

-- RLS: 匿名ユーザーは INSERT のみ可。SELECT/UPDATE/DELETE は service_role のみ
alter table contact_messages enable row level security;

create policy "anon can insert contact messages"
  on contact_messages
  for insert
  to anon
  with check (true);
-- ↑ SELECTポリシーは作らないので、anon は読み取り不可
