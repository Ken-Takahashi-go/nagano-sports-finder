"""
Stage M3-fix v2: 階層メニュー深掘りで全カテゴリ施設マッピング

戦略:
  Stage M3 で「カテゴリーから探す/使用目的から探す/施設種類から探す/施設名から探す/
  一覧から探す/体育施設」のメニューを発見済
  → 「カテゴリーから探す」を起点に階層を辿る
  → 各遷移先で checkShisetsu を採取し JSON 統合

出力:
  - outputs/matsumoto_M3fix_v2_all_facilities.json
  - outputs/matsumoto_M3fix_v2_screenshots/  各画面 HTML+PNG
"""
from __future__ import annotations

import io
import json
import os
import re
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
SHOTS = SCRIPT_DIR / "outputs" / "matsumoto_M3fix_v2_screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)
OUTPUT_JSON = SCRIPT_DIR / "outputs" / "matsumoto_M3fix_v2_all_facilities.json"

console = Console()


def snapshot(page, name: str) -> None:
    try:
        html = page.content()
        (SHOTS / f"{name}.html").write_text(html, encoding="utf-8")
        page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)
    except Exception as e:
        console.print(f"  [dim]snapshot {name} 失敗: {e}[/dim]")


def extract_checkboxes(page, category_hint: str) -> list[dict]:
    items = page.evaluate("""
        () => Array.from(document.querySelectorAll("input[name='checkShisetsu']")).map(c => {
            const label = document.querySelector(`label[for='${c.id}']`);
            return {
                id: c.id, value: c.value,
                name: label ? label.textContent.trim() : null
            };
        })
    """)
    for it in items:
        it["category"] = category_hint
    return items


def list_visible_links(page) -> list[dict]:
    return page.evaluate("""
        () => Array.from(document.querySelectorAll("a, input[type='submit'], input[type='button'], button"))
            .filter(b => b.offsetParent !== null)
            .map(b => ({
                text: (b.value || b.innerText || '').trim(),
                name: b.name || '',
                id: b.id || '',
                href: b.getAttribute('href') || ''
            }))
            .filter(b => b.text && b.text.length < 40)
    """)


def safe_click_by_text(page, text: str, timeout: int = 3000) -> bool:
    """テキストでクリック試行 (a, button, label, input value すべて)"""
    selectors = [
        f"a:text-is('{text}')",
        f"a:has-text('{text}')",
        f"input[type='submit'][value='{text}']",
        f"input[type='button'][value='{text}']",
        f"button:has-text('{text}')",
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=timeout):
                el.click(timeout=timeout)
                page.wait_for_load_state("networkidle", timeout=20000)
                page.wait_for_timeout(1500)
                return True
        except Exception:
            continue
    return False


