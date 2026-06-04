"""
NELCS系 公共施設予約システム 構造調査 (伊那市で代表調査)

Phase 2 コンプリート: 伊那・千曲・中野・箕輪が NELCS(nelcs.ne.jp)。
PHP(.php5)・VIEWSTATEなし。カレンダーの○×が静的HTMLかAjaxかを確認し、
httpx直叩き可能か / Playwright必須かを判定する。

NELCS URL: nelcs.ne.jp/Facilityrsv/Smartphone/{自治体ID}/user/
  伊那=2020900 千曲=2021800 中野=2021100 箕輪=2038300
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))
from webr_core import USER_AGENT, console  # noqa: E402

CITY_NAME = "伊那市"
BASE = "https://nelcs.ne.jp/Facilityrsv/Smartphone/2020900/user/rsvlot/RsvIndex.php5"
SHOTS = Path(__file__).parent.parent / "outputs" / "nelcs_probe_screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)

req_log: list[tuple] = []


def on_request(req) -> None:
    try:
        if req.resource_type in ("xhr", "fetch") or ".php" in req.url:
            pd = ""
            if req.method == "POST":
                try:
                    pd = (req.post_data or "")[:80]
                except Exception:
                    pd = ""
            req_log.append((req.method, req.url[:110], req.resource_type, pd))
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
    console.print(f"  VIEWSTATE(ASP.NET): {'__VIEWSTATE' in html} / .php5: {'.php5' in html}")
    console.print(f"  要素: table={page.locator('table').count()} "
                  f"radio={page.locator('input[type=radio]').count()} "
                  f"select={page.locator('select').count()} "
                  f"a={page.locator('a').count()}")
    for sym in ["○", "△", "×", "空き", "休", "－"]:
        c = html.count(sym)
        if c:
            console.print(f"  記号'{sym}': {c}回")


def list_links(page) -> list[dict]:
    return page.evaluate("""
        () => Array.from(document.querySelectorAll('a, input[type=button], input[type=submit], button'))
            .filter(b => b.offsetParent !== null)
            .map(b => ({ text: (b.value || b.innerText || '').trim().slice(0,24),
                         href: (b.getAttribute('href')||'').slice(0,60),
                         onclick: (b.getAttribute('onclick')||'').slice(0,50) }))
            .filter(b => b.text)
    """)


def click_text(page, kw: str) -> bool:
    for sel in [f"a:has-text('{kw}')", f"input[value*='{kw}']", f"text={kw}"]:
        try:
            el = page.locator(sel).first
            if el.count() and el.is_visible(timeout=2000):
                el.click()
                page.wait_for_load_state("networkidle", timeout=20000)
                page.wait_for_timeout(1800)
                return True
        except Exception:
            continue
    return False


def main() -> int:
    console.print(f"[bold green]NELCS 構造調査: {CITY_NAME}[/bold green]")
    console.print(f"[dim]{BASE}[/dim]\n")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(user_agent=USER_AGENT, locale="ja-JP",
                                   viewport={"width": 400, "height": 800}).new_page()
        page.set_default_timeout(20000)
        page.on("request", on_request)

        console.print("[cyan]Step 1: トップ(施設一覧)[/cyan]")
        page.goto(BASE, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2000)
        snapshot(page, "01_top")
        analyze(page, "トップ")
        console.print("\n[cyan]操作要素(先頭20):[/cyan]")
        for l in list_links(page)[:20]:
            console.print(f"    '{l['text']}' {l['href']}{(' on='+l['onclick']) if l['onclick'] else ''}")

        console.print("\n[cyan]Step 2: 屋内スポーツ→検索→施設→カレンダー[/cyan]")
        try:
            page.evaluate("() => { if(typeof RsvSelCategory==='function') RsvSelCategory('1'); }")
            page.wait_for_timeout(1500)
            page.evaluate("() => { if(typeof search==='function') search(); }")
            page.wait_for_load_state("networkidle", timeout=20000)
            page.wait_for_timeout(2500)
            snapshot(page, "02_shisetsu_list")
            analyze(page, "施設一覧(屋内スポーツ)")
            links = list_links(page)
            console.print(f"  施設一覧リンク({len(links)}件):")
            for l in links[:18]:
                console.print(f"    '{l['text']}' {l['href'][:40]} {l['onclick'][:40]}")
            # 種目(バスケ 00002)を選択 → 次画面
            page.evaluate("() => { if(typeof RsvSelItemId==='function') RsvSelItemId('00002'); }")
            page.wait_for_load_state("networkidle", timeout=20000)
            page.wait_for_timeout(2500)
            snapshot(page, "03_after_item")
            analyze(page, "種目選択後")
            console.print("  操作要素(先頭18):")
            for l in list_links(page)[:18]:
                console.print(f"    '{l['text']}' {l['href'][:30]} {l['onclick'][:42]}")
            # 地区選択(伊那市 2020901) → 確定 → カレンダー
            page.evaluate("() => { if(typeof RsvSelDestrict==='function') RsvSelDestrict('2020901'); }")
            page.wait_for_timeout(1000)
            page.evaluate("() => { if(typeof registDistrict==='function') registDistrict(); }")
            page.wait_for_load_state("networkidle", timeout=20000)
            page.wait_for_timeout(2500)
            snapshot(page, "04_calendar")
            analyze(page, "カレンダー(地区確定後)")
            console.print(f"  → URL: {page.url}")
            # RsvResult の施設リンク(onclick) を確認
            shlinks = page.evaluate("() => Array.from(document.querySelectorAll('a')).map(a=>({t:a.innerText.trim().slice(0,18), o:(a.getAttribute('onclick')||'').slice(0,55)})).filter(a=>a.o && /Sel|Shis|Rsv|Week|week/.test(a.o))")
            console.print(f"  施設リンクonclick(先頭8): {shlinks[:8]}")
            # サンビレッジ体育館(20209-00101)の週間カレンダー
            page.evaluate("() => { if(typeof calendar_submit==='function') calendar_submit('0','20209-00101','00002'); }")
            page.wait_for_load_state("networkidle", timeout=20000)
            page.wait_for_timeout(2500)
            snapshot(page, "05_week_calendar")
            analyze(page, "週間カレンダー(最終)")
            console.print(f"  → URL: {page.url}")
            marks = page.evaluate("() => { const t=document.body.innerText; return {maru:(t.match(/○/g)||[]).length, sankaku:(t.match(/△/g)||[]).length, batsu:(t.match(/×/g)||[]).length}; }")
            console.print(f"  ○×記号: {marks}")
            imgs = page.evaluate("() => [...new Set(Array.from(document.querySelectorAll('img')).map(i=>i.src.split('/').pop()))].slice(0,12)")
            console.print(f"  img(状態画像?): {imgs}")
        except Exception as e:
            console.print(f"  [red]Step2 失敗: {e}[/red]")

        browser.close()

    console.print(f"\n[bold]=== Network (XHR/php {len(req_log)}件) ===[/bold]")
    for m, u, rt, pd in req_log[:20]:
        console.print(f"  [{m}] {u} ({rt}){(' '+pd) if pd else ''}")
    console.print("\n[bold]判定: ○×が静的HTMLにあれば httpx可能 / XHRでJSON取得ならAPI叩く / 全てJS描画ならPlaywright[/bold]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
