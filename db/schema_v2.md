# 長野県公共施設ナビ DBスキーマ v2

- **バージョン**: 2.0
- **最終更新**: 2026-05-23
- **対象DB**: Supabase (PostgreSQL 15+)
- **正本**: 本ファイル + `db/migrations/*.sql`
- **変更履歴**: 本ファイル末尾の Changelog 参照

---

## 設計方針

1. **検索（読み）が主、書き込みは管理画面 or スクレイパー経由**
2. **データの「鮮度」を常に表示できるよう、`last_*_at` 系を全エンティティに保持**
3. **時系列スナップショット (`availability_snapshots`) を Day 1 から蓄積** — 将来の自治体向けSaaS化（稼働率分析）の資産形成
4. **Phase 1 は手動更新でも回せる粒度**にとどめ、Phase 2-4 で正規化を段階的に進める
5. **更新しやすさのため、enum は文字列CHECK制約ではなく、別表 (lookup) を最小限に**

---

## エンティティ全体図

```
facilities (1) ──< facility_sports (N)
facilities (1) ──< facility_courts (N)        ※Phase 2以降
facilities (1) ──< availability_current (N)   ※検索表示用
facilities (1) ──< availability_snapshots (N) ※時系列蓄積用
facilities (1) ──< scraping_jobs (N)
users (1) ──< favorites (N)                   ※Phase 2
users (1) ──< notification_rules (N)          ※Phase 3
```

---

## テーブル定義

### `facilities` — 施設マスタ

公共スポーツ施設1件＝1行。物理的な施設単位で、テニスコート8面まとめて1行（コートごとの差はPhase2で `facility_courts` 切出し）。

| カラム | 型 | 必須 | 例 | 補足 |
|---|---|---|---|---|
| `id` | uuid PK | ✓ | `auto` | `gen_random_uuid()` |
| `facility_code` | text UNIQUE | ✓ | `NAG-TEN-001` | スクレイピング識別子。既存XLSXの命名規則を踏襲 |
| `facility_name` | text | ✓ | 長野市営城山テニスコート | 表示名 |
| `official_name` | text | ✗ | 同上 | 公式表記が別の場合のみ |
| `municipality` | text | ✓ | 長野市 | 検索キー |
| `address` | text | ✗ | 長野市箱清水一丁目10番41号 | 候補登録段階では空欄あり |
| `latitude` | numeric(9,6) | ✗ | 36.6601 | ジオコーディングで後付け可 |
| `longitude` | numeric(9,6) | ✗ | 138.1944 | |
| `indoor_outdoor` | text | ✓ | `屋外` | CHECK: 屋内/屋外/屋根付き/要確認 |
| `surface_type` | text | ✗ | `砂入り人工芝` | CHECK: 砂入り人工芝/人工芝/天然芝/クレー/ハード/土/体育館床/要確認 |
| `court_count` | integer | ✗ | 8 | 物理的なコート/面数。0は不明 |
| `lighting_available` | boolean | ✗ | true | NULLは「要確認」 |
| `operating_hours` | text | ✗ | 9:00-21:00 | テキスト保持 |
| `closed_days` | text | ✗ | 月曜・年末年始 | |
| `parking` | text | ✗ | あり(30台) | 台数あればベター |
| `changing_shower` | text | ✗ | 更衣室あり/シャワーなし | |
| `fee_text` | text | ✗ | 1時間500円(市外1500円) | Phase 1は自由記述 |
| `fee_structure` | jsonb | ✗ | `{"hourly":500,"nonresident_hourly":1500}` | Phase 2で構造化 |
| `booking_method` | text | ✗ | `Web` | CHECK: Web/電話/窓口/予約不要/複合 |
| `registration_required` | text | ✗ | `必要` | CHECK: 不要/必要/団体登録/市内限定/要確認 |
| `nonresident_policy` | text | ✗ | `可` | CHECK: 可/不可/制限あり/要確認 |
| `same_day_booking` | text | ✗ | `可` | CHECK: 可/不可/電話のみ/要確認 |
| `phone_number` | text | ✗ | 026-224-5083 | |
| `official_url` | text | ✗ | https://... | 自治体公式の施設ページ |
| `reservation_url` | text | ✗ | https://... | 予約システムURL |
| `availability_url` | text | ✗ | https://... | 空き状況URL(同じなら同値) |
| `data_confidence` | text | ✓ | `B` | CHECK: A/B/C |
| `last_verified_at` | timestamptz | ✓ | 2026-05-21 | 手動確認した最終日時 |
| `notes` | text | ✗ | スパイク不可 | 自由記述 |
| `created_at` | timestamptz | ✓ | `now()` | |
| `updated_at` | timestamptz | ✓ | `now()` | トリガで自動更新 |

