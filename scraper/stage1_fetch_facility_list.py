"""
Stage 1: まちかぎリモートから施設一覧を取得して (machikagi_id, facility_name) ペアを抽出

法務的ガードレール:
  - User-Agent 明示
  - 取得間隔 15秒以上
  - 1回1ページ、6ページのみ
  - 取得HTMLはローカル保存(再パース可能に)

出力:
  - outputs/raw_page_{N}.html: 取得した生HTML (デバッグ用)
  - outputs/machikagi_facility_list.json: パース結果

使い方:
  python stage1_fetch_facility_list.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# ----- 設定 ---------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
load_dotenv(SCRIPT_DIR / ".env")

BASE_URL = os.getenv("MACHIKAGI_BASE_URL", "https://city.nagano.nagano.machikagi-remote.jp")
SCRAPER_NAME = os.getenv("SCRAPER_NAME", "NaganoSportsFinder")
SCRAPER_VERSION = os.getenv("SCRAPER_VERSION", "0.1.0")
SCRAPER_CONTACT = os.getenv("SCRAPER_CONTACT", "contact@example.com")
INTERVAL = int(os.getenv("REQUEST_INTERVAL_SECONDS", "15"))

USER_AGENT = f"{SCRAPER_NAME}/{SCRAPER_VERSION} (+{SCRAPER_CONTACT})"

OUTPUTS_DIR = SCRIPT_DIR / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

console = Console()


# ----- データ構造 ---------------------------------------------------
@dataclass
class MachikagiFacility:
    machikagi_id: str           # まちかぎリモート内のID (例: "42")
    facility_name: str          # 表示名 (例: "長野市営城山テニスコート")
    detail_url: str             # /facilities/{id}
    source_page: int            # 取得元ページ番号


# ----- HTTP 取得 ----------------------------------------------------
def fetch_page(client: httpx.Client, page: int) -> str:
    """指定ページ番号を取得してHTML文字列を返す"""
    url = f"{BASE_URL}/facilities?page={page}"
    console.print(f"[cyan]GET[/cyan] {url}")

    response = client.get(url, timeout=30.0)
    response.raise_for_status()

    # 生HTMLを保存(デバッグ・再パース用)
    raw_path = OUTPUTS_DIR / f"raw_page_{page}.html"
    raw_path.write_text(response.text, encoding="utf-8")
    console.print(f"  → saved {raw_path.relative_to(SCRIPT_DIR)} ({len(response.text):,} bytes)")

    return response.text


# ----- HTML パース --------------------------------------------------
def parse_facility_list(html: str, page: int) -> list[MachikagiFacility]:
    """
    HTMLから (machikagi_id, facility_name) ペアを抽出する。
    URL 構造: /facilities/{ID} へのリンクを探す。
    """
    soup = BeautifulSoup(html, "lxml")
    facilities: list[MachikagiFacility] = []

    # /facilities/{数字} へのリンクを全て収集
    for link in soup.select("a[href]"):
        href: str = link.get("href", "")
        # /facilities/42 のようなパターンにマッチ
        if href.startswith("/facilities/") and href.count("/") == 2:
            # 末尾が数字のみ (page=1 等のクエリは除外)
            tail = href.rsplit("/", 1)[-1]
            if not tail.isdigit():
                continue

            machikagi_id = tail
            name = link.get_text(strip=True)
            if not name:
                continue

            facilities.append(
                MachikagiFacility(
                    machikagi_id=machikagi_id,
                    facility_name=name,
                    detail_url=f"{BASE_URL}{href}",
                    source_page=page,
                )
            )

    return facilities


# ----- メイン --------------------------------------------------------
def main(max_pages: int = 6) -> int:
    console.print(f"[bold green]Stage 1: まちかぎリモート施設一覧取得[/bold green]")
    console.print(f"User-Agent: [dim]{USER_AGENT}[/dim]")
    console.print(f"取得間隔: {INTERVAL} 秒")
    console.print()

    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.5",
    }

    all_facilities: list[MachikagiFacility] = []

    with httpx.Client(headers=headers, follow_redirects=True) as client:
        for page in range(1, max_pages + 1):
            try:
                html = fetch_page(client, page)
            except httpx.HTTPError as e:
                console.print(f"[red]Error fetching page {page}: {e}[/red]")
                continue

            page_facilities = parse_facility_list(html, page)
            console.print(f"  → parsed [bold]{len(page_facilities)}[/bold] facility links")
            all_facilities.extend(page_facilities)

            # 最終ページ以外は sleep
            if page < max_pages:
                console.print(f"  [dim]sleeping {INTERVAL}s...[/dim]")
                time.sleep(INTERVAL)
            console.print()

    # 重複除去 (同じIDが複数ページに登場する可能性は低いが念のため)
    seen_ids: set[str] = set()
    unique_facilities = []
    for f in all_facilities:
        if f.machikagi_id not in seen_ids:
            seen_ids.add(f.machikagi_id)
            unique_facilities.append(f)

    duplicates = len(all_facilities) - len(unique_facilities)
    if duplicates > 0:
        console.print(f"[yellow]重複除去: {duplicates}件[/yellow]")

    # JSON出力
    output_path = OUTPUTS_DIR / "machikagi_facility_list.json"
    output_path.write_text(
        json.dumps([asdict(f) for f in unique_facilities], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    console.print(f"[green]保存完了: {output_path.relative_to(SCRIPT_DIR)}[/green]")
    console.print()

    # 結果サマリー
    console.print(f"[bold]✓ 抽出施設数: {len(unique_facilities)}件[/bold]")
    console.print()

    # 結果テーブル表示 (先頭20件)
    if unique_facilities:
        table = Table(title="抽出された施設 (先頭20件)", show_lines=False)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("施設名", style="white")
        table.add_column("page", style="dim", no_wrap=True)
        for f in unique_facilities[:20]:
            table.add_row(f.machikagi_id, f.facility_name, str(f.source_page))
        console.print(table)
        if len(unique_facilities) > 20:
            console.print(f"[dim]...他 {len(unique_facilities) - 20} 件 (詳細はJSONファイル参照)[/dim]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
