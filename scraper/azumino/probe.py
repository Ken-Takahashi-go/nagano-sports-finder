"""
安曇野市 公共施設予約システム(富士通/web版) 構造調査 probe

Phase 2: 安曇野は pf489.com だが /web/ (webRは /webr/)。富士通の従来版の可能性。
webr_core(webR前提)が流用できるか、別スクレイパーが必要かを判定する。

調査項目:
  1. トップのメニュー/導線(空き照会リンク)
  2. 空き照会への遷移方式(__doPostBack? URL遷移? フレーム?)
  3. 施設選択UI(施設種類/地域/目的の分類、radio/checkbox/select)
  4. カレンダー形式(webRのcheckdate と同じか、別構造か)
  5. ASP.NET WebForms か 独自(.asp等)か

出力: outputs/azumino_probe_screenshots/ + コンソールレポート
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))
from webr_core import USER_AGENT, console  # noqa: E402

BASE = "https://www4.pf489.com/azumino/web/"
SHOTS = Path(__file__).parent.parent / "outputs" / "azumino_probe_screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)


def snapshot(page, name: str) -> None:
    try:
        (SHOTS / f"{name}.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)
        console.print(f"  [dim]→ {name} ({len(page.content()):,}B)[/dim]")
    except Exception as e:
        console.print(f"  [dim]snapshot {name} 失敗: {e}[/dim]")


def list_interactives(page) -> list[dict]:
    return page.evaluate("""
        () => Array.from(document.querySelectorAll('a, input[type=button], input[type=submit], button'))
            .filter(b => b.offsetParent !== null)
            .map(b => ({
                text: (b.value || b.innerText || '').trim(),
                href: b.getAttribute('href') || '',
                onclick: (b.getAttribute('onclick') || '').slice(0, 80),
                id: b.id || '', name: b.name || ''
            }))
            .filter(b => b.text && b.text.length < 40)
    """)


def analyze_page(page, label: str) -> None:
    html = page.content()
    console.print(f"\n[bold]--- {label} 解析 ---[/bold]")
    console.print(f"  URL: {page.url}")
    console.print(f"  title: {page.title()}")
    # フレームワーク判定
    has_postback = "__doPostBack" in html
    has_viewstate = "__VIEWSTATE" in html
    has_aspnet = ".aspx" in html or has_viewstate
    console.print(f"  __doPostBack: {has_postback} / __VIEWSTATE(ASP.NET): {has_viewstate}")
    # フレーム
    frames = page.frames
    console.print(f"  frames: {len(frames)} ({[f.name for f in frames if f.name]})")
    # フォーム要素
    radios = page.locator("input[type=radio]").count()
    checks = page.locator("input[type=checkbox]").count()
    selects = page.locator("select").count()
    tables = page.locator("table").count()
    console.print(f"  radio:{radios} checkbox:{checks} select:{selects} table:{tables}")
    # name属性の特徴的なもの
    names = page.evaluate("""
        () => [...new Set(Array.from(document.querySelectorAll('input,select'))
            .map(e => e.name).filter(Boolean))].slice(0, 25)
    """)
    console.print(f"  input/select names: {names}")
    # checkdate(webR特有)があるか
    console.print(f"  [{'green' if 'checkdate' in html else 'dim'}]checkdate(webR形式): {'checkdate' in html}[/]")
    # PostBackターゲット
    pbs = re.findall(r"__doPostBack\(['\"]([^'\"]+)['\"]", html)
    if pbs:
        from collections import Counter
        console.print(f"  PostBackターゲット上位: {Counter(pbs).most_common(10)}")


def main() -> int:
    console.print("[bold green]安曇野市 予約システム 構造調査[/bold green]")
    console.print(f"[dim]{BASE}[/dim]\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, locale="ja-JP",
                                      viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.set_default_timeout(20000)

        console.print("[cyan]Step 1: トップ[/cyan]")
        page.goto(BASE, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2000)
        snapshot(page, "01_top")
        analyze_page(page, "トップ")

        console.print("\n[cyan]Step 1b: 操作要素 列挙[/cyan]")
        links = list_interactives(page)
        for l in links[:30]:
            console.print(f"    [{l['name'][:20]:20s}] '{l['text']}' "
                          f"{('href='+l['href'][:30]) if l['href'] else ''}"
                          f"{(' onclick='+l['onclick'][:40]) if l['onclick'] else ''}")

        console.print("\n[cyan]Step 2: 空き照会導線をクリック[/cyan]")
        clicked = False
        for kw in ["空き照会", "空き状況", "あき", "照会", "予約申込", "施設の予約", "検索"]:
            try:
                el = page.locator(f"text={kw}").first
                if el.count() and el.is_visible(timeout=2000):
                    before = page.url
                    el.click()
                    page.wait_for_load_state("networkidle", timeout=20000)
                    page.wait_for_timeout(2000)
                    console.print(f"  → 「{kw}」クリック (URL: {before} → {page.url})")
                    clicked = True
                    snapshot(page, "02_after_aki")
                    analyze_page(page, f"空き照会({kw})後")
                    break
            except Exception as e:
                console.print(f"  [dim]{kw}: {e}[/dim]")
        if not clicked:
            console.print("  [yellow]空き照会導線が自動で見つからず。Step1bのリンク一覧から手動判断要[/yellow]")

        browser.close()

    console.print("\n[bold]判定の目安:[/bold]")
    console.print("  - checkdate あり & __doPostBack あり → webR系に近い (webr_core一部流用可)")
    console.print("  - VIEWSTATE あり & checkdate なし → ASP.NET別UI (新パーサ要)")
    console.print("  - frames 複数 → フレーム型旧UI (各フレーム個別処理要)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
