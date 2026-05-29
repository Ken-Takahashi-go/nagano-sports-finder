"""
Stage 2-E: 発見した JSON エンドポイントの中身を取得・解析

エンドポイント (room_id=299 で発見):
  - /rooms/{room_id}/reservation_calendar.json
  - /rooms/{room_id}/availability.json

これらが空き状況データを返すか、追加パラメータが必要かを検証する。
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.syntax import Syntax

SCRIPT_DIR = Path(__file__).parent
load_dotenv(SCRIPT_DIR / ".env")

BASE_URL = os.getenv("MACHIKAGI_BASE_URL", "https://city.nagano.nagano.machikagi-remote.jp")
SCRAPER_NAME = os.getenv("SCRAPER_NAME", "NaganoSportsFinder")
SCRAPER_VERSION = os.getenv("SCRAPER_VERSION", "0.1.0")
SCRAPER_CONTACT = os.getenv("SCRAPER_CONTACT", "contact@example.com")
INTERVAL = int(os.getenv("REQUEST_INTERVAL_SECONDS", "15"))
USER_AGENT = f"{SCRAPER_NAME}/{SCRAPER_VERSION} (+{SCRAPER_CONTACT})"

TARGET_ROOM = 299
SETTING_ID = "84"
OUTPUTS = SCRIPT_DIR / "outputs"

console = Console()


def fetch_and_save_json(
    client: httpx.Client, path: str, params: dict, label: str
) -> dict | list | None:
    """JSON エンドポイントを取得して保存・解析"""
    url = BASE_URL + path
    console.print(f"\n[cyan]GET[/cyan] {url}")
    console.print(f"  params={params}")

    r = client.get(url, params=params, timeout=30.0)
    console.print(f"  → status: [bold]{r.status_code}[/bold], size: {len(r.text):,} bytes, "
                  f"content-type: {r.headers.get('content-type', '?')}")

    if r.status_code != 200:
        console.print(f"  [red]non-200, body: {r.text[:200]}[/red]")
        return None

    # JSONパース試行
    try:
        data = r.json()
    except Exception as e:
        console.print(f"  [yellow]not JSON: {e}[/yellow]")
        # 先頭500バイトを保存
        save_path = OUTPUTS / f"stage2e_{label}.txt"
        save_path.write_text(r.text, encoding="utf-8")
        console.print(f"  → saved {save_path.relative_to(SCRIPT_DIR)}")
        return None

    # 保存
    save_path = OUTPUTS / f"stage2e_{label}.json"
    save_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"  → saved {save_path.relative_to(SCRIPT_DIR)}")

    # 構造解析
    console.print(f"\n  [bold]構造:[/bold]")
    if isinstance(data, dict):
        for k, v in data.items():
            vtype = type(v).__name__
            if isinstance(v, list):
                hint = f"({len(v)} items)"
            elif isinstance(v, dict):
                hint = f"({len(v)} keys)"
            elif isinstance(v, str):
                hint = f'"{v[:30]}..."' if len(v) > 30 else f'"{v}"'
            else:
                hint = str(v)
            console.print(f"    {k}: [yellow]{vtype}[/yellow] {hint}")
    elif isinstance(data, list):
        console.print(f"    list (length={len(data)})")
        if data:
            sample = data[0]
            if isinstance(sample, dict):
                console.print(f"    各要素のキー: {list(sample.keys())}")

    # サンプルJSON先頭部分を表示
    pretty = json.dumps(data, ensure_ascii=False, indent=2)
    snippet = pretty[:800] if len(pretty) > 800 else pretty
    console.print(f"\n  [bold]サンプル (先頭800文字):[/bold]")
    console.print(Syntax(snippet, "json", theme="monokai", line_numbers=False, word_wrap=True))

    return data


def main() -> int:
    console.print(f"[bold green]Stage 2-E: JSONエンドポイント取得・解析[/bold green]")
    console.print(f"対象: room_id={TARGET_ROOM}\n")

    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.5",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",  # Ajax扱いにする
    }

    target_date = (date.today() + timedelta(days=7)).isoformat()

    # 試行パターン
    trials = [
        # (path, params, label)
        (f"/rooms/{TARGET_ROOM}/reservation_calendar.json", {}, "calendar_noparam"),
        (f"/rooms/{TARGET_ROOM}/reservation_calendar.json",
         {"requested_setting_id": SETTING_ID}, "calendar_setting"),
        (f"/rooms/{TARGET_ROOM}/reservation_calendar.json",
         {"requested_setting_id": SETTING_ID, "date": target_date},
         "calendar_setting_date"),
        (f"/rooms/{TARGET_ROOM}/availability.json", {}, "availability_noparam"),
        (f"/rooms/{TARGET_ROOM}/availability.json",
         {"requested_setting_id": SETTING_ID}, "availability_setting"),
        (f"/rooms/{TARGET_ROOM}/availability.json",
         {"date": target_date}, "availability_date"),
    ]

    with httpx.Client(headers=headers, follow_redirects=True) as client:
        for i, (path, params, label) in enumerate(trials):
            fetch_and_save_json(client, path, params, label)
            if i < len(trials) - 1:
                console.print(f"\n  [dim]sleeping {INTERVAL}s...[/dim]")
                time.sleep(INTERVAL)

    console.print(f"\n[bold green]✓ 完了[/bold green]")
    console.print(f"  outputs/stage2e_*.json を確認して、最も情報量の多いパターンを特定")

    return 0


if __name__ == "__main__":
    sys.exit(main())
