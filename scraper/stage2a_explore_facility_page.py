"""
Stage 2-A: 単一施設のmachikagiページ構造を探索する
目的: 空き状況がどのURLで取れるか・ログイン要否・HTML構造を把握する

対象: NAG-TEN-019 (machikagi_id=84) 南長野運動公園テニスコート
理由: 16面ある主力施設で、空き枠の数が多くサンプルとして最適

取得対象URL:
  1. /facilities/84              - 施設詳細
  2. /rooms?facility_id=84       - 部屋(コート)一覧
  3. /reservations/new?facility_id=84  - 予約フォーム(空き状況含む可能性)

使い方: python stage2a_explore_facility_page.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

SCRIPT_DIR = Path(__file__).parent
load_dotenv(SCRIPT_DIR / ".env")

BASE_URL = os.getenv("MACHIKAGI_BASE_URL", "https://city.nagano.nagano.machikagi-remote.jp")
SCRAPER_NAME = os.getenv("SCRAPER_NAME", "NaganoSportsFinder")
SCRAPER_VERSION = os.getenv("SCRAPER_VERSION", "0.1.0")
SCRAPER_CONTACT = os.getenv("SCRAPER_CONTACT", "contact@example.com")
INTERVAL = int(os.getenv("REQUEST_INTERVAL_SECONDS", "15"))
USER_AGENT = f"{SCRAPER_NAME}/{SCRAPER_VERSION} (+{SCRAPER_CONTACT})"

TARGET_FACILITY_ID = 84  # NAG-TEN-019 南長野運動公園テニスコート
TARGET_NAME = "南長野運動公園テニスコート"

OUTPUTS_DIR = SCRIPT_DIR / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

console = Console()


def fetch_and_save(client: httpx.Client, url: str, save_as: str) -> str:
    """URLを取得しHTMLを保存。応答内容を返す"""
    console.print(f"[cyan]GET[/cyan] {url}")
    response = client.get(url, timeout=30.0)
    console.print(f"  → status: [bold]{response.status_code}[/bold], "
                  f"content-length: {len(response.text):,} bytes")
    response.raise_for_status()

    save_path = OUTPUTS_DIR / save_as
    save_path.write_text(response.text, encoding="utf-8")
    console.print(f"  → saved {save_path.relative_to(SCRIPT_DIR)}")

    return response.text


def analyze_html(html: str, label: str) -> dict:
    """HTMLの構造を解析して特徴を抽出"""
    soup = BeautifulSoup(html, "lxml")

    # 主要要素の抽出
    title = soup.title.get_text(strip=True) if soup.title else "(no title)"

    # 表 (空きカレンダーの可能性が高い)
    tables = soup.find_all("table")

    # 日付関連の文字列
    date_keywords = ["月", "日", "曜", "空き", "満", "予約", "受付"]
    date_mentions = sum(1 for kw in date_keywords if kw in html)

    # フォーム
    forms = soup.find_all("form")

    # JSON-LD やインラインJSのデータ
    scripts = soup.find_all("script")
    has_json_data = any("application/json" in (s.get("type") or "") for s in scripts)
    has_calendar_js = any(kw in html for kw in ["calendar", "schedule", "availability"])

    # ログインリンクの存在
    has_login_form = bool(soup.find("input", {"type": "password"}))
    has_login_link = any(
        "ログイン" in (a.get_text() or "") or "login" in (a.get("href") or "").lower()
        for a in soup.find_all("a")
    )

    return {
        "label": label,
        "title": title,
        "tables": len(tables),
        "date_keyword_count": date_mentions,
        "forms": len(forms),
        "has_login_form": has_login_form,
        "has_login_link": has_login_link,
        "has_json_data": has_json_data,
        "has_calendar_js": has_calendar_js,
    }


def main() -> int:
    console.print(f"[bold green]Stage 2-A: まちかぎリモート 単一施設探索[/bold green]")
    console.print(f"対象: facility_id={TARGET_FACILITY_ID} ({TARGET_NAME})")
    console.print()

    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.5",
    }

    urls = [
        (f"{BASE_URL}/facilities/{TARGET_FACILITY_ID}", "stage2_facility_detail.html"),
        (f"{BASE_URL}/rooms?facility_id={TARGET_FACILITY_ID}", "stage2_rooms.html"),
    ]

    results = []

    with httpx.Client(headers=headers, follow_redirects=True) as client:
        for i, (url, save_as) in enumerate(urls):
            try:
                html = fetch_and_save(client, url, save_as)
                analysis = analyze_html(html, save_as)
                results.append(analysis)
            except httpx.HTTPError as e:
                console.print(f"[red]Error: {e}[/red]")
                results.append({"label": save_as, "error": str(e)})

            if i < len(urls) - 1:
                console.print(f"  [dim]sleeping {INTERVAL}s...[/dim]")
                time.sleep(INTERVAL)
            console.print()

    # 結果サマリーテーブル
    table = Table(title="ページ解析結果", show_lines=True)
    table.add_column("URL", style="cyan", no_wrap=False)
    table.add_column("タイトル", style="white")
    table.add_column("テーブル", justify="right")
    table.add_column("日付KW", justify="right")
    table.add_column("フォーム", justify="right")
    table.add_column("ログイン要", justify="center")
    table.add_column("カレンダーJS", justify="center")

    for r in results:
        if "error" in r:
            table.add_row(r["label"], f"[red]ERROR: {r['error']}[/red]", "-", "-", "-", "-", "-")
        else:
            login_needed = "yes" if (r["has_login_form"] or r["has_login_link"]) else "no"
            calendar_js = "yes" if r["has_calendar_js"] else "no"
            table.add_row(
                r["label"],
                r["title"][:40],
                str(r["tables"]),
                str(r["date_keyword_count"]),
                str(r["forms"]),
                login_needed,
                calendar_js,
            )

    console.print(table)
    console.print()

    # 次のステップ提案
    console.print("[bold]次のステップ:[/bold]")
    console.print("  1. outputs/stage2_facility_detail.html を ブラウザで開いて確認")
    console.print("  2. outputs/stage2_rooms.html を ブラウザで開いて確認")
    console.print("  3. 空きカレンダー/予約カレンダーがどこにあるか視認")
    console.print("  4. 空き状況用URLが別にあれば次の探索対象に追加")

    return 0


if __name__ == "__main__":
    sys.exit(main())
