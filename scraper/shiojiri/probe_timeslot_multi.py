"""
塩尻 webR 時間帯別空き状況: 複数日一括選択の検証

目的: 施設別空き状況で複数日(checkdate)を一括選択 → 次へ進む で
      「複数日分の時間帯別テーブル」が1ページで取れるか確認。
      取れれば 1施設=1遷移で全日分取得でき、スクレイプ時間が激減する。

対象: 塩尻 市立体育館 215001 (アリーナ=種別00)
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))
from webr_core import CityConfig, USER_AGENT, console, fetch_facility_calendar  # noqa: E402

SHOTS = Path(__file__).parent.parent / "outputs" / "shiojiri_timeslot_screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)

SHIOJIRI = CityConfig(
    name="塩尻市", external_system="shiojiri_webR",
    base_url="https://www.pf489.com/shiojiri",
    type_map={"SIO-GYM": "00", "SIO-TEN": "13", "SIO-SOC": "10"},
)


def main() -> int:
    console.print("[bold green]塩尻 時間帯別: 複数日一括選択 検証[/bold green]\n")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(user_agent=USER_AGENT, locale="ja-JP",
                                   viewport={"width": 1280, "height": 900}).new_page()
        page.set_default_timeout(20000)

        fetch_facility_calendar(page, SHIOJIRI, "215001", "市立体育館", "00")

        # 全 checkdate を取得し、日付ごとに1つ(最初の部屋)を選ぶ
        cds = page.evaluate("""
            () => Array.from(document.querySelectorAll("input[name='checkdate']"))
                .map(c => ({ id: c.id, value: c.value }))
        """)
        console.print(f"  checkdate 総数: {len(cds)}")
        # value: YYYYMMDD + TTT + RR ... → 先頭8桁=日付
        by_date = {}
        for c in cds:
            d = c["value"][:8]
            by_date.setdefault(d, c["id"])  # 各日付の最初の checkbox id
        dates = sorted(by_date.keys())
        console.print(f"  ユニーク日付数: {len(dates)} ({dates[0]}〜{dates[-1]})")

        # 全日付(最大31)を一括選択
        pick = dates[:31]
        for d in pick:
            cid = by_date[d]
            try:
                page.locator(f"#{cid}").check(force=True)
            except Exception:
                page.locator(f"label[for='{cid}']").first.click(force=True)
        page.wait_for_timeout(500)
        console.print(f"  選択した日付数: {len(pick)}")

        # 次へ進む
        page.evaluate("() => __doPostBack('next', '')")
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        html = page.content()
        (SHOTS / "03_jikantai_multi.html").write_text(html, encoding="utf-8")
        console.print(f"\n[cyan]遷移後 ({len(html):,}B)  URL: {page.url}[/cyan]")

        # 何日分のテーブルが出たか
        info = page.evaluate("""
            () => {
                const tables = Array.from(document.querySelectorAll('table.calendar'));
                const dateHeads = tables.map(t => {
                    const th = t.querySelector('th.shisetsu');
                    return th ? th.innerText.trim() : '(no date)';
                });
                return { tableCount: tables.length, dates: dateHeads };
            }
        """)
        console.print(f"  時間帯別テーブル数: {info['tableCount']}")
        console.print(f"  各テーブルの日付: {info['dates']}")
        for sym in ["○", "△", "×"]:
            console.print(f"  記号'{sym}': {html.count(sym)}回")

        browser.close()
    console.print("\n[green]→ 03_jikantai_multi.html 保存[/green]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
