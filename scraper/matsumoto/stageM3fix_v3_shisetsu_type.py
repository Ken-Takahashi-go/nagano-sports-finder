"""
Stage M3-fix v3: 施設種類検索でテニス・サッカー施設の webR ID を取得

発見 (使用目的か_01.html の解析):
  webR 空き照会画面に「施設種類から探す」タブがあり、
  radioShisetsuMiddle ラジオで施設種別を選択 → searchShisetsu() で検索:
    01=体育館 02=剣道場 03=柔道室 04=卓球室 05=サッカー場 06=野球場
    07=庭球場 08=運動広場 09=ゲートボール場 10=トレーニング室
    11=競技場 12=球場 13=会議室
  検索ボタン: <input id="btnSearchViaShisetsu" onclick="searchShisetsu();">

戦略:
  A3スコープ (テニス + サッカー/フットサル) をカバーする施設種別を順に検索:
    05 サッカー場 / 07 庭球場 / 08 運動広場 / 11 競技場
  各検索結果の checkShisetsu (value=external_facility_id, name) を採取・統合

出力:
  - outputs/matsumoto_M3fix_v3_facilities.json
  - outputs/matsumoto_M3fix_v3_screenshots/
"""
from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

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
BASE_URL = "https://yoyaku.city.matsumoto.lg.jp"
SHOTS = SCRIPT_DIR / "outputs" / "matsumoto_M3fix_v3_screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)
OUTPUT_JSON = SCRIPT_DIR / "outputs" / "matsumoto_M3fix_v3_facilities.json"

console = Console()

# A3スコープをカバーする施設種別 (value, 名称)
TARGET_TYPES = [
    ("05", "サッカー場"),
    ("07", "庭球場"),
    ("08", "運動広場"),
    ("11", "競技場"),
]


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


def goto_kuki(page) -> None:
    page.goto(f"{BASE_URL}/WebR/", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(1500)
    page.locator("text=空き照会").first.click()
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(1500)


def search_by_type(page, type_value: str, type_name: str) -> list[dict]:
    """施設種類で検索 → checkShisetsu 採取"""
    goto_kuki(page)

    # 「施設種類から探す」タブをアクティブ化
    try:
        tab = page.locator("a:has-text('施設種類から探す')").first
        if tab.is_visible(timeout=3000):
            tab.click()
            page.wait_for_timeout(600)
    except Exception:
        console.print(f"  [dim]タブ切替スキップ（既に表示済みか）[/dim]")

    # 施設種別 radio を label クリック
    radio_id = f"radioShisetsuMiddle{type_value}"
    label = page.locator(f"label[for='{radio_id}']").first
    label.click(force=True)
    page.wait_for_timeout(400)

    # 検索実行 (searchShisetsu() → __doPostBack('btnSearchViaShisetsu',''))
    try:
        page.evaluate("() => searchShisetsu()")
    except Exception:
        # フォールバック: ボタン直接クリック
        page.locator("#btnSearchViaShisetsu").first.click(force=True)
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(1500)

    snapshot(page, f"type{type_value}_{type_name}")
    items = extract_checkboxes(page, type_name)
    return items


def main() -> int:
    console.print("[bold green]Stage M3-fix v3: 施設種類でテニス・サッカー施設取得[/bold green]\n")

    all_facilities: list[dict] = []
    seen_values: set[str] = set()

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
                new = [i for i in items if i["value"] not in seen_values]
                console.print(f"  → {len(items)}件 (新規 {len(new)}件)")
                for it in items:
                    console.print(f"     [{it['value']}] {it['name']}")
                for it in new:
                    seen_values.add(it["value"])
                    all_facilities.append(it)
            except Exception as e:
                console.print(f"  [red]失敗: {e}[/red]")
            console.print("")

        browser.close()

    # 集計
    console.print(f"[bold]全 {len(all_facilities)}件 検出[/bold]")
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
    console.print(f"\n[bold green]-> 保存: {OUTPUT_JSON.name}[/bold green]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
