"""
Stage 2-C: 実際の空き状況カレンダーを取得して構造解析
URL: /rooms/{room_id}/reservation_calendar?requested_setting_id={X}

手順:
  1. rooms.html から requested_setting_id の選択肢を抽出
  2. 最初のroom (299) のカレンダーを取得 (各 requested_setting_id で試す)
  3. レスポンスHTMLを保存・構造解析

出力:
  - outputs/stage2_calendar_room{ID}_setting{N}.html
  - コンソールに構造解析結果
"""
from __future__ import annotations

import os
import re
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

OUTPUTS_DIR = SCRIPT_DIR / "outputs"
ROOMS_HTML = OUTPUTS_DIR / "stage2_rooms.html"

# 最初のroom (299) でテスト
TARGET_ROOM_ID = 299

console = Console()


def extract_setting_options(html: str) -> list[tuple[str, str]]:
    """
    rooms.html から requested_setting_id の選択肢を抽出
    戻り値: [(value, label), ...]
    """
    soup = BeautifulSoup(html, "lxml")

    # name="requested_setting_id" の select を探す
    select = soup.find("select", {"name": "requested_setting_id"})
    if select:
        options = []
        for opt in select.find_all("option"):
            value = opt.get("value", "")
            label = opt.get_text(strip=True)
            if value:
                options.append((value, label))
        return options

    # 見つからない場合: 「申請内容」というラベル付近のselectを探す
    label_text = soup.find(string=re.compile(r"申請内容|使用目的"))
    if label_text:
        parent = label_text.parent
        for sibling in parent.find_next_siblings():
            if sibling.name == "select":
                options = []
                for opt in sibling.find_all("option"):
                    value = opt.get("value", "")
                    label = opt.get_text(strip=True)
                    if value:
                        options.append((value, label))
                return options

    return []


def fetch_calendar(client: httpx.Client, room_id: int, setting_id: str | None) -> tuple[int, str]:
    """指定room_id+setting_idでカレンダーを取得"""
    url = f"{BASE_URL}/rooms/{room_id}/reservation_calendar"
    params = {}
    if setting_id:
        params["requested_setting_id"] = setting_id

    console.print(f"[cyan]GET[/cyan] {url} params={params}")
    response = client.get(url, params=params, timeout=30.0)
    console.print(f"  → status: [bold]{response.status_code}[/bold], "
                  f"content-length: {len(response.text):,} bytes")

    # 保存
    setting_label = setting_id or "no_setting"
    save_path = OUTPUTS_DIR / f"stage2_calendar_room{room_id}_setting{setting_label}.html"
    save_path.write_text(response.text, encoding="utf-8")
    console.print(f"  → saved {save_path.relative_to(SCRIPT_DIR)}")

    return response.status_code, response.text


def analyze_calendar(html: str) -> dict:
    """カレンダーHTMLの構造を解析"""
    soup = BeautifulSoup(html, "lxml")

    # 日付パターン
    date_patterns = {
        "YYYY-MM-DD": len(re.findall(r"\d{4}-\d{1,2}-\d{1,2}", html)),
        "MM月DD日": len(re.findall(r"\d{1,2}月\d{1,2}日", html)),
        "HH:MM": len(re.findall(r"\d{1,2}:\d{2}", html)),
    }

    # クラス名カウント
    from collections import Counter
    classes = Counter()
    for el in soup.find_all(class_=True):
        for c in el.get("class", []):
            classes[c] += 1

    # ステータスキーワード
    status_kws = ["空", "満", "予約済", "予約可", "○", "×", "△", "－", "受付"]
    kw_counts = {kw: html.count(kw) for kw in status_kws if html.count(kw) > 0}

    # テーブル・カレンダー要素
    tables = soup.find_all("table")
    title = soup.title.get_text(strip=True) if soup.title else ""

    # ログイン要否
    redirect_to_login = "users/sign_in" in html and ("ログインしてください" in html or "Sign in" in html)

    return {
        "title": title,
        "tables": len(tables),
        "date_patterns": date_patterns,
        "status_keywords": kw_counts,
        "top_classes": classes.most_common(15),
        "login_required": redirect_to_login,
    }


def main() -> int:
    console.print(f"[bold green]Stage 2-C: 空室カレンダー取得・構造解析[/bold green]")
    console.print(f"対象: room_id={TARGET_ROOM_ID}")
    console.print()

    if not ROOMS_HTML.exists():
        console.print(f"[red]ERROR: {ROOMS_HTML} がありません。先にstage2aを実行してください[/red]")
        return 1

    rooms_html = ROOMS_HTML.read_text(encoding="utf-8")
    options = extract_setting_options(rooms_html)

    console.print(f"[bold]requested_setting_id の選択肢:[/bold]")
    if options:
        for value, label in options:
            console.print(f"  value=[cyan]{value}[/cyan]  label={label}")
    else:
        console.print("  [yellow]見つかりませんでした (パラメータなしで試行)[/yellow]")
    console.print()

    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.5",
    }

    # 試行する setting_id のリスト: なし → 各オプション
    test_settings = [None]
    if options:
        test_settings += [v for v, _ in options]

    results = []

    with httpx.Client(headers=headers, follow_redirects=True) as client:
        for i, setting in enumerate(test_settings):
            try:
                status, html = fetch_calendar(client, TARGET_ROOM_ID, setting)
                analysis = analyze_calendar(html)
                analysis["setting_id"] = setting or "(none)"
                analysis["status_code"] = status
                results.append(analysis)
            except httpx.HTTPError as e:
                console.print(f"[red]Error: {e}[/red]")
                results.append({"setting_id": setting, "error": str(e)})

            if i < len(test_settings) - 1:
                console.print(f"  [dim]sleeping {INTERVAL}s...[/dim]")
                time.sleep(INTERVAL)
            console.print()

    # 結果テーブル
    table = Table(title="カレンダー取得結果", show_lines=True)
    table.add_column("setting_id", style="cyan", no_wrap=True)
    table.add_column("HTTP", justify="right")
    table.add_column("タイトル", style="white", max_width=30)
    table.add_column("MM月DD日", justify="right")
    table.add_column("HH:MM", justify="right")
    table.add_column("○件", justify="right")
    table.add_column("×件", justify="right")
    table.add_column("ログイン要", justify="center")

    for r in results:
        if "error" in r:
            table.add_row(str(r["setting_id"]), "ERR", "-", "-", "-", "-", "-", "-")
        else:
            table.add_row(
                str(r["setting_id"]),
                str(r["status_code"]),
                r["title"][:30],
                str(r["date_patterns"].get("MM月DD日", 0)),
                str(r["date_patterns"].get("HH:MM", 0)),
                str(r["status_keywords"].get("○", 0)),
                str(r["status_keywords"].get("×", 0)),
                "yes" if r["login_required"] else "no",
            )
    console.print(table)
    console.print()

    # 最も「データが多そうな」結果のクラス名top5
    if results:
        best = max((r for r in results if "error" not in r), key=lambda r: sum(r["date_patterns"].values()), default=None)
        if best:
            console.print(f"[bold]最もデータ量が多い setting_id={best['setting_id']} のCSSクラスtop15:[/bold]")
            for cls, count in best["top_classes"]:
                console.print(f"  {cls}: {count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
