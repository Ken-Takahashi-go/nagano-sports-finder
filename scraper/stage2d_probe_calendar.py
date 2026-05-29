"""
Stage 2-D: 空きカレンダーのデータ取得方法を多角的に調査

仮説:
  A. JSで遅延ロード → HTMLに含まれる <script> や API endpoint hints を探す
  B. 日付パラメータ不足 → &date=YYYY-MM-DD を付けて取得
  C. 別の専用エンドポイント (例: /api/availability, /rooms/N/availability.json)

調査対象: room_id=299 南長野運動公園テニスコート N1面
"""
from __future__ import annotations

import os
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from rich.console import Console

SCRIPT_DIR = Path(__file__).parent
load_dotenv(SCRIPT_DIR / ".env")

BASE_URL = os.getenv("MACHIKAGI_BASE_URL", "https://city.nagano.nagano.machikagi-remote.jp")
SCRAPER_NAME = os.getenv("SCRAPER_NAME", "NaganoSportsFinder")
SCRAPER_VERSION = os.getenv("SCRAPER_VERSION", "0.1.0")
SCRAPER_CONTACT = os.getenv("SCRAPER_CONTACT", "contact@example.com")
INTERVAL = int(os.getenv("REQUEST_INTERVAL_SECONDS", "15"))
USER_AGENT = f"{SCRAPER_NAME}/{SCRAPER_VERSION} (+{SCRAPER_CONTACT})"

OUTPUTS = SCRIPT_DIR / "outputs"
TARGET_ROOM = 299
SETTING_ID = "84"

console = Console()


def hypothesis_a_inspect_html() -> None:
    """既存の保存HTMLからJSのヒントを抽出"""
    path = OUTPUTS / f"stage2_calendar_room{TARGET_ROOM}_setting{SETTING_ID}.html"
    if not path.exists():
        console.print(f"[red]ERROR: {path} が無い。先にstage2cを実行[/red]")
        return

    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    console.print(f"[bold cyan]仮説A: HTMLに埋まったJSヒントを探す[/bold cyan]")

    # <script src=...>
    console.print(f"\n[bold]<script src> リスト:[/bold]")
    for sc in soup.find_all("script", src=True):
        console.print(f"  {sc.get('src')}")

    # インラインJSから fetch / ajax / api URLを抽出
    js_url_patterns = [
        r'fetch\(["\']([^"\']+)["\']',
        r'\.ajax\([^)]*url:\s*["\']([^"\']+)["\']',
        r'["\']\s*(/[a-zA-Z0-9/_\-]+\.json[^"\']*)["\']',
        r'(/rooms?/\d+[/a-zA-Z0-9_\-]*)',
        r'(/availability[a-zA-Z0-9/_\-]*)',
        r'(/api/[a-zA-Z0-9/_\-]+)',
    ]
    console.print(f"\n[bold]インラインJSのURL候補:[/bold]")
    all_inline = "\n".join((sc.get_text() or "") for sc in soup.find_all("script") if not sc.get("src"))
    found = set()
    for pat in js_url_patterns:
        for m in re.findall(pat, all_inline):
            found.add(m)
    if found:
        for url in sorted(found):
            console.print(f"  {url}")
    else:
        console.print("  [yellow](発見されず - JSは別ファイルかも)[/yellow]")

    # data-* 属性 (Vue/React等が使うことが多い)
    console.print(f"\n[bold]data-* 属性:[/bold]")
    data_attrs = set()
    for el in soup.find_all():
        for attr in el.attrs:
            if attr.startswith("data-"):
                data_attrs.add(attr)
    for da in sorted(data_attrs)[:20]:
        console.print(f"  {da}")

    # form action URL
    console.print(f"\n[bold]form action:[/bold]")
    for form in soup.find_all("form"):
        method = (form.get("method") or "GET").upper()
        action = form.get("action", "")
        console.print(f"  {method} {action}")


def hypothesis_b_with_date(client: httpx.Client) -> None:
    """日付パラメータ付きで再取得"""
    console.print(f"\n[bold cyan]仮説B: &date= パラメータを付けて再取得[/bold cyan]")
    target_date = (date.today() + timedelta(days=7)).isoformat()  # 1週間後
    url = f"{BASE_URL}/rooms/{TARGET_ROOM}/reservation_calendar"
    params = {"requested_setting_id": SETTING_ID, "date": target_date}

    console.print(f"GET {url} params={params}")
    r = client.get(url, params=params, timeout=30.0)
    console.print(f"  → status: {r.status_code}, size: {len(r.text):,} bytes")

    save_path = OUTPUTS / f"stage2_calendar_with_date.html"
    save_path.write_text(r.text, encoding="utf-8")
    console.print(f"  → saved {save_path.relative_to(SCRIPT_DIR)}")

    # 簡易解析
    date_count = len(re.findall(r"\d{1,2}月\d{1,2}日", r.text))
    time_count = len(re.findall(r"\d{1,2}:\d{2}", r.text))
    available_marks = sum(r.text.count(s) for s in ["○", "△", "×"])
    console.print(f"  日付検出: {date_count} / 時刻検出: {time_count} / 空きマーク: {available_marks}")


def hypothesis_c_try_endpoints(client: httpx.Client) -> None:
    """別のエンドポイントパターンを試行"""
    console.print(f"\n[bold cyan]仮説C: 別エンドポイントの試行[/bold cyan]")
    candidates = [
        f"/rooms/{TARGET_ROOM}/availability",
        f"/rooms/{TARGET_ROOM}/availabilities",
        f"/rooms/{TARGET_ROOM}/reservation_calendar.json",
        f"/rooms/{TARGET_ROOM}/availability.json",
        f"/api/rooms/{TARGET_ROOM}/availability",
        f"/api/v1/rooms/{TARGET_ROOM}/calendar",
    ]
    for path in candidates:
        url = BASE_URL + path
        try:
            r = client.get(url, timeout=15.0)
            tag = "OK" if r.status_code == 200 else "NG"
            color = "green" if r.status_code == 200 else "red"
            console.print(f"  [{color}]{tag}[/{color}] {r.status_code} {len(r.text):>7,}B  {path}")
        except httpx.HTTPError as e:
            console.print(f"  [red]ERR[/red] {path}  {e}")
        time.sleep(2)  # 検証段階なので短め


def main() -> int:
    console.print(f"[bold green]Stage 2-D: カレンダーデータ取得方法の多角調査[/bold green]")
    console.print(f"対象: room_id={TARGET_ROOM}, setting_id={SETTING_ID}\n")

    # 仮説A: 既存HTMLから手がかりを抽出 (HTTPリクエスト不要)
    hypothesis_a_inspect_html()
    console.print()

    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.5",
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
    }

    with httpx.Client(headers=headers, follow_redirects=True) as client:
        # 仮説B: 日付パラメータ
        hypothesis_b_with_date(client)
        time.sleep(INTERVAL)

        # 仮説C: 別エンドポイント
        hypothesis_c_try_endpoints(client)

    return 0


if __name__ == "__main__":
    sys.exit(main())