**インデックス:**
- `(municipality)`, `(municipality, indoor_outdoor)`
- GIST `(point(longitude, latitude))` — 距離検索用
- `(surface_type)`, `(lighting_available)` — 絞り込み用

---

### `facility_sports` — 施設×競技 (多対多)

| カラム | 型 | 必須 | 補足 |
|---|---|---|---|
| `facility_id` | uuid FK | ✓ | facilities.id |
| `sport` | text | ✓ | CHECK: tennis/soccer/futsal/multi/baseball/basketball/volleyball |
| PRIMARY KEY | (facility_id, sport) | | |

`tennis_available`/`soccer_available` のフラグ列を廃止して拡張性確保。

---

### `facility_courts` — コート個別管理 ※Phase 2以降に有効化

1施設内でサーフェス・面数が混在するときのみ使う。MVPは未使用。

| カラム | 型 | 必須 | 補足 |
|---|---|---|---|
| `id` | uuid PK | ✓ | |
| `facility_id` | uuid FK | ✓ | |
| `court_number` | int | ✗ | 1, 2, 3... |
| `court_name` | text | ✗ | A面、人工芝コートなど |
| `surface_type` | text | ✗ | facilities.surface_type と独立 |
| `lighting_available` | boolean | ✗ | |

---

### `availability_current` — 最新空き状況（表示用）

検索結果・空きカレンダー表示で使う。施設×日×時間スロット で UNIQUE。

| カラム | 型 | 必須 | 例 | 補足 |
|---|---|---|---|---|
| `id` | bigserial PK | ✓ | | |
| `facility_id` | uuid FK | ✓ | | |
| `target_date` | date | ✓ | 2026-06-15 | |
| `start_time` | time | ✓ | 18:00 | |
| `end_time` | time | ✓ | 20:00 | |
| `availability_status` | text | ✓ | `空き` | CHECK: 空き/一部空き/満/不明/休館 |
| `available_court_count` | int | ✗ | 3 | |
| `source` | text | ✓ | `scrape` | CHECK: scrape/manual/api |
| `last_checked_at` | timestamptz | ✓ | | 取得時刻 |
| UNIQUE | (facility_id, target_date, start_time) | | | upsert キー |

**インデックス:**
- `(target_date, availability_status)` — 「今日の空き」検索
- `(facility_id, target_date)` — 施設詳細のカレンダー表示

---

### `availability_snapshots` — 時系列蓄積（分析用）⭐ v2 で新規追加

取得ごとに行を追加し、稼働率・キャンセル推移を時系列で残す。Phase 4 の自治体SaaSの核データ。

| カラム | 型 | 必須 | 補足 |
|---|---|---|---|
| `id` | bigserial PK | ✓ | |
| `facility_id` | uuid FK | ✓ | |
| `target_date` | date | ✓ | |
| `start_time` | time | ✓ | |
| `end_time` | time | ✓ | |
| `availability_status` | text | ✓ | |
| `available_court_count` | int | ✗ | |
| `source` | text | ✓ | scrape/manual/api |
| `snapshot_at` | timestamptz | ✓ | 取得時刻 (now()) |

