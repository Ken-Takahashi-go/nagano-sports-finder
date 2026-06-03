"""
P-Kashikan系 公共施設予約システム 構造調査 (須坂市で代表調査)

Phase 2: 上田・須坂・駒ヶ根・東御・大町が P-Kashikan(PHP系)。
webR(富士通/ASP.NET)とは別エンジン。代表市で構造を調べ、
  - httpx直叩き可能か (URLパラメータベースか)
  - Playwright必須か (JS/Ajax依存度)
  - 空き状況カレンダーの形式 (○△×、パラメータ)
を判定する。

P-Kashikan URL: k{N}.p-kashikan.jp/{city}/
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))
from webr_core import USER_AGENT, console  # noqa: E402

CITY_NAME = "須坂市"
BASE = "https://k3.p-kashikan.jp/suzaka-city/"
SHOTS = Path(__file__).parent.parent / "outputs" / "pkashikan_probe_screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)

req_log: list[tuple] = []


def on_request(req) -> None:
    try:
        if req.resource_type in ("xhr", "fetch") or req.url.endswith(".php") or "op=" in req.url:
            pd = ""
            if req.method == "POST":
                try:
                    pd = (req.post_data or "")[:100]
                except Exception:
                    pd = ""
            req_log.append((req.method, req.url[:130], req.resource_type, pd))
    except Exception:
        pass


def snapshot(page, name: str) -> None:
    try:
        (SHOTS / f"{name}.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)
        console.print(f"  [dim]→ {name}[/dim]")
    except Exception as e:
        console.print(f"  [dim]snapshot {name}: {e}[/dim]")


def analyze(page, label: str) -> None:
    html = page.content()
    console.print(f"\n[bold]--- {label} ---[/bold]")
    console.print(f"  URL: {page.url}")
    console.print(f"  title: {page.title()}")
    console.print(f"  framework: PHP={'php' in page.url.lower() or '.php' in html.lower()} "
                  f"ASP.NET_VIEWSTATE={'__VIEWSTATE' in html} jQuery={'jquery' in html.lower()}")
    console.print(f"  要素: table={page.locator('table').count()} "
                  f"radio={page.locator('input[type=radio]').count()} "
                  f"checkbox={page.locator('input[type=checkbox]').count()} "
                  f"select={page.locator('select').count()} "
                  f"img={page.locator('img').count()}")
    # 空き状況記号 (○△×) や状態クラス
    for sym in ["○", "△", "×", "空き", "予約", "休"]:
        c = html.count(sym)
        if c:
            console.print(f"  記号'{sym}': {c}回")


def list_links(page) -> list[dict]:
    return page.evaluate("""
        () => Array.from(document.querySelectorAll('a, input[type=button], input[type=submit], button, area'))
            .filter(b => b.offsetParent !== null || b.tagName==='AREA')
            .map(b => ({
                text: (b.value || b.innerText || b.getAttribute('alt') || '').trim(),
                href: (b.getAttribute('href') || '').slice(0, 70),
                onclick: (b.getAttribute('onclick') || '').slice(0, 60),
            }))
            .filter(b => b.text && b.text.length < 30)
    """)


def click_text(page, kw: str) -> bool:
    for sel in [f"a:has-text('{kw}')", f"input[value*='{kw}']",
                f"area[alt*='{kw}']", f"text={kw}"]:
        try:
            el = page.locator(sel).first
            if el.count() and el.is_visible(timeout=2000):
                el.click()
                page.wait_for_load_state("networkidle", timeout=20000)
                page.wait_for_timeout(2000)
                return True
        except Exception:
            continue
    return False


def main() -> int:
    console.print(f"[bold green]P-Kashikan 構造調査: {CITY_NAME}[/bold green]")
    console.print(f"[dim]{BASE}[/dim]\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, locale="ja-JP",
                                      viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.set_default_timeout(20000)
        page.on("request", on_request)

        console.print("[cyan]Step 1: トップ[/cyan]")
        page.goto(BASE, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2000)
        snapshot(page, "01_top")
        analyze(page, "トップ")
        console.print("\n[cyan]操作要素:[/cyan]")
        for l in list_links(page)[:25]:
            console.print(f"    '{l['text']}' {('href='+l['href']) if l['href'] else ''}"
                          f"{(' on='+l['onclick']) if l['onclick'] else ''}")

        console.print("\n[cyan]Step 2: 空き状況導線[/cyan]")
        for kw in ["空き状況", "施設の空き", "空き照会", "あき", "予約状況", "施設予約"]:
            if click_text(page, kw):
                console.print(f"  → 「{kw}」クリック → {page.url}")
                snapshot(page, "02_aki")
                analyze(page, f"空き状況({kw})")
                break

        console.print("\n[cyan]Step 3: さらに分類/施設を辿る[/cyan]")
        for kw in ["スポーツ", "体育", "目的", "施設名", "分類", "一覧", "テニス"]:
            if click_text(page, kw):
                console.print(f"  → 「{kw}」クリック → {page.url}")
                snapshot(page, f"03_{kw}")
                analyze(page, f"分類({kw})")
                break

        console.print("\n[cyan]Step 4: 屋内スポーツ(Type=6)→目的→検索→施設一覧→カレンダー[/cyan]")
        try:
            t6 = page.locator("input[name='Type'][value='6']").first
            if t6.count():
                t6.click(force=True)
                page.wait_for_timeout(1800)  # make_mokuteki_menu(6) のJS生成待ち
                # 屋内スポーツの目的内容を確認
                mcs = page.evaluate("""
                    () => Array.from(document.querySelectorAll("input[name='MokutekiCode']")).map(r => {
                        const l = r.closest('label'); return { value: r.value, label: l ? l.innerText.trim() : null };
                    })
                """)
                console.print(f"  屋内スポーツの目的内容: {mcs}")
                mc = page.locator("input[name='MokutekiCode']").first
                if mc.count():
                    mc.click(force=True)
                    page.wait_for_timeout(1800)  # makeShisetsuList()
                snapshot(page, "04_type6_mokuteki")
                # 検索
                page.locator("button[name='searchBtn']").first.click()
                page.wait_for_load_state("networkidle", timeout=20000)
                page.wait_for_timeout(2000)
                snapshot(page, "05_shisetsu_list")
                analyze(page, "施設一覧")
                console.print("  施設一覧の操作要素:")
                for l in list_links(page)[:18]:
                    console.print(f"    '{l['text']}' {l['href']} {l['onclick']}")
                # disp_span=2 (1ヶ月) に切替えて日別カレンダー構造を確認
                try:
                    page.evaluate("() => { if (typeof setDispSpan === 'function') setDispSpan(2); }")
                    page.wait_for_load_state("networkidle", timeout=15000)
                    page.wait_for_timeout(2500)
                    snapshot(page, "07_month")
                    analyze(page, "1ヶ月表示")
                    heads = page.evaluate("() => Array.from(document.querySelectorAll('.koma-table th')).map(t=>t.innerText.trim()).slice(0,20)")
                    console.print(f"  koma-table ヘッダー(先頭20): {heads}")
                    facs = page.evaluate("() => Array.from(document.querySelectorAll('.koma-area h3')).map(h=>h.innerText.trim())")
                    console.print(f"  施設(h3): {facs}")
                except Exception as e:
                    console.print(f"  [yellow]disp_span=2 確認失敗: {e}[/yellow]")
            else:
                console.print("  [yellow]Type=6 radio が見つからない[/yellow]")
        except Exception as e:
            console.print(f"  [red]Step4 失敗: {e}[/red]")

        browser.close()

    # Network まとめ
    console.print(f"\n[bold]=== Network (XHR/php/op= リクエスト {len(req_log)}件) ===[/bold]")
    for m, u, rt, pd in req_log[:25]:
        console.print(f"  [{m}] {u}  ({rt}){(' POST:'+pd) if pd else ''}")

    console.print("\n[bold]判定の目安:[/bold]")
    console.print("  - URL に op=/施設ID等のGETパラメータ → httpx直叩きできる可能性 (軽量)")
    console.print("  - XHR/fetch でJSON取得 → APIを叩けば軽量")
    console.print("  - 全てPOST/VIEWSTATE依存 → Playwright必須")
    return 0


if __name__ == "__main__":
    sys.exit(main())
