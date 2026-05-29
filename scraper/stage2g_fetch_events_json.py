"""
Stage 2-G: 本物のJSON APIを直接叩いて予約イベントを取得

エンドポイント (Playwrightのネットワーク観察で発見):
  GET /rooms/{room_id}/reservation_events.json
  ?start=YYYY-MM-DD&end=YYYY-MM-DD&requested_setting_id={X}

これが空き状況の本物データソース。Playwright不要で軽量・高速。
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

SCRIPT_DIR = Path(__file__).parent
load_dotenv(SCRIPT_DIR / ".env")

BASE_URL = os.getenv("MACHIKAGI_BASE_URL", "https://city.nagano.nagano.machikagi-remote.jp")
SCRAPER_NAME = os.getenv("SCRAPER_NAME", "NaganoSportsFinder")
SCRAPER_VERSION = os.getenv("SCRAPER_VERSION", "0.1.0")
SCRAPER_CONTACT = os.getenv("SCRAPER_CONTACT", "contact@example.com")
USER_AGENT = f"{SCRAPER_NAME}/{SCRAPER_VERSION} (+{SCRAPER_CONTACT})"

OUTPUTS = SCRIPT_DIR / "outputs"
TARGET_ROOM = 299
SETTING_ID = "84"

console = Console()


def main() -> int:
    console.print(f"[bold green]Stage 2-G: 本物JSONエンドポイント直接取得[/bold green]")
    console.print(f"対象: room_id={TARGET_ROOM}, setting_id={SETTING_ID}\n")

    # 取得期間: 今日から30日先まで
    start = date.today().isoformat()
    end = (date.today() + timedelta(days=30)).isoformat()

    url = f"{BASE_URL}/rooms/{TARGET_ROOM}/reservation_events.json"
    params = {
        "start": start,
        "end": end,
        "requested_setting_id": SETTING_ID,
    }

    headers = {
        # 重要: XHR扱いにする (RailsはこれでJSON返してくれる)
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "ja-JP,ja;q=0.9",
        # User-Agentにブラウザ風文字列+識別子を入れる
        "User-Agent": (
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/120.0.0.0 Safari/537.36 "
            f"{USER_AGENT}"
        ),
        # Referer も付ける (一部のサイトはチェックする)
        "Referer": f"{BASE_URL}/rooms/{TARGET_ROOM}/reservation_calendar?requested_setting_id={SETTING_ID}",
    }

    console.print(f"[cyan]GET[/cyan] {url}")
    console.print(f"  params={params}")
    console.print()

    with httpx.Client(headers=headers, follow_redirects=True) as client:
        response = client.get(url, params=params, timeout=30.0)

    console.print(f"[bold]レスポンス:[/bold]")
    console.print(f"  status: {response.status_code}")
    console.print(f"  content-type: {response.headers.get('content-type', '?')}")
    console.print(f"  size: {len(response.text):,} bytes")
    console.print()

    if response.status_code != 200:
        console.print(f"[red]ERROR: non-200, body:[/red]")
        console.print(response.text[:500])
        return 1

    # 保存
    save_path = OUTPUTS / "stage2g_events.json"
    save_path.write_text(response.text, encoding="utf-8")
    console.print(f"[green]✓ 保存: {save_path.relative_to(SCRIPT_DIR)}[/green]\n")

    # JSONパース
    try:
        data = response.json()
    except Exception as e:
        console.print(f"[red]not JSON: {e}[/red]")
        console.print(response.text[:1000])
        return 1

    # 構造解析
    console.print(f"[bold]データ構造:[/bold]")
    if isinstance(data, list):
        console.print(f"  type: list ({len(data)} items)")
        if data:
            sample = data[0]
            console.print(f"  各要素のキー: {list(sample.keys()) if isinstance(sample, dict) else type(sample).__name__}")
    elif isinstance(data, dict):
        console.print(f"  type: dict ({len(data)} keys)")
        for k, v in data.items():
            vtype = type(v).__name__
            if isinstance(v, list):
                console.print(f"    {k}: list ({len(v)} items)")
            elif isinstance(v, dict):
                console.print(f"    {k}: dict ({len(v)} keys)")
            else:
                console.print(f"    {k}: {vtype} {str(v)[:50]}")
    console.print()

    # サンプル先頭5件をテーブル表示
    items = data if isinstance(data, list) else (data.get("events") or [])

    if items:
        console.print(f"[bold]サンプル先頭5件:[/bold]")
        table = Table(show_lines=False)
        sample_keys = list(items[0].keys()) if isinstance(items[0], dict) else []
        for k in sample_keys[:8]:  # 最初の8キーだけ
            table.add_column(k, style="cyan", overflow="fold")
        for item in items[:5]:
            row = []
            for k in sample_keys[:8]:
                v = item.get(k, "")
                row.append(str(v)[:30])
            table.add_row(*row)
        console.print(table)
        console.print()

    # JSON先頭部分をシンタックスハイライト表示
    pretty = json.dumps(data, ensure_ascii=False, indent=2)
    snippet = pretty[:1500] if len(pretty) > 1500 else pretty
    console.print(f"[bold]JSON先頭部分:[/bold]")
    console.print(Syntax(snippet, "json", theme="monokai", line_numbers=False, word_wrap=True))
    console.print()

    # ユニーク値カウント
    if items and isinstance(items[0], dict):
        from collections import Counter
        for key in items[0].keys():
            values = [item.get(key) for item in items]
            if all(isinstance(v, (str, int, bool, type(None))) for v in values):
                counter = Counter(values)
                if 1 <= len(counter) <= 10:
                    console.print(f"[bold]{key}[/bold]ユニーク値: {dict(counter)}")

    console.print(f"\n[bold green]✓ 完了。次は全16コート分の取得 (Stage 2-H)[/bold green]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