**インデックス:**
- `(facility_id, target_date, snapshot_at DESC)` — 施設の履歴取得
- `(snapshot_at)` — 古いデータの一括削除/集計用
- 月単位パーティション化推奨（容量1500万行/年想定）

**運用ルール:**
- スクレイパー成功時に必ず1行追加
- 3ヶ月以上前のデータは `availability_stats_monthly`（後述）に集計後、削除可

---

### `availability_stats_monthly` — 月次集計 ※Phase 3以降

`availability_snapshots` を曜日×時間帯×施設で集計したサマリ。

| カラム | 型 | 補足 |
|---|---|---|
| `facility_id` | uuid FK | |
| `year_month` | char(7) | "2026-06" |
| `day_of_week` | int | 0=日 〜 6=土 |
| `time_slot` | text | "18:00-20:00" |
| `available_ratio` | numeric(4,3) | 0.000〜1.000 (空き発生率) |
| `sample_count` | int | スナップショット件数 |

---

### `scraping_jobs` — 取得ログ

データ鮮度の根拠と運用品質モニタリング。

| カラム | 型 | 必須 | 補足 |
|---|---|---|---|
| `id` | bigserial PK | ✓ | |
| `municipality` | text | ✓ | |
| `sport` | text | ✗ | |
| `scraper_name` | text | ✓ | machikagi-nagano-tennis等 |
| `scraper_version` | text | ✓ | |
| `started_at` | timestamptz | ✓ | |
| `finished_at` | timestamptz | ✗ | |
| `status` | text | ✓ | CHECK: running/success/partial/error |
| `records_fetched` | int | ✗ | |
| `error_message` | text | ✗ | |

---

### `users` — ユーザー ※Phase 2以降

Supabase Auth 連携前提なので最小限。

| カラム | 型 | 補足 |
|---|---|---|
| `id` | uuid PK | auth.users.id と同期 |
| `display_name` | text | |
| `home_municipality` | text | |
| `created_at` | timestamptz | |

---

### `favorites` — お気に入り ※Phase 2以降

| カラム | 型 | 補足 |
|---|---|---|
| `user_id` | uuid FK | |
| `facility_id` | uuid FK | |
| `created_at` | timestamptz | |
| PRIMARY KEY | (user_id, facility_id) | |

---

### `notification_rules` — 空き通知ルール ※Phase 3以降

| カラム | 型 | 補足 |
|---|---|---|
| `id` | uuid PK | |
| `user_id` | uuid FK | |
| `facility_id` | uuid FK | nullable (条件のみでも可) |
| `sport` | text | |
| `municipality` | text | |
| `day_of_week_mask` | int | bit mask |
| `time_range_start`, `time_range_end` | time | |
| `surface_type` | text | nullable |
| `lighting_required` | boolean | |
| `channel` | text | line/email |
| `active` | boolean | |

---

## Phase 1 で実際に作るテーブル

⭐ MVP（6月末ベータ）では以下だけ作る:
- `facilities`
- `facility_sports`
- `availability_current`
- `availability_snapshots` ⭐ Day 1 から蓄積開始
- `scraping_jobs`

未作成テーブル（`facility_courts`, `users`, `favorites`, `notification_rules`, `availability_stats_monthly`）は migration を Phase 2-3 で順次追加。

---

## Changelog

### v2.0.1 (2026-05-23)
- `facilities.address` を nullable に変更（候補登録段階の施設で住所未取得を許容）

### v2.0 (2026-05-23)
- `availability_snapshots` 新設（時系列蓄積）
- `facility_attributes` を `facilities` に統合（1:1 関係のため）
- 競技対応をフラグ列から `facility_sports` 多対多テーブルへ
- `fee_text` / `fee_structure` の二段構え採用
- `scraping_jobs` 新設（運用品質モニタリング）
- ユーザー意思決定2026-05-23反映: 長野市1市集中スタート、6月末ベータ目標

### v1.0 (2026-05-21)
- 初版 (XLSX [public_sports_facility_mvp_database_architecture_updated.xlsx](../public_sports_facility_mvp_database_architecture_updated.xlsx))
