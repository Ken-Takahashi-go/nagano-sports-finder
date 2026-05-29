# Web (Next.js) セットアップ手順

長野県公共施設ナビのフロントエンド。Next.js 14 (App Router) + TypeScript + Tailwind CSS + Supabase。

---

## 前提

- **Node.js 20 LTS 以上** がインストールされていること

未インストールなら https://nodejs.org/ja からダウンロード（左の「LTS」ボタン）。インストール後にPowerShellを再起動。

```powershell
node -v   # v20.x.x が表示されればOK
npm -v
```

---

## ステップ 1: 依存パッケージのインストール（3〜5分）

PowerShellで以下を実行：

```powershell
cd "C:\Users\user\長野県公共施設ナビ\web"
npm install
```

`node_modules/` フォルダが作られ、約400MB分のパッケージが入ります。Warningはほぼ無視してOK。

---

## ステップ 2: 環境変数の設定（1分）

```powershell
Copy-Item .env.local.example .env.local
notepad .env.local
```

ファイルが開いたら、プロジェクトルートの `..\.env.local` と同じ値を入れます：

```
NEXT_PUBLIC_SUPABASE_URL=https://kqrfltdpcptymqxctikv.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_xxxxxxxxx
```

保存して閉じる。

> **注**: `SUPABASE_SERVICE_ROLE_KEY` はフロントエンドには不要なので書きません（書くとブラウザに漏れます）。

---

## ステップ 3: 開発サーバー起動（30秒）

```powershell
npm run dev
```

数秒待って下記のような表示が出れば成功：

```
   ▲ Next.js 14.2.x
   - Local:        http://localhost:3000
 ✓ Ready in 2.3s
```

ブラウザで http://localhost:3000 を開くと、TOPページが表示されます。

---

## 動作確認

- **TOPページ** (`/`) — 統計、クイック導線、ナイター可能テニス施設6件のリスト
- **検索ページ** (`/search?sport=tennis&lighting=true`) — フィルタ付き一覧
- **詳細ページ** (`/facilities/NAG-TEN-019`) — 南長野運動公園16面の詳細

### TOPに表示される数字の期待値（seed 001〜004 実行後）

- 登録施設数: 31
- 合計コート面数: 約80+面（テニスのみで70+）
- ナイター可能テニス: 6

---

## ディレクトリ構成

```
web/
├── app/                       Next.js App Router
│   ├── layout.tsx             共通レイアウト(ヘッダー・フッター)
│   ├── page.tsx               TOPページ
│   ├── globals.css            全体CSS
│   ├── not-found.tsx          404
│   ├── search/page.tsx        検索結果
│   └── facilities/[code]/page.tsx  施設詳細
├── components/
│   └── FacilityCard.tsx       施設カード(共通)
├── lib/
│   ├── supabase.ts            Supabaseクライアント
│   ├── types.ts               DB型定義
│   └── queries.ts             DBクエリ関数
├── public/                    画像等(なし)
├── .env.local                 環境変数(gitignore)
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── next.config.js
```

---

## よくあるエラー

### `Error: Supabase URL/anon key が未設定です`
→ `.env.local` の中身を確認。`NEXT_PUBLIC_` 接頭辞を忘れていないか。サーバーを Ctrl+C で停止して `npm run dev` 再実行。

### `relation "facilities" does not exist`
→ Supabase に migration が当たっていない。Supabaseダッシュボードで `db/migrations/001_initial_schema.sql` を再実行。

### TOPページの数字が `0` 件
→ seed が当たっていない。`db/seeds/001_nagano_facilities.sql` → `002` → `003` → `004` の順で全部当て直す。

### ポート3000が使われている
→ `npm run dev -- -p 3001` で別ポートで起動。

### 日本語が文字化け
→ ファイル保存時のエンコーディング確認。VS Code 推奨。

---

## 次のステップ

- スクレイパー実装 (Phase 1 Week 2)
- 空き状況表示の追加 (availability_current テーブル参照)
- 地図表示 (Google Maps API)
- SEO設定 (sitemap.xml, robots.txt, 構造化データ)

---

## 本番デプロイ (Phase 1 Week 5 で実施)

Vercel 推奨。GitHubリポジトリを作って Push → Vercelダッシュボードで Import → 環境変数 (NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY) を設定 → 自動デプロイ。
