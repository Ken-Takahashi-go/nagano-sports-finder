"""
松本市 webR スクレイパー (Phase 1.5)

長野市まちかぎリモートと同様の方針：
  1. Playwright で実画面を取得し、Network タブで実 Ajax URL を発見
  2. 発見した URL を httpx で直接叩いて軽量・高速化

ディレクトリ構成:
  - stageM1_explore_webR.py    : 構造解析
  - stageM2_facility_map.py    : 施設ID マッピング
  - stageM3_fetch_availability.py : 空き状況取得 PoC
  - stageM_full.py             : 全件取得 (stage2j相当)
"""