def go_to_kuki(page) -> None:
    """webR top → 空き照会"""
    page.goto(f"{BASE_URL}/WebR/", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(2000)
    page.locator("text=空き照会").first.click()
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(2000)


def explore_menu(page, menu_text: str, snap_prefix: str, depth: int = 0) -> list[dict]:
    """1つの探索メニュー(カテゴリーから探す等)に入って checkbox 全採取"""
    found: list[dict] = []
    seen_vals: set[str] = set()

    console.print(f"\n[cyan]>>> 「{menu_text}」へ遷移[/cyan]")
    go_to_kuki(page)
    if not safe_click_by_text(page, menu_text):
        console.print(f"  [yellow]「{menu_text}」クリック失敗[/yellow]")
        return found
    snapshot(page, f"{snap_prefix}_01")

    # この画面の checkbox を即時採取
    immediate = extract_checkboxes(page, menu_text)
    if immediate:
        console.print(f"  → 即時 checkShisetsu: {len(immediate)}件")
        for it in immediate:
            if it["value"] not in seen_vals:
                seen_vals.add(it["value"])
                found.append(it)

    # この画面のリンク候補を列挙
    links = list_visible_links(page)
    # 興味があるカテゴリ語
    interest_words = [
        "体育", "テニス", "庭球", "サッカー", "フットサル",
        "グラウンド", "球技", "公園", "屋内", "屋外",
        "アリーナ", "体育館", "コート", "市民", "総合",
    ]

    # ノイズ語 (除外)
    noise = ["ログイン", "メッセージ", "ご利用", "色・", "メニュー",
             "マイメニュー", "抽選", "申請", "決済", "AED",
             "TOP", "戻る", "ホーム", "予約状況"]

    drill_candidates = []
    for l in links:
        t = l["text"]
        if any(n in t for n in noise):
            continue
        if any(w in t for w in interest_words):
            drill_candidates.append(t)

    # 重複削除 + 上位 N 件
    seen_text: set[str] = set()
    unique_candidates = []
    for t in drill_candidates:
        if t not in seen_text:
            seen_text.add(t)
            unique_candidates.append(t)

    console.print(f"  深掘り候補: {unique_candidates[:15]}")

    # 各候補に入って checkbox 取得
    for idx, sub_text in enumerate(unique_candidates[:12], start=1):
        try:
            console.print(f"\n  [dim]>> 「{sub_text}」 (level{depth+1})[/dim]")
            # 戻ってから再遷移 (各 sub_text 独立)
            go_to_kuki(page)
            if not safe_click_by_text(page, menu_text):
                continue
            if not safe_click_by_text(page, sub_text):
                console.print(f"    [yellow]サブクリック失敗[/yellow]")
                continue
            snapshot(page, f"{snap_prefix}_sub{idx:02d}_{sub_text[:8]}")
            items = extract_checkboxes(page, f"{menu_text} > {sub_text}")
            new = [i for i in items if i["value"] not in seen_vals]
            console.print(f"    -> {len(items)}件 (新規{len(new)}件)")
            for it in new:
                seen_vals.add(it["value"])
                found.append(it)
        except Exception as e:
            console.print(f"    [yellow]例外: {e}[/yellow]")
            continue

    return found


def main() -> int:
    console.print("[bold green]Stage M3-fix v2: 階層深掘り全件マッピング[/bold green]\n")

    all_facilities: list[dict] = []
    seen_values: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=USER_AGENT, locale="ja-JP",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()
        page.set_default_timeout(20000)

        # 探索メニュー候補 (優先順)
        # 「使用目的から探す」「カテゴリーから探す」がスポーツ系で当たりやすい
        for menu in ["使用目的から探す", "カテゴリーから探す", "施設種類から探す"]:
            try:
                items = explore_menu(page, menu, snap_prefix=menu[:5])
                console.print(f"[bold]「{menu}」結果: {len(items)}件[/bold]")
                for it in items:
                    if it["value"] not in seen_values:
                        seen_values.add(it["value"])
                        all_facilities.append(it)
            except Exception as e:
                console.print(f"[red]「{menu}」全体例外: {e}[/red]")

        browser.close()

    # ----------------------------------------------------------------
    # 集計
    # ----------------------------------------------------------------
    console.print(f"\n[bold]全 {len(all_facilities)}件 検出[/bold]")
    prefix_counts: dict[str, int] = {}
    for f in all_facilities:
        pfx = f["value"][:4] if len(f["value"]) >= 4 else f["value"]
        prefix_counts[pfx] = prefix_counts.get(pfx, 0) + 1
    console.print("[bold]value プレフィックス別:[/bold]")
    for pfx, cnt in sorted(prefix_counts.items()):
        console.print(f"  {pfx}xx: {cnt}件")

    # サンプル表示
    console.print("\n[bold]サンプル(各 prefix 先頭3件):[/bold]")
    by_prefix: dict[str, list[dict]] = {}
    for f in all_facilities:
        pfx = f["value"][:4]
        by_prefix.setdefault(pfx, []).append(f)
    for pfx in sorted(by_prefix.keys()):
        for f in by_prefix[pfx][:3]:
            console.print(f"  [{pfx}] {f['value']}: {f['name']} ({f['category']})")

    OUTPUT_JSON.write_text(
        json.dumps(all_facilities, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    console.print(f"\n[bold green]-> 保存: {OUTPUT_JSON.name}[/bold green]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
