"""
Stage M1: 松本市 webR の構造解析 (Playwright)

戦略 (長野市 Stage 2-F の流用):
  1. ヘッドレス Chromium を起動
  2. webR トップ → 施設検索画面に遷移
  3. JSによる動的描画を待つ
  4. ネットワークタブで実際の Ajax URL を記録
  5. 描画後HTMLとスクリーンショット保存

出力:
  - outputs/matsumoto_M1_top.html        webRトップ HTML
  - outputs/matsumoto_M1_top.png         スクリーンショット
  - outputs/matsumoto_M1_network.txt     ページが呼び出した URL 全リスト
  - outputs/matsumoto_M1_xhr.json        XHR/Fetch リクエストの詳細
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from rich.console import Console

SCRIPT_DIR = Path(__file__).parent.parent  # scraper/ をルートに
load_dotenv(SCRIPT_DIR / ".env")

SCRAPER_NAME = os.getenv("SCRAPER_NAME", "NaganoSportsFinder")
SCRAPER_VERSION = os.getenv("SCRAPER_VERSION", "0.1.0")
SCRAPER_CONTACT = os.getenv("SCRAPER_CONTACT", "contact@example.com")

USER_AGENT = (
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    f"AppleWebKit/537.36 (KHTML, like Gecko) "
    f"Chrome/120.0.0.0 Safari/537.36 "
    f"{SCRAPER_NAME}/{SCRAPER_VERSION} (+{SCRAPER_CONTACT})"
)

TARGET_URL = "https://yoyaku.city.matsumoto.lg.jp/webR/"
OUTPUTS = SCRIPT_DIR / "outputs"
OUTPUTS.mkdir(exist_ok=True)

console = Console()


def main() -> int:
    console.print(f"[bold green]Stage M1: 松本市 webR 構造解析[/bold green]")
    console.print(f"対象: {TARGET_URL}\n")

    network_log: list[dict] = []
    xhr_log: list[dict] = []

    with sync_playwright() as p:
        console.print("[cyan]Chromium 起動中...[/cyan]")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=USER_AGENT,
            locale="ja-JP",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        # ネットワーク監視: 全リクエスト
        def on_request(req):
            if "matsumoto" in req.url or "pf489" in req.url:
                network_log.append({
                    "method": req.method,
                    "url": req.url,
                    "resource_type": req.resource_type,
                })

        # XHR/Fetch だけ詳細記録 (実 API URL 発見用)
        def on_response(res):
            if res.request.resource_type in ("xhr", "fetch"):
                if "matsumoto" in res.url or "pf489" in res.url:
                    try:
                        body = res.text()[:2000]  # 先頭2KB
                    except Exception:
                        body = "(failed to read body)"
                    xhr_log.append({
                        "method": res.request.method,
                        "url": res.url,
                        "status": res.status,
                        "content_type": res.headers.get("content-type", ""),
                        "body_preview": body,
                    })

        page.on("request", on_request)
        page.on("response", on_response)

        console.print(f"[cyan]ページに遷移...[/cyan]")
        try:
            page.goto(TARGET_URL, wait_until="networkidle", timeout=45000)
        except PlaywrightTimeoutError:
            console.print(f"  [yellow]networkidle timeout (続行)[/yellow]")
        console.print(f"  → page loaded (URL: {page.url})")

        # JS描画完了を念のため待つ
        page.wait_for_timeout(3000)

        # HTML保存
        html = page.content()
        html_path = OUTPUTS / "matsumoto_M1_top.html"
        html_path.write_text(html, encoding="utf-8")
        console.print(f"[green]✓ HTML保存: {html_path.relative_to(SCRIPT_DIR)} ({len(html):,} bytes)[/green]")

        # スクリーンショット
        screenshot_path = OUTPUTS / "matsumoto_M1_top.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        console.print(f"[green]✓ スクリーンショット: {screenshot_path.relative_to(SCRIPT_DIR)}[/green]")

        # ネットワーク全ログ
        net_path = OUTPUTS / "matsumoto_M1_network.txt"
        with net_path.open("w", encoding="utf-8") as f:
            f.write(f"# 全リクエスト履歴 ({len(network_log)}件)\n")
            for req in network_log:
                f.write(f"[{req['resource_type']:8s}] {req['method']:6s} {req['url']}\n")
        console.print(f"[green]✓ ネットワーク全ログ: {net_path.relative_to(SCRIPT_DIR)}[/green]")

        # XHR/Fetch 詳細 (本命)
        xhr_path = OUTPUTS / "matsumoto_M1_xhr.json"
        xhr_path.write_text(json.dumps(xhr_log, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"[green]✓ XHR/Fetch 詳細: {xhr_path.relative_to(SCRIPT_DIR)} ({len(xhr_log)} 件)[/green]")

        # 簡易解析
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        title = soup.title.get_text(strip=True) if soup.title else "(no title)"
        forms = soup.find_all("form")
        links = soup.find_all("a", href=True)

        console.print(f"\n[bold]ページ解析:[/bold]")
        console.print(f"  title: {title}")
        console.print(f"  body長: {len(soup.get_text()):,} 文字")
        console.print(f"  フォーム数: {len(forms)}")
        console.print(f"  リンク数: {len(links)}")

        # 主要リンクの抽出
        if links:
            console.print(f"\n[bold]上位10リンク(href):[/bold]")
            from collections import Counter
            href_counter = Counter()
            for a in links:
                href = a.get("href", "")
                if href and not href.startswith("#"):
                    href_counter[href] += 1
            for href, count in href_counter.most_common(10):
                text = ""
                for a in links:
                    if a.get("href") == href:
                        text = a.get_text(strip=True)[:30]
                        break
                console.print(f"  [{count:2d}x] {href[:80]:<80s} {text}")

        # XHR/Fetch ハイライト (本命の Ajax URL)
        if xhr_log:
            console.print(f"\n[bold magenta]🌟 XHR/Fetch リクエスト (実 API 候補):[/bold magenta]")
            for r in xhr_log[:15]:
                ct = r['content_type'][:30]
                console.print(f"  [{r['status']}] {r['method']:6s} {r['url']}")
                console.print(f"           Content-Type: {ct}")
        else:
            console.print(f"\n[yellow]⚠ XHR/Fetch リクエストが0件: SPA でなく旧来サーバ描画かも、もしくは別画面で発生[/yellow]")

        context.close()
        browser.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
