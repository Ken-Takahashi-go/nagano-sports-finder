"""
Stage M3-fix: 全カテゴリ施設マッピング

経緯:
  Stage M3 では zenshisetsu 画面で 10件 (体育館 2020XX) のみ取得
  → テニス、サッカー、残り体育館 など 27件が未取得

戦略:
  1. webR top → 空き照会
  2. zenshisetsu (全施設) を試す + 種目別 (種目選択 → 体育館/テニス/グラウンド) を試す
  3. 各画面でページ送りボタンを探して全件取得
  4. 検出した checkbox を JSON 統合

成果物:
  - outputs/matsumoto_M3fix_all_facilities.json
    [{ "id": "checkShisetsu202001", "value": "202001",
       "name": "総合体育館", "category": "...", "page": 1 }, ...]
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from rich.console import Console

SCRIPT_DIR = Path(__file__).parent.parent
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

BASE_URL = "https://yoyaku.city.matsumoto.lg.jp"
SHOTS = SCRIPT_DIR / "outputs" / "matsumoto_M3fix_screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)
OUTPUT_JSON = SCRIPT_DIR / "outputs" / "matsumoto_M3fix_all_facilities.json"

console = Console()


def snapshot(page, name: str) -> None:
    html = page.content()
    (SHOTS / f"{name}.html").write_text(html, encoding="utf-8")
    page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)


def extract_checkboxes(page, category_hint: str, page_num: int) -> list[dict]:
    """現在画面の checkShisetsu チェックボックスを全て抽出"""
    items = page.evaluate("""
        () => Array.from(document.querySelectorAll("input[name='checkShisetsu']")).map(c => {
            const label = document.querySelector(`label[for='${c.id}']`);
            return {
                id: c.id,
                value: c.value,
                name: label ? label.textContent.trim() : null
            };
        })
    """)
    for it in items:
        it["category"] = category_hint
        it["page"] = page_num
    return items


def find_pagination_buttons(page) -> list[str]:
    """次へ/前へ などのページ送りボタンの value or name を抽出"""
    result = page.evaluate("""
        () => Array.from(document.querySelectorAll("input[type='submit'], input[type='button'], button"))
            .map(b => ({
                value: b.value || b.innerText || '',
                name: b.name || '',
                id: b.id || ''
            }))
            .filter(b => /次|前|ページ|>|</.test(b.value))
    """)
    return result


def main() -> int:
    console.print("[bold green]Stage M3-fix: 全カテゴリ施設マッピング[/bold green]\n")

    all_facilities: list[dict] = []
    seen_values: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, locale="ja-JP",
                                      viewport={"width": 1280, "height": 900})
        page = context.new_page()

        # =================================================================
        # Step 1-2: webR → 空き照会
        # =================================================================
        console.print("[cyan]Step 1: webR トップ[/cyan]")
        page.goto(f"{BASE_URL}/WebR/", wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2000)

        console.print("[cyan]Step 2: 空き照会・予約の申込[/cyan]")
        page.locator("text=空き照会").first.click()
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        snapshot(page, "01_after_kuki")

        # =================================================================
        # Step 3: 「目的選択」ボタンを探す
        # =================================================================
        console.print("\n[cyan]Step 3: 全カテゴリ探索[/cyan]")

        # 利用目的(競技別)ボタン候補
        category_candidates = [
            ("zenshisetsu", "全施設"),
            ("shumokubetsu", "種目別"),
            ("mokutekibetsu", "目的別"),
            ("mokuteki", "目的"),
            ("shisetsubetsu", "施設別"),
        ]

        # 画面上のボタンを列挙
        buttons = page.evaluate("""
            () => Array.from(document.querySelectorAll("a, input[type='submit'], input[type='button'], button"))
                .map(b => ({
                    text: (b.value || b.innerText || '').trim(),
                    name: b.name || '',
                    id: b.id || '',
                    href: b.getAttribute('href') || ''
                }))
                .filter(b => b.text && b.text.length < 30)
        """)
        console.print(f"  ボタン候補 ({len(buttons)}件):")
        for b in buttons[:30]:
            console.print(f"    [name={b['name']:<25s}] [{b['text']}]")

        # =================================================================
        # Step 4: 各カテゴリへ遷移して全 checkbox 取得
        # =================================================================
        # まず zenshisetsu を実行 (体育館 10件は既知)
        console.print("\n[cyan]Step 4-A: zenshisetsu (全施設)[/cyan]")
        try:
            page.evaluate("() => __doPostBack('zenshisetsu', '')")
            page.wait_for_load_state("networkidle", timeout=30000)
            page.wait_for_timeout(1500)
            snapshot(page, "02_zenshisetsu_p1")

            items = extract_checkboxes(page, "zenshisetsu", 1)
            console.print(f"  → {len(items)}件 取得")
            for it in items:
                if it["value"] not in seen_values:
                    seen_values.add(it["value"])
                    all_facilities.append(it)

            # ページ送りボタンを探す
            page_buttons = page.evaluate("""
                () => Array.from(document.querySelectorAll("input[type='submit'], input[type='button'], button, a"))
                    .map(b => ({
                        text: (b.value || b.innerText || '').trim(),
                        name: b.name || '',
                        id: b.id || '',
                        href: b.getAttribute('href') || ''
                    }))
                    .filter(b => /次|前|ページ|表示順|>>|<</.test(b.text))
            """)
            console.print(f"  ページ送り候補:")
            for b in page_buttons:
                console.print(f"    text={b['text']!r} name={b['name']!r} id={b['id']!r}")

            # 「次へ」/「次ページ」ボタンを試す (5ページまで)
            for try_page in range(2, 7):
                clicked_next = False
                for selector in [
                    "input[type='submit'][value*='次']",
                    "a:has-text('次')",
                    "input[name*='next']",
                    "input[name*='Next']",
                ]:
                    try:
                        el = page.locator(selector).first
                        if el.is_visible(timeout=1500):
                            el.click()
                            page.wait_for_load_state("networkidle", timeout=20000)
                            page.wait_for_timeout(1500)
                            clicked_next = True
                            break
                    except Exception:
                        continue
                if not clicked_next:
                    console.print(f"  → ページ {try_page}: 次ボタン無し終了")
                    break
                snapshot(page, f"02_zenshisetsu_p{try_page}")
                items = extract_checkboxes(page, "zenshisetsu", try_page)
                new = [i for i in items if i["value"] not in seen_values]
                console.print(f"  → ページ {try_page}: {len(items)}件 (新規 {len(new)}件)")
                for it in new:
                    seen_values.add(it["value"])
                    all_facilities.append(it)
                if not new:
                    break
        except Exception as e:
            console.print(f"  [red]zenshisetsu 失敗: {e}[/red]")

        # 一度トップに戻って種目別を試す
        console.print("\n[cyan]Step 4-B: 種目別 (shumokubetsu) を試す[/cyan]")
        try:
            page.goto(f"{BASE_URL}/WebR/", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            page.locator("text=空き照会").first.click()
            page.wait_for_load_state("networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            page.evaluate("() => __doPostBack('shumokubetsu', '')")
            page.wait_for_load_state("networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            snapshot(page, "03_shumokubetsu")

            # 種目選択画面のオプションを抽出
            options = page.evaluate("""
                () => Array.from(document.querySelectorAll("input[name*='shumoku'], input[name*='radio'], a, button"))
                    .map(b => ({
                        text: (b.value || b.innerText || '').trim(),
                        name: b.name || '',
                        id: b.id || ''
                    }))
                    .filter(b => b.text && b.text.length < 30)
            """)
            console.print(f"  → 種目選択肢候補:")
            for o in options[:20]:
                console.print(f"    [name={o['name']:<25s}] [{o['text']}]")

            # checkbox があれば取得
            items = extract_checkboxes(page, "shumokubetsu", 1)
            console.print(f"  → 即時 checkShisetsu: {len(items)}件")
        except Exception as e:
            console.print(f"  [yellow]shumokubetsu: {e}[/yellow]")

        browser.close()

    # =================================================================
    # 結果保存
    # =================================================================
    console.print(f"\n[bold]全 {len(all_facilities)}件 検出[/bold]")

    # value プレフィックス別集計
    prefix_counts: dict[str, int] = {}
    for f in all_facilities:
        pfx = f["value"][:4] if len(f["value"]) >= 4 else f["value"]
        prefix_counts[pfx] = prefix_counts.get(pfx, 0) + 1
    console.print("[bold]value プレフィックス別:[/bold]")
    for pfx, cnt in sorted(prefix_counts.items()):
        console.print(f"  {pfx}xx: {cnt}件")

    OUTPUT_JSON.write_text(
        json.dumps(all_facilities, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    console.print(f"\n[bold green]→ 保存: {OUTPUT_JSON.name}[/bold green]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
