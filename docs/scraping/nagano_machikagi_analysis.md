# 長野市まちかぎリモート 実地調査レポート

- **対象システム**: https://city.nagano.nagano.machikagi-remote.jp/
- **運営**: 株式会社ライナフ
- **調査日**: 2026-05-23
- **目的**: PoCスクレイパー設計の前提情報整理

---

## エグゼクティブサマリー（最重要発見）

⭐ **スクレイピング対象を「空き状況のみ」に局所化できる**

理由：施設属性（面数・サーフェス・料金・営業時間・電話番号）は、**長野市公式ページの個別施設ページから取得可能**。御厨テニスコートで確認したところ、面数(2面)・サーフェス(全天候型舗装)・営業時間(夏冬で異なる)・電話番号まで掲載されている。

**これによる帰結:**
- 法務リスクのある「予約システムからの取得」は空き状況だけに絞れる
- 静的属性は手動コピー（または公式ページの簡易スクレイピング＝こちらはリスク低）でカバー
- スクレイパー保守の対象を最小化できる

---

## システム構造分析

### URL設計（判明分）

| 用途 | URL パターン | 例 |
|---|---|---|
| ホーム | `/` | https://city.nagano.nagano.machikagi-remote.jp/ |
| 施設一覧 | `/facilities` | ページネーション付き (1, 2, 3, ... 6) |
| 施設詳細 | `/facilities/{ID}` | `/facilities/42` |
| 部屋(コート)一覧 | `/rooms?facility_id={ID}` | 個別コートの予約状況 |
| カテゴリ検索 | `/rooms?tag={NUMBER}` | `tag=1` で体育館 |
| ログイン | `/login` | 予約には必要 |

### 技術的観察

| 項目 | 内容 |
|---|---|
| 推定基盤 | Ruby on Rails or 類似フレームワーク（URL設計から推測） |
| レンダリング | 一覧は静的HTML、検索UIは一部SPA要素あり |
| 認証 | 閲覧は不要、予約は要ログイン |
| 施設総数 | 約70施設（ページネーション6ページ） |
| Robots.txt | 存在するが標準コメントのみ。Disallow指定なし |
| 利用規約 | トップページに明示リンクなし。要追加調査（PDF or 別ページ） |

### スクレイピング難易度評価

| 取得対象 | 難易度 | 手段 |
|---|---|---|
| 施設一覧（IDマッピング） | **低** | HTML直接解析（`/facilities?page=N`を1〜6巡回） |
| 部屋(コート)構成 | **低〜中** | `/rooms?facility_id={ID}` の解析 |
| 空き状況カレンダー | **中** | おそらく日付指定パラメータあり。Playwright必要かも |
| 予約画面 | （取得しない） | ログイン必須・利用規約違反リスク高 |

---

## 長野市公式ページからの属性取得（重要）

### 取得実験：御厨テニスコート

| 項目 | 取得結果 |
|---|---|
| URL | https://www.city.nagano.nagano.jp/n155400/contents/p003066.html |
| 面数 | 2面 |
| サーフェス | 全天候型舗装 |
| ナイター | なし |
| 利用時間（冬） | 8:30〜日没 |
| 利用時間（夏） | 6:30〜日没 |
| 電話番号 | 026-224-5083（市スポーツ課） |
| 住所 | 長野市川中島町御厨562 |
| 料金 | PDF: `/documents/3274/119446.pdf` |

### 24件のテニスコート個別ページURL

[`data/research/nagano_facilities_research.csv`](../data/research/nagano_facilities_research.csv) に全件マッピング済。

### 北部スポーツ・レクリエーションパーク屋内運動場（重要）

- URL: `/n155400/contents/p003100.html`
- **テニス4面 + フットサル2面 + ゲートボール6面** の多目的屋内施設
- 砂入り人工芝
- 個人利用2時間1,220円〜
- 照明料金: 全面810円/時間
- 営業時間: 8:30〜21:00
- 電話: 026-266-0582 (専用)
- → 現在は `NAG-SOC-003` だが、**テニスも提供している** ため `facility_sports` に `tennis` 追加が必要

---

## 利用規約の状況

### 観察済の事実

- ホームページ・施設一覧ページ・robots.txt のいずれにも「スクレイピング禁止」の明示記載なし
- ライナフ社のサービス利用規約は **本サイトからリンクされていない**
- 長野市側の「ながの電子申請サービス利用案内」が一次情報

### 不確実性が残る事項

- ⚠️ 全文を網羅できているわけではない。**深い階層の利用規約ページが存在する可能性**
- ⚠️ ライナフ社のサービス契約上の制約はBtoB契約のため不明
- ⚠️ 長野市の電子申請利用規約に間接的な制約がある可能性

### Phase 1 での運用方針

1. **PoCは1施設・1日分のみ**で技術検証
2. **取得間隔は最短15秒**（自治体システム配慮で長め）
3. **深夜帯 02:00-04:00 JST に集約**
4. **User-Agent明示**: `NaganoSportsFinder/0.1 (+contact@example.com)`
5. **問い合わせ窓口設置 → 24h以内に取得停止対応**
6. **ベータ公開前に弁護士1時間レビュー**（必須）

---

## PoC スクレイパー設計（Week 2 で実装）

### Step 1: 施設IDマッピング（半日）

`/facilities?page=1..6` を巡回し、`(施設名, facility ID)` のマッピング表を作る。これを `facilities.reservation_url` に書き戻す。

```python
# 擬似コード
for page in range(1, 7):
    html = fetch(f"/facilities?page={page}")
    for link in parse_links(html, "a[href^='/facilities/']"):
        facility_id = extract_id(link.href)
        facility_name = link.text
        # 長野市公式の名前と突き合わせて NAG-TEN-* にマッピング
```

### Step 2: 空き状況取得（1日）

判明した URL パターンで `(facility_id, date)` から空き状況を取得。

```python
# 擬似コード
for facility_id in tennis_facility_ids:
    for date in next_30_days:
        slots = fetch_availability(facility_id, date)
        upsert_availability_current(slots)
        insert_availability_snapshots(slots)
```

### Step 3: 取得ログ整備（半日）

`scraping_jobs` テーブルへの記録、エラー時の指数バックオフ、Discord/Slack 通知。

### Step 4: 1週間連続稼働テスト

ローカルcronで深夜帯のみ実行。データ整合性を毎朝確認。

---

## 次のアクション

- [ ] **手動**: 長野市まちかぎリモートを実際にブラウザで開いて利用規約PDFを探索（フッター・ヘルプ・FAQ）
- [ ] **手動**: Phase 1.5 で参考にする他自治体での「まちかぎリモート」採用例の運用実態確認
- [ ] **Week 2**: PoCスクレイパー実装（上記4ステップ）
- [ ] **Week 1並行**: 32施設の属性手動補完（次セクション参照）

---

## 関連ドキュメント

- 利用規約調査全体: [`docs/legal_check_phase1.md`](../legal_check_phase1.md)
- 施設研究テンプレート: [`data/research/nagano_facilities_research.csv`](../../data/research/nagano_facilities_research.csv)
- 研究作業ガイド: [`docs/research_guide.md`](../research_guide.md)
