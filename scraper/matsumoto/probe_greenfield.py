"""
信州グリーンフィールドかりがね (MAT-SOC-002 / webR 202067) の構造調査。
複合施設(天然芝/人工芝/少年人工芝/フットサル/ゲートボール)が webR 上で
1施設1枠なのか、複数の部屋(コート種別)に分かれているのかを確認する。
"""
from __future__ import annotations
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))
from webr_core import USER_AGENT, console, fetch_facility_calendar, fetch_timeband_html  # noqa: E402
from webr_cities import CITIES  # noqa: E402

OUT = Path(__file__).parent.parent / "outputs"
OUT.mkdir(exist_ok=True)
CFG = CITIES["matsumoto"]


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(user_agent=USER_AGENT, locale="ja-JP",
                                   viewport={"width": 1280, "height": 900}).new_page()
        page.set_default_timeout(20000)

        # 1) 施設別空き状況(カレンダー) の部屋一覧
        cal = fetch_facility_calendar(page, CFG, "202067", "信州グリーンフィールドかりがね", "05")
        (OUT / "greenfield_calendar.html").write_text(cal, encoding="utf-8")
        soup = BeautifulSoup(cal, "lxml")
        main_table = max(soup.find_all("table"), key=lambda t: len(t.find_all("tr")), default=None)
        rooms = []
        if main_table:
            for tr in main_table.find_all("tr"):
                c = tr.find("td", class_="shisetsu")
                if c:
                    rooms.append(c.get_text(strip=True))
        console.print(f"[bold cyan]カレンダー画面の部屋(td.shisetsu): {len(rooms)}件[/bold cyan]")
        for r in rooms:
            console.print(f"   - {r}")

        # 2) 時間帯別画面の構造
        html = fetch_timeband_html(page, CFG, "202067", "信州グリーンフィールドかりがね", "05")
        (OUT / "greenfield_timeband.html").write_text(html, encoding="utf-8")
        s2 = BeautifulSoup(html, "lxml")
        console.print("\n[bold cyan]時間帯別画面:[/bold cyan]")
        console.print(f"  h3(施設): {[h.get_text(strip=True)[:30] for h in s2.select('.item h3')][:5]}")
        console.print(f"  h4(部屋グループ・先頭5): {[h.get_text(strip=True) for h in s2.select('h4')][:5]}")
        tables = s2.select("table.calendar")
        console.print(f"  日別テーブル数: {len(tables)}")
        if tables:
            t0 = tables[0]
            date = t0.select_one("th.shisetsu")
            console.print(f"  先頭テーブルの日付: {date.get_text(strip=True) if date else '?'}")
            trs = t0.select("tbody tr")
            console.print(f"  先頭テーブルの行(部屋)数: {len(trs)}")
            for tr in trs:
                cells = tr.find_all("td")
                name = cells[0].get_text(strip=True) if cells else "?"
                marks = [td.get_text(strip=True) for td in cells[1:]]
                console.print(f"    部屋[{name}]: {marks}")
        browser.close()
    console.print("\n[green]→ outputs/greenfield_calendar.html / greenfield_timeband.html 保存[/green]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
