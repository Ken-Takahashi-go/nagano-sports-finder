"""
Stage 2-F: Playwrightでカレンダーを実際に描画して取得

戦略:
  1. ヘッドレスChromiumを起動
  2. /rooms/{room_id}/reservation_calendar?requested_setting_id=84 にアクセス
  3. JSによるカレンダー描画完了を待つ (#reservation_calendar の子要素が現れるまで)
  4. 描画後のHTMLとスクリーンショットを保存
  5. ネットワークタブで実際に呼び出された Ajax URL も記録 (将来の最適化用)

出力:
  - outputs/stage2f_rendered.html       (描画後の完全なHTML)
  - outputs/stage2f_screenshot.png      (視認用スクリーンショット)
  - outputs/stage2f_network_log.txt     (ページが呼び出したURL一覧)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from rich.console import Console

SCRIPT_DIR = Path(__file__).parent
load_dotenv(SCRIPT_DIR / ".env")

BASE_URL = os.getenv("MACHIKAGI_BASE_URL", "https://city.nagano.nagano.machikagi-remote.jp")
SCRAPER_NAME = os.getenv("SCRAPER_NAME", "NaganoSportsFinder")
SCRAPER_VERSION = os.getenv("SCRAPER_VERSION", "0.1.0")
SCRAPER_CONTACT = os.getenv("SCRAPER_CONTACT", "contact@example.com")

USER_AGENT = (
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    f"AppleWebKit/537.36 (KHTML, like Gecko) "
    f"Chrome/120.0.0.0 Safari/537.36 "
    f"{SCRAPER_NAME}/{SCRAPER_VERSION} (+{SCRAPER_CONTACT})"
)

TARGET_URL = f"{BASE_URL}/rooms/299/reservation_calendar?requested_setting_id=84"
OUTPUTS = SCRIPT_DIR / "outputs"

console = Console()


def main() -> int:
    console.print(f"[bold green]Stage 2-F: Playwrightでカレンダー描画後の取得[/bold green]")
    console.print(f"対象: {TARGET_URL}")
    console.print()

    network_log: list[dict] = []

    with sync_playwright() as p:
        console.print("[cyan]Chromium 起動中...[/cyan]")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=USER_AGENT,
            locale="ja-JP",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        # ネットワーク監視
        def on_request(req):
            if "machikagi-remote.jp" in req.url:
                network_log.append({
                    "method": req.method,
                    "url": req.url,
                    "resource_type": req.resource_type,
                })

        page.on("request", on_request)

        console.print(f"[cyan]ページに遷移...[/cyan]")
        page.goto(TARGET_URL, wait_until="networkidle", timeout=30000)
        console.print(f"  → page loaded (URL after redirects: {page.url})")

        # カレンダー本体が描画されるまで待つ
        console.print(f"[cyan]カレンダー描画待ち...[/cyan]")
        try:
            # #reservation_calendar 内に何らかの要素が現れるまで(10秒)
            page.wait_for_function(
                "() => document.querySelector('#reservation_calendar')?.children.length > 0",
                timeout=10000,
            )
            console.print(f"  → calendar rendered!")
        except PlaywrightTimeoutError:
            console.print(f"  [yellow]warning: timeout. カレンダーが描画されなかった or 別構造[/yellow]")

        # 念の為もう少し待つ
        page.wait_for_timeout(2000)

        # HTML取得
        html = page.content()
        html_path = OUTPUTS / "stage2f_rendered.html"
        html_path.write_text(html, encoding="utf-8")
        console.print(f"[green]✓ HTML保存: {html_path.relative_to(SCRIPT_DIR)} "
                      f"({len(html):,} bytes)[/green]")

        # スクリーンショット
        screenshot_path = OUTPUTS / "stage2f_screenshot.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        console.print(f"[green]✓ スクリーンショット: {screenshot_path.relative_to(SCRIPT_DIR)}[/green]")

        # 簡易解析
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        cal_div = soup.find("div", id="reservation_calendar")
        if cal_div:
            children_count = len(cal_div.find_all(recursive=False))
            inner_text = (cal_div.get_text(strip=True) or "")[:200]
            console.print(f"\n[bold]#reservation_calendar の状態:[/bold]")
            console.print(f"  子要素数: {children_count}")
            console.print(f"  text先頭200文字: {inner_text}")

            # 日付・時刻パターン
            import re
            inner_html = str(cal_div)
            date_count = len(re.findall(r"\d{1,2}月\d{1,2}日", inner_html))
            time_count = len(re.findall(r"\d{1,2}:\d{2}", inner_html))
            star_count = inner_html.count("fa-star-o")
            circle_count = inner_html.count("fa-circle-o")
            close_count = inner_html.count("fa-close")
            console.print(f"\n[bold]内容の数値指標:[/bold]")
            console.print(f"  MM月DD日 形式: {date_count}件")
            console.print(f"  HH:MM 形式: {time_count}件")
            console.print(f"  ○マーク (fa-circle-o): {circle_count}件 = 空き枠あり")
            console.print(f"  △マーク (fa-star-o): {star_count}件 = 抽選申込可")
            console.print(f"  ×マーク (fa-close): {close_count}件 = 空き枠なし")

        # ネットワークログ保存
        log_path = OUTPUTS / "stage2f_network_log.txt"
        with log_path.open("w", encoding="utf-8") as f:
            f.write("# 全リクエスト履歴\n")
            for req in network_log:
                f.write(f"[{req['resource_type']}] {req['method']} {req['url']}\n")
        console.print(f"\n[green]✓ ネットワークログ: {log_path.relative_to(SCRIPT_DIR)} "
                      f"({len(network_log)}リクエスト)[/green]")

        # XHR/Fetch だけ抽出 (実際のAPIエンドポイント特定用)
        ajax_calls = [r for r in network_log if r["resource_type"] in ("xhr", "fetch")]
        if ajax_calls:
            console.print(f"\n[bold]Ajax/Fetch リクエスト (将来の最適化用):[/bold]")
            for c in ajax_calls[:10]:
                console.print(f"  {c['method']} {c['url']}")

        context.close()
        browser.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
