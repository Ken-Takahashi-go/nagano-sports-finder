# 長野県公共施設ナビ — Scraper

## 定期実行 (GitHub Actions)

毎日 JST 02:30 に自動実行されます (`.github/workflows/scrape.yml`)。
手動実行は GitHub の Actions タブ → "Daily Scrape Availability" → "Run workflow" から可能。



長野市まちかぎリモートから空き状況等を取得するスクレイパー。

## ステージ

| Stage | 内容 | スクリプト | 完了 |
|---|---|---|---|
| 0 | 環境構築 | (本READMEのセットアップ) | - |
| 1 | 施設IDマッピング | `stage1_fetch_facility_list.py` | ✅ 実装済 |
| 2 | 空き状況取得 (PoC) | `stage2_*.py` | ⏳ 未実装 |
| 3 | 全施設・複数日対応 | `stage3_*.py` | ⏳ 未実装 |
| 4 | 定期実行 (cron / Task Scheduler) | - | ⏳ 未実装 |

## 法務遵守事項

- User-Agent明示: `NaganoSportsFinder/0.1.0 (+contact@example.com)`
- 取得間隔: 最短 **15秒/req** (env で調整可)
- 取得対象: 空き状況のみ (個人情報・予約者情報は取得しない)
- 出典明示: フロントエンドに「データ提供元: 長野市公共施設予約システム」を表示済
- 問い合わせ受付: 24時間以内に取得停止対応

詳細は [`../docs/legal_check_phase1.md`](../docs/legal_check_phase1.md) 参照。

## セットアップ

### 1. 仮想環境作成 (1回だけ)

```powershell
cd "C:\Users\user\長野県公共施設ナビ\scraper"
python -m venv .venv
```

### 2. 仮想環境有効化 (毎回)

```powershell
.\.venv\Scripts\Activate.ps1
```

> 初回エラーが出たら `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` を一度実行

プロンプトの左に `(.venv)` が出れば有効化成功。

### 3. 依存パッケージインストール (1回だけ)

```powershell
pip install -r requirements.txt
```

### 4. 環境変数設定 (1回だけ)

```powershell
Copy-Item .env.example .env
notepad .env
```

中身を実値に置き換えて保存。

## 実行

### Stage 1 — 施設IDマッピング取得

```powershell
python stage1_fetch_facility_list.py
```

実行時間: 約2分 (15秒×6ページ + 処理時間)

出力:
- `outputs/raw_page_1.html` 〜 `raw_page_6.html` — デバッグ用生HTML
- `outputs/machikagi_facility_list.json` — 構造化された施設リスト

期待値: 70施設前後 (まちかぎリモートに登録された長野市公共施設全件)

## トラブル時

### `python` コマンドが見つからない
- Python 3.12+ がPATHに通っているか `python --version` で確認

### 仮想環境の Activate.ps1 が実行できない
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### `403 Forbidden` などのエラー
- User-Agent が空かもしれない → .env を確認
- 取得間隔が短すぎる可能性 → REQUEST_INTERVAL_SECONDS を 30 に増やす

### 全くデータが取れない
- まちかぎリモートのHTML構造が変わった可能性
- `outputs/raw_page_1.html` を直接ブラウザで開いて、施設リンクの構造を確認
- `parse_facility_list()` の CSSセレクタを調整
