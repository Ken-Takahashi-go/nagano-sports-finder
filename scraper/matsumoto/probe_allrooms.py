"""
全コート選択時の時間帯別画面の構造調査 (かりがねサッカー場 202067)。
現行 fetch_timeband_html は「各日付の先頭1部屋」しか選ばないため、複合施設で
コートを取りこぼす。ここでは calendar の checkdate を全選択して、時間帯別画面が
コートをどう構造化して返すか(h4/部屋名/テーブル対応)を解析する。
"""
from __future__ import annotations
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))
from webr_core import USER_AGENT, console, fetch_facility_calendar  # noqa: E402
from webr_cities import CITIES  # noqa: E402

OUT = Path(__file__).parent.parent / "outputs"
CFG = CITIES["matsumoto"]


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(user_agent=USER_AGENT, locale="ja-JP",
                                   viewport={"width": 1280, "height": 900}).new_page()
        page.set_default_timeout(20000)
        fetch_facility_calendar(page, CFG, "202067", "信州グリーンフィールドかりがね", "05")

        # checkdate 全件の構造 (value=YYYYMMDD+TTT+RR)。部屋(RR)ごとの件数を確認
        cds = page.evaluate("""
            () => Array.from(document.querySelectorAll("input[name='checkdate']"))
                .map(c => ({ id: c.id, value: c.value }))
        """)
        console.print(f"[cyan]checkdate 総数: {len(cds)}[/cyan]")
        from collections import Counter
        rr = Counter(c["value"][11:13] for c in cds)   # 末尾2桁=room_part
        ttt = Counter(c["value"][8:11] for c in cds)    # 中3桁=time_band
        console.print(f"  room_part(RR)別件数: {dict(rr)}")
        console.print(f"  time_band(TTT)種類: {dict(ttt)}")
        dates = Counter(c["value"][:8] for c in cds)
        console.print(f"  日付種類数: {len(dates)}")

        # 全 checkdate を選択 (最大件数まで)
        n = 0
        for c in cds:
            try:
                page.locator(f"#{c['id']}").check(force=True); n += 1
            except Exception:
                pass
        console.print(f"  選択した checkbox: {n}")
        page.wait_for_timeout(500)
        page.evaluate("() => __doPostBack('next', '')")
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(1500)
        html = page.content()
        (OUT / "greenfield_allrooms_timeband.html").write_text(html, encoding="utf-8")

        s = BeautifulSoup(html, "lxml")
        if "JikantaibetsuAkiJoukyou" not in html and "時間帯別" not in html:
            console.print("[red]時間帯別画面に未到達[/red]")
            console.print(f"  URL: {page.url}  title: {page.title()}")
            browser.close(); return 1

        # 構造: item ごとに h3(施設) と h4(部屋) があり、その下に日別table
        items = s.select(".item")
        console.print(f"\n[bold]item 数: {len(items)}[/bold]")
        h4s = [h.get_text(strip=True) for h in s.select("h4")]
        from collections import OrderedDict
        uniq_h4 = list(OrderedDict.fromkeys(h4s))
        console.print(f"[bold]ユニークな h4(部屋/コート): {uniq_h4}[/bold]")

        # 各 h4 直後の最初のtableの tbody 行(部屋内の小区分)を1つ確認
        for h4 in s.select("h4"):
            name = h4.get_text(strip=True)
            tbl = h4.find_next("table", class_="calendar")
            if not tbl:
                continue
            date = tbl.select_one("th.shisetsu")
            rows = tbl.select("tbody tr")
            subrooms = [tr.find("td", class_="shisetsu").get_text(strip=True)
                        for tr in rows if tr.find("td", class_="shisetsu")]
            console.print(f"  h4='{name}' | 例の日付={date.get_text(strip=True) if date else '?'} | tbody小区分={subrooms}")
            break  # 1例だけ

        browser.close()
    console.print("\n[green]→ outputs/greenfield_allrooms_timeband.html 保存[/green]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
