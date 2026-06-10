"""
塩尻 webR 時間帯別空き状況の取得検証 (ハイブリッド対応の事前調査)

webRには2画面:
  - 施設別空き状況(カレンダー): 1日1コマ集約 (webr_core が現在取得)
  - 時間帯別空き状況: 日付選択 → その日の 時間帯×部屋 の○△×

フロー検証:
  webr_core.fetch_facility_calendar で施設別空き状況に到達
  → checkdate(日付)を1つ選択 → __doPostBack('next') → 時間帯別空き状況
  → 時間帯ヘッダ・部屋・○△× の構造を確認

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
    console.print("[bold green]塩尻 時間帯別空き状況 取得検証[/bold green]\n")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(user_agent=USER_AGENT, locale="ja-JP",
                                   viewport={"width": 1280, "height": 900}).new_page()
        page.set_default_timeout(20000)

        # 1. 施設別空き状況(カレンダー)に到達
        html = fetch_facility_calendar(page, SHIOJIRI, "215001", "市立体育館", "00")
        console.print(f"[cyan]施設別空き状況 到達 ({len(html):,}B)[/cyan]")
        (SHOTS / "01_shisetsubetsu.html").write_text(html, encoding="utf-8")

        # 2. 最初の予約可能な日付(checkdate)を選択
        cds = page.evaluate("""
            () => Array.from(document.querySelectorAll("input[name='checkdate']")).slice(0,5)
                .map(c => ({ id: c.id, value: c.value,
                             label: (document.querySelector(`label[for='${c.id}']`)||{}).textContent || '' }))
        """)
        console.print(f"  checkdate サンプル: {cds[:3]}")
        # △ or ○ の日付を選ぶ
        target = None
        for c in cds:
            if "△" in c["label"] or "○" in c["label"]:
                target = c
                break
        target = target or (cds[0] if cds else None)
        if not target:
            console.print("[red]checkdate が無い[/red]")
            browser.close()
            return 1
        console.print(f"  選択日付: id={target['id']} label={target['label']!r}")
        page.locator(f"label[for='{target['id']}']").first.click(force=True)
        page.wait_for_timeout(500)

        # 3. 次へ進む → 時間帯別空き状況
        page.evaluate("() => __doPostBack('next', '')")
        page.wait_for_load_state("networkidle", timeout=25000)
        page.wait_for_timeout(2000)
        html2 = page.content()
        (SHOTS / "02_jikantai.html").write_text(html2, encoding="utf-8")
        page.screenshot(path=str(SHOTS / "02_jikantai.png"), full_page=True)
        console.print(f"\n[cyan]遷移後 ({len(html2):,}B)[/cyan]")
        console.print(f"  URL: {page.url}")
        console.print(f"  title: {page.title()}")

        # 4. 時間帯別構造の確認
        for sym in ["○", "△", "×", "－"]:
            console.print(f"  記号'{sym}': {html2.count(sym)}回")
        # 時間帯ヘッダ・部屋名
        heads = page.evaluate("() => Array.from(document.querySelectorAll('th,td')).map(e=>e.innerText.trim()).filter(t=>/[0-9]{1,2}:[0-9]{2}|全面|半面|アリーナ|定員/.test(t)).slice(0,20)")
        console.print(f"  時間帯/部屋ヘッダ: {heads}")
        # チェックボックス(予約セル)のvalue
        slots = page.evaluate("""
            () => Array.from(document.querySelectorAll("input[type='checkbox']")).slice(0,8)
                .map(c => ({ name: c.name, value: c.value }))
        """)
        console.print(f"  予約セル サンプル: {slots}")

        browser.close()
    console.print("\n[green]→ outputs/shiojiri_timeslot_screenshots/ に保存[/green]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
