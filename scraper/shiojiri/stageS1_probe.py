"""
Stage S1: 塩尻市 webR が松本市と同一構造か検証する probe

目的:
  Phase 2 一次調査で「塩尻市 = 松本市と同じ webR エンジン」と判明。
  松本スクレイパー(matsumoto/stageM3fix_v3 + stageM6)のロジックが
  ホスト差し替えのみで流用できるかを実証する。

検証項目:
  1. 「空き照会」導線が松本と同じか
  2. 施設種類タブ + radioShisetsuMiddle(体育館01/サッカー場05/庭球場07) があるか
  3. 検索結果に checkShisetsu が出るか (施設マッピング素材)
  4. 1施設選択 → __doPostBack('next') → カレンダーに checkdate があるか
  5. カレンダー value が松本と同じ YYYYMMDD+TTT+RR エンコードか

ホスト差分:
  松本: https://yoyaku.city.matsumoto.lg.jp  + /WebR/
  塩尻: https://www.pf489.com/shiojiri        + /WebR/
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from rich.console import Console

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

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

BASE_URL = "https://www.pf489.com/shiojiri"
SHOTS = SCRIPT_DIR / "outputs" / "shiojiri_S1_screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)
OUTPUT_JSON = SCRIPT_DIR / "outputs" / "shiojiri_S1_facilities.json"

console = Console()
VALUE_PATTERN = re.compile(r"^(\d{8})(\d{3})(\d{2})\s*(\d*)$")

# 塩尻の施設種類番号 (松本とは別体系: 00=アリーナ, 13=テニス, 10=サッカー)
TARGET_TYPES = [("00", "アリーナ"), ("13", "テニスコート"), ("10", "サッカー場")]


def snapshot(page, name: str) -> None:
    try:
        (SHOTS / f"{name}.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)
    except Exception as e:
        console.print(f"  [dim]snapshot {name} 失敗: {e}[/dim]")


def extract_checkboxes(page, type_name: str) -> list[dict]:
    items = page.evaluate("""
        () => Array.from(document.querySelectorAll("input[name='checkShisetsu']")).map(c => {
            const label = document.querySelector(`label[for='${c.id}']`);
            return { id: c.id, value: c.value,
                     name: label ? label.textContent.trim() : null };
        })
    """)
    for it in items:
        it["shisetsu_type"] = type_name
    return items


def goto_kuki(page) -> bool:
    """webR → 空き照会。松本と同じ導線か検証"""
    page.goto(f"{BASE_URL}/WebR/", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(1500)
    snapshot(page, "01_top")
    # 「空き照会」リンク
    link = page.locator("text=空き照会").first
    if link.count() == 0 or not link.is_visible(timeout=3000):
        console.print("  [red]「空き照会」リンクが見つからない (構造差異の可能性)[/red]")
        return False
    link.click()
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(1500)
    snapshot(page, "02_after_kuki")
    return True


def search_by_type(page, type_value: str, type_name: str) -> list[dict]:
    if not goto_kuki(page):
        return []
    # 施設種類タブ
    try:
        tab = page.locator("a:has-text('施設種類から探す')").first
        if tab.is_visible(timeout=3000):
            tab.click()
            page.wait_for_timeout(600)
    except Exception:
        pass
    # radio
    radio = page.locator(f"label[for='radioShisetsuMiddle{type_value}']").first
    if radio.count() == 0:
        console.print(f"  [yellow]radioShisetsuMiddle{type_value} 無し[/yellow]")
        return []
    radio.click(force=True)
    page.wait_for_timeout(400)
    # 検索
    try:
        page.evaluate("() => searchShisetsu()")
    except Exception:
        try:
            page.locator("#btnSearchViaShisetsu").first.click(force=True)
        except Exception:
            return []
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(1500)
    snapshot(page, f"03_type{type_value}_{type_name}")
    return extract_checkboxes(page, type_name)


def try_calendar(page, ext_id: str, name: str) -> dict:
    """1施設選択 → next → カレンダー構造確認"""
    result = {"ext_id": ext_id, "name": name, "reached": False, "rooms": 0, "sample_value": None}
    cb_id = f"checkShisetsu{ext_id}"
    try:
        page.wait_for_selector(f"#{cb_id}", timeout=10000, state="attached")
        page.locator(f"label[for='{cb_id}']").first.click(force=True)
        page.wait_for_timeout(400)
        page.evaluate("() => __doPostBack('next', '')")
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(1500)
        snapshot(page, f"04_calendar_{ext_id}")
        html = page.content()
        if "checkdate" not in html:
            return result
        result["reached"] = True
        soup = BeautifulSoup(html, "lxml")
        cbs = soup.find_all("input", attrs={"name": "checkdate"})
        rooms = set()
        for cb in cbs:
            m = VALUE_PATTERN.match(cb.get("value", "").strip())
            if m:
                rooms.add(m.group(3))
                if result["sample_value"] is None:
                    result["sample_value"] = cb.get("value")
        result["rooms"] = len(rooms)
        result["checkdate_count"] = len(cbs)
    except Exception as e:
        result["error"] = str(e)[:80]
    return result


def main() -> int:
    console.print("[bold green]Stage S1: 塩尻 webR 構造検証[/bold green]")
    console.print(f"[dim]BASE_URL: {BASE_URL}[/dim]\n")

    all_facilities: list[dict] = []
    seen: set[str] = set()
    calendar_check = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, locale="ja-JP",
                                      viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.set_default_timeout(20000)

        for type_value, type_name in TARGET_TYPES:
            console.print(f"[cyan]>>> 施設種別 {type_value} = {type_name}[/cyan]")
            try:
                items = search_by_type(page, type_value, type_name)
                console.print(f"  → {len(items)}件")
                for it in items[:20]:
                    console.print(f"     [{it['value']}] {it['name']}")
                for it in items:
                    if it["value"] not in seen:
                        seen.add(it["value"])
                        all_facilities.append(it)
            except Exception as e:
                console.print(f"  [red]失敗: {e}[/red]")
            console.print("")

        # カレンダー検証 (体育館の先頭1施設)
        gyms = [f for f in all_facilities if f["shisetsu_type"] == "アリーナ"]
        if gyms:
            target = gyms[0]
            console.print(f"[cyan]>>> カレンダー検証: {target['name']} ({target['value']})[/cyan]")
            # アリーナで再検索してから選択
            search_by_type(page, "00", "アリーナ")
            calendar_check = try_calendar(page, target["value"], target["name"])
            console.print(f"  → {calendar_check}")

        browser.close()

    # 保存
    OUTPUT_JSON.write_text(json.dumps(all_facilities, ensure_ascii=False, indent=2), encoding="utf-8")

    # 判定
    console.print(f"\n[bold]===== 検証結果 =====[/bold]")
    console.print(f"検出施設数: {len(all_facilities)}")
    by_type = {}
    for f in all_facilities:
        by_type[f["shisetsu_type"]] = by_type.get(f["shisetsu_type"], 0) + 1
    for t, c in by_type.items():
        console.print(f"  {t}: {c}件")
    if calendar_check and calendar_check.get("reached"):
        console.print(f"[bold green][OK] カレンダー到達: 部屋{calendar_check['rooms']} "
                      f"checkdate{calendar_check.get('checkdate_count')} "
                      f"sample={calendar_check['sample_value']!r}[/bold green]")
        if calendar_check["sample_value"] and VALUE_PATTERN.match(calendar_check["sample_value"].strip()):
            console.print("[bold green][OK] value エンコードが松本と同一形式 → スクレイパー流用可能[/bold green]")
    else:
        console.print(f"[yellow][!] カレンダー検証: {calendar_check}[/yellow]")

    console.print(f"\n[green]→ 保存: {OUTPUT_JSON.name}[/green]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
