# DB 設計の運用ガイド

## ファイル構成

```
db/
├── README.md                          ← 運用ガイド (このファイル)
├── SUPABASE_SETUP.md                  ← Supabase初期構築手順
├── schema_v2.md                       ← 設計の正本 (人間が読む)
├── migrations/
│   └── 001_initial_schema.sql         ← Supabaseに当てるSQL DDL
└── seeds/
    ├── 001_nagano_facilities.sql      ← 長野市32施設の初期データ (SQL)
    └── 001_nagano_facilities.csv      ← 同上 (CSV版・管理用)
```

## 最初にやること

→ [`SUPABASE_SETUP.md`](SUPABASE_SETUP.md) の手順を順に実行してください。

## 更新の流れ

1. **設計を変えたい** → `schema_v2.md` を編集
2. **DBに反映する** → `migrations/00N_xxx.sql` を新規作成（番号は連番）
3. **Supabaseに適用** → ダッシュボードの SQL Editor or `supabase db push`
4. **Changelog 更新** → `schema_v2.md` 末尾に v2.1 / v2.2 などで追記
5. **初期データの追加・修正** → `seeds/00N_xxx.sql` を新規作成（番号は連番）

## 過去資産

- 旧データ辞書: [`../public_sports_facility_mvp_database_architecture_updated.xlsx`](../public_sports_facility_mvp_database_architecture_updated.xlsx)
  - 「施設マスタ」シートのデータ（82件中、長野市32件）は `seeds/001_nagano_facilities.sql` に移行済
  - 「調査チェックリスト」「収集進捗」シートは引き続き運用ログとして利用可

## 命名規則

- テーブル/カラムはすべて `snake_case`
- 真偽値は `_available` / `_required` などの形容詞付与で意図を明示
- 時刻系は `_at`（timestamptz）、日付系は `_date`、時刻のみは `_time`
- migrations/seeds は3桁連番 `001_` `002_` ...

## CSV 直接インポートしたい場合

Supabase の Table Editor → 対象テーブル → 右上「Import data via CSV」から `001_nagano_facilities.csv` を選択。

ただし `facility_sports` は CSV 直接インポートできない（UUID変換が必要）ため、SQL版 (`001_nagano_facilities.sql`) を推奨します。
