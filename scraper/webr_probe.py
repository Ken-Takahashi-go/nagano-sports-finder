"""
webR 汎用 probe: 任意の webR市の施設種類番号 + スポーツ施設リストを自動取得

Phase 2 webR系の横展開用。施設種類番号は自治体ごとにカスタムのため、
施設種類タブの全 radioShisetsuMiddle を取得して体育館/テニス/サッカー等を
ラベルから自動分類し、該当種別で施設(checkShisetsu)を採取する。

対象: 茅野市・諏訪市・岡谷市 (Phase 2一次調査で webR と判明)
出力: outputs/webr_probe_{key}.json （施設種類番号 + 施設リスト）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from webr_core import USER_AGENT, console, goto_kuki  # noqa: E402

SCRIPT_DIR = Path(__file__).parent
SHOTS = SCRIPT_DIR / "outputs" / "webr_probe_screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)

CITIES = {
    "chino": ("茅野市", "https://www.pf489.com/chino"),
    "suwa": ("諏訪市", "https://www.pf489.com/suwa"),
    "okaya": ("岡谷市", "https://www.pf489.com/okaya"),
}


def classify(label: str) -> str | None:
    """施設種類ラベル → スポーツ分類 (A3スコープ: 体育館/テニス/サッカー/フットサル/グラウンド)"""
    if "アリーナ" in label or "体育館" in label:
        return "体育館"
    if "テニス" in label or "庭球" in label:
        return "テニス"
    if "フットサル" in label:
        return "フットサル"
    if "サッカー" in label:
        return "サッカー"
    if "運動広場" in label or "グラウンド" in label or "運動場" in label or "多目的" in label:
        return "グラウンド"
    return None


def get_shisetsu_types(page) -> list[dict]:
    return page.evaluate("""
        () => Array.from(document.querySelectorAll("input[name='radioShisetsuMiddle']")).map(r => {
            const l = document.querySelector(`label[for='${r.id}']`);
            return { value: r.value, label: l ? l.textContent.trim() : null };
        })
    """)


def extract_checkboxes(page) -> list[dict]:
    return page.evaluate("""
        () => Array.from(document.querySelectorAll("input[name='checkShisetsu']")).map(c => {
            const l = document.querySelector(`label[for='${c.id}']`);
            return { value: c.value, name: l ? l.textContent.trim() : null };
        })
    """)


def open_shisetsu_tab(page) -> None:
    try:
        tab = page.locator("a:has-text('施設種類から探す')").first
        if tab.is_visible(timeout=3000):
            tab.click()
            page.wait_for_timeout(600)
    except Exception:
        pass


def search_type(page, base_url: str, type_value: str) -> list[dict]:
    goto_kuki(page, base_url)
    open_shisetsu_tab(page)
    page.locator(f"label[for='radioShisetsuMiddle{type_value}']").first.click(force=True)
    page.wait_for_timeout(400)
    try:
        page.evaluate("() => searchShisetsu()")
    except Exception:
        page.locator("#btnSearchViaShisetsu").first.click(force=True)
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(1500)
    return extract_checkboxes(page)


def probe_city(page, key: str, name: str, base_url: str) -> dict:
    console.print(f"\n[bold cyan]===== {name} ({base_url}) =====[/bold cyan]")
    goto_kuki(page, base_url)
    open_shisetsu_tab(page)
    types = get_shisetsu_types(page)
    console.print(f"  施設種類: {[(t['value'], t['label']) for t in types]}")

    # 分類 → 対象種別
    target: dict[str, list[tuple]] = {}
    for t in types:
        c = classify(t["label"] or "")
        if c:
            target.setdefault(c, []).append((t["value"], t["label"]))
    console.print(f"  対象分類: { {k: [v[0] for v in vs] for k, vs in target.items()} }")

    facilities: list[dict] = []
    seen: set[str] = set()
    for sport, tvs in target.items():
        for tv, tlabel in tvs:
            try:
                items = search_type(page, base_url, tv)
                new = [i for i in items if i["value"] not in seen]
                console.print(f"  [{sport}/{tlabel}({tv})] {len(items)}件 (新規{len(new)})")
                for it in new:
                    seen.add(it["value"])
                    it["sport_class"] = sport
                    it["type_value"] = tv
                    facilities.append(it)
            except Exception as e:
                console.print(f"  [red]{sport}/{tv} 失敗: {e}[/red]")

    result = {
        "city": name, "key": key, "base_url": base_url,
        "shisetsu_types": types,
        "facilities": facilities,
    }
    out = SCRIPT_DIR / "outputs" / f"webr_probe_{key}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"  [green]→ {out.name}: {len(facilities)}施設[/green]")
    return result


def main() -> int:
    console.print("[bold green]webR 汎用 probe (茅野・諏訪・岡谷)[/bold green]")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, locale="ja-JP",
                                      viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.set_default_timeout(20000)
        for key, (name, base_url) in CITIES.items():
            try:
                probe_city(page, key, name, base_url)
            except Exception as e:
                console.print(f"[red]{name} 全体失敗: {e}[/red]")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
