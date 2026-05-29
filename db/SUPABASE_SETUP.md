# Supabase セットアップ手順 — Phase 1 Week 1

長野県公共施設ナビ MVP の Supabase 環境を構築します。所要時間は **30〜45分**。

---

## 前提

- メールアドレス
- GitHubアカウント（任意・Supabaseサインアップで使うと楽）
- ブラウザ（Chrome/Edge推奨）

---

## ステップ 1: Supabase プロジェクト作成（10分）

1. **アクセス**: https://supabase.com にアクセス
2. **Start your project** → GitHubでサインアップ（推奨）またはメール登録
3. ダッシュボードで **New project** をクリック
4. プロジェクト設定:
   - **Name**: `nagano-sports-finder`
   - **Database Password**: 強いパスワードを生成（**必ず保存** ─ 1Password等）
   - **Region**: `Northeast Asia (Tokyo)`
   - **Pricing Plan**: Free（500MB DB、十分）
5. **Create new project** をクリック → 2-3分待つ

### 保存しておく情報

ダッシュボード `Project Settings → API` から以下をコピーし、ローカルの安全な場所に保存：

```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...               # フロントエンド用（公開OK）
SUPABASE_SERVICE_ROLE_KEY=eyJ...       # バックエンド用（絶対公開禁止）
```

---

## ステップ 2: スキーマ適用（5分）

1. ダッシュボード左メニュー **SQL Editor** を開く
2. **New query** をクリック
3. 以下のファイルの内容をすべてコピーして貼り付け:

   [`db/migrations/001_initial_schema.sql`](migrations/001_initial_schema.sql)

4. 右下の **Run** をクリック
5. **Success. No rows returned** が出れば成功
6. 左メニュー **Table Editor** で以下5テーブルが見えれば OK:
   - `facilities`
   - `facility_sports`
   - `availability_current`
   - `availability_snapshots`
   - `scraping_jobs`

### トラブル時

- エラー `extension "earthdistance" is not allowed` → 該当行を削除して再実行（距離検索は後で対応）
- エラー `permission denied for schema public` → Database Password の打ち間違いか、プロジェクト作成が完了していない

---

## ステップ 3: 初期データ投入（5分）

1. **SQL Editor** で **New query**
2. 以下のファイルの内容をコピペ:

   [`db/seeds/001_nagano_facilities.sql`](seeds/001_nagano_facilities.sql)

3. **Run** をクリック
4. **Success** が出れば成功

### 確認

新しいクエリで以下を実行:

```sql
-- 件数確認
select municipality, count(*) as total from facilities group by municipality;
-- 期待値: 長野市 | 32

-- 競技別件数
select sport, count(*) from facility_sports group by sport;
-- 期待値: tennis | 24, soccer | 8, futsal | 8

-- データ信頼度別
select data_confidence, count(*) from facilities group by data_confidence;
-- 期待値: B | 24 (テニス), C | 8 (サッカー系)

-- サンプル表示
select facility_code, facility_name, booking_method, data_confidence
from facilities
order by facility_code
limit 10;
```

---

## ステップ 4: Row Level Security の動作確認（5分）

1. **Table Editor → facilities → Authentication**: 「RLS enabled」になっていることを確認
2. 別ブラウザ（シークレットモード）で anon key を使ってアクセスし、SELECT は可能、INSERT/UPDATE は拒否されることを確認

軽く動作確認するには、SQL Editor で以下:

```sql
-- 公開読み取りができることを確認
set role anon;
select count(*) from facilities;  -- 32 が返るはず
select count(*) from availability_snapshots;  -- 0 が返るはず（読み取り自体は可能）
reset role;
```

---

## ステップ 5: 環境変数の保管（5分）

プロジェクトルート（`C:\Users\user\長野県公共施設ナビ\`）に `.env.local.example` と `.env.local` を分けて作成：

```bash
# .env.local (gitignoreに必ず追加！絶対にコミットしない)
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...    # スクレイパー用
```

`.gitignore` に以下を追加:
```
.env.local
.env*.local
docs/legal/*.pdf   # 利用規約PDFはローカル保存のみ
```

---

## 次のアクション (Week 1 残タスク)

- [ ] 長野市まちかぎリモートの実地ブラウジング調査
- [ ] 利用規約PDFをローカル保存 → `docs/legal/nagano_machikagi_terms_20260524.pdf` 等
- [ ] 32施設の詳細属性手動補完（サーフェス・ナイター・面数を可能な範囲で）

---

## トラブルシューティング

### Q. SQL実行時に「conflicting key constraint」エラー
A. seed が複数回実行された可能性。`001_nagano_facilities.sql` の冒頭に DELETE 文があるので、再実行で重複は解消されます。

### Q. SQL Editor で日本語が文字化け
A. ブラウザのUTF-8設定を確認。または開発者ツール（F12）で `document.charset` を確認。

### Q. RLS で自分が SELECT できなくなった
A. SQL Editor は `service_role` で動くので影響なし。anon キーから読めないなら policy を再確認。

### Q. 環境変数を間違えてコミットしてしまった
A. すぐに Supabase ダッシュボードで Database Password と API Key をローテートする → `git filter-branch` か新規リポジトリ作り直し。
