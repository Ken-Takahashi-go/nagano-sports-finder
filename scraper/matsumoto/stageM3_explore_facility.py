"""
Stage M3: 1施設をクリックして空き状況画面に進む PoC

戦略:
  1. webR トップ → 空き照会・予約の申込
  2. zenshisetsu (全施設) で table を表示
  3. table[0] の特定施設行で「案内」または施設名をクリック
  4. 遷移後の画面 (施設詳細) を解析
  5. さらに「空き状況」へ進める方法を特定

ターゲット: 総合体育館 (MAT-GYM-001 エア・ウォーターアリーナ松本)

出力:
  - outputs/matsumoto_M3_screenshots/  各画面のHTML+PNG
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from rich.console import Console

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
TARGET_FACILITY = "総合体育館"  # エア・ウォーターアリーナ松本
SHOTS = SCRIPT_DIR / "outputs" / "matsumoto_M3_screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)

console = Console()
postback_pattern = re.compile(r"__doPostBack\([\"']([^\"']+)[\"'],\s*[\"']([^\"']*)[\"']\)")


def snapshot(page, name: str) -> None:
    html = page.content()
    (SHOTS / f"{name}.html").write_text(html, encoding="utf-8")
    page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)
    console.print(f"  [dim]→ {name}.html, {name}.png ({len(html):,}B)[/dim]")


def main() -> int:
    console.print(f"[bold green]Stage M3: 1施設の空き状況画面探索[/bold green]")
    console.print(f"対象: 「{TARGET_FACILITY}」\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, locale="ja-JP",
                                      viewport={"width": 1280, "height": 900})
        page = context.new_page()

        # =================================================================
        # Step 1-3: webR → 空き照会 → 全施設
        # =================================================================
        console.print("[cyan]Step 1: webR トップ[/cyan]")
        page.goto(f"{BASE_URL}/WebR/", wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2000)
        snapshot(page, "01_top")

        console.print("\n[cyan]Step 2: 空き照会・予約の申込 をクリック[/cyan]")
        page.locator("text=空き照会").first.click()
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        snapshot(page, "02_after_kuki")
        console.print(f"  → URL: {page.url}")

        console.print("\n[cyan]Step 3: 「全施設」(zenshisetsu)[/cyan]")
        page.evaluate("() => __doPostBack('zenshisetsu', '')")
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        snapshot(page, "03_zenshisetsu")
        console.print(f"  → URL: {page.url}")

        # ★ 全 checkbox の (id, value, label) を取得 (Bonus: 全施設マッピングの素材)
        console.print(f"\n[cyan]Step 3b: 全 checkShisetsu の (id, value, name) 抽出[/cyan]")
        all_checkboxes = page.evaluate("""
            () => Array.from(document.querySelectorAll("input[name='checkShisetsu']")).map(c => {
                const label = document.querySelector(`label[for='${c.id}']`);
                return {
                    id: c.id,
                    value: c.value,
                    name: label ? label.textContent.trim() : null
                };
            })
        """)
        console.print(f"  → 検出: {len(all_checkboxes)} 件")
        for cb in all_checkboxes[:15]:
            console.print(f"    id={cb['id'][:25]:<25s} value={cb['value']:<10s} name={cb['name']}")
        if len(all_checkboxes) > 15:
            console.print(f"    [dim]...他 {len(all_checkboxes) - 15}件[/dim]")

        # JSON 保存 (Stage M4 で使う素材)
        import json
        cb_path = SHOTS.parent / "matsumoto_M3_all_checkboxes.json"
        cb_path.write_text(
            json.dumps(all_checkboxes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        console.print(f"  [green]→ 保存: {cb_path.name}[/green]")

        # =================================================================
        # Step 4: 「総合体育館」のチェックボックスを選択
        # =================================================================
        console.print(f"\n[cyan]Step 4: 「{TARGET_FACILITY}」のチェックボックスを選択[/cyan]")

        # スイッチUI (label) をクリック (checkbox 本体は CSS で隠れている)
        check_ok = False
        try:
            # 戦略: label[for=checkShisetsuXXX] をクリック
            label = page.locator(f"label:has-text('{TARGET_FACILITY}')").first
            if label.is_visible(timeout=3000):
                # 対応する checkbox の value (= 施設ID) を取得
                for_attr = label.get_attribute("for")
                if for_attr:
                    facility_id_input = page.locator(f"input#{for_attr}").first
                    facility_id = facility_id_input.get_attribute("value")
                    console.print(f"  → label の for='{for_attr}', 施設ID='{facility_id}'")

                # label クリック (force=True で確実に)
                label.click(force=True)
                page.wait_for_timeout(500)
                check_ok = True
                console.print(f"  → ✓ label クリック成功")

                # 念のため checkbox の状態確認
                try:
                    is_checked = page.locator(f"input#{for_attr}").is_checked()
                    console.print(f"  → checkbox state: {is_checked}")
                except Exception:
                    pass
            else:
                console.print(f"  [yellow]label が見えない[/yellow]")
        except Exception as e:
            console.print(f"  [yellow]label クリック失敗: {e}[/yellow]")
            # フォールバック: checkbox を force check
            try:
                row = page.locator(f"tr:has-text('{TARGET_FACILITY}')").first
                checkbox = row.locator("input[type='checkbox']").first
                checkbox.check(force=True)
                check_ok = True
                console.print(f"  → フォールバック: checkbox force check 成功")
            except Exception as e2:
                console.print(f"  [red]フォールバックも失敗: {e2}[/red]")

        # 画面下のボタンを探してクリック
        console.print(f"\n[cyan]Step 5: 「次へ」「申込」「空き照会」ボタンを探す[/cyan]")
        clicked = False
        for btn_text in ["次へ", "申込", "予約", "空き照会", "検索", "決定", "確定"]:
            for selector in [
                f"input[type='submit'][value*='{btn_text}']",
                f"input[type='button'][value*='{btn_text}']",
                f"button:has-text('{btn_text}')",
                f"a:has-text('{btn_text}')",
            ]:
                try:
                    el = page.locator(selector).first
                    if el.is_visible(timeout=1500):
                        # クリック前のURL記録
                        before_url = page.url
                        el.click()
                        page.wait_for_load_state("networkidle", timeout=15000)
                        page.wait_for_timeout(1500)
                        # 何か変化があったか
                        after_url = page.url
                        if after_url != before_url or "空き" in page.content():
                            clicked = True
                            console.print(f"  → 「{btn_text}」({selector}) クリック → URL: {after_url}")
                            break
                except Exception:
                    continue
            if clicked:
                break

        if not clicked:
            console.print(f"  [yellow]いずれのボタンも見つからず。画面下のすべてのボタンを列挙:[/yellow]")
            for el in page.locator("input[type='submit'], input[type='button'], button").all()[:30]:
                try:
                    val = el.get_attribute("value") or el.inner_text() or ""
                    name = el.get_attribute("name") or ""
                    if val.strip():
                        console.print(f"    [name='{name[:30]}'] value='{val[:40]}'")
                except Exception:
                    pass

        snapshot(page, "04_after_click")
        console.print(f"\n[bold green]✓ 現在の URL: {page.url}[/bold green]")

        # =================================================================
        # Step 5: 遷移後画面の解析
        # =================================================================
        console.print(f"\n[cyan]Step 5: 遷移後画面 解析[/cyan]")
        html = page.content()
        soup = BeautifulSoup(html, "lxml")

        title = soup.title.get_text(strip=True) if soup.title else "(no title)"
        console.print(f"  title: {title}")
        console.print(f"  body長: {len(soup.get_text()):,} 文字")
        console.print(f"  table数: {len(soup.find_all('table'))}")

        # キーワードカウント
        text = soup.get_text()
        console.print(f"\n[bold]キーワード検出:[/bold]")
        for kw in ["空き", "○", "×", "△", "空き状況", "予約可", "予約済",
                   "日付", "時間", "カレンダー", "週", "月"]:
            count = text.count(kw)
            color = "green" if count > 0 else "dim"
            console.print(f"  [{color}]'{kw}': {count}回[/{color}]")

        # 日付・時刻パターン
        date_pat = re.compile(r"\d{1,2}月\d{1,2}日|\d{4}[/-]\d{1,2}[/-]\d{1,2}")
        time_pat = re.compile(r"\d{1,2}:\d{2}")
        console.print(f"\n[bold]日付/時刻:[/bold]")
        console.print(f"  日付パターン: {len(date_pat.findall(text))}件")
        console.print(f"  時刻パターン: {len(time_pat.findall(text))}件")

        # PostBack ターゲット
        postbacks = postback_pattern.findall(html)
        console.print(f"\n[bold]__doPostBack ターゲット (上位20):[/bold]")
        from collections import Counter
        tgt_counter = Counter([t for t, a in postbacks])
        for tgt, count in tgt_counter.most_common(20):
            console.print(f"  [{count:2d}x] {tgt}")

    console.print(f"\n[bold]次のステップ:[/bold]")
    console.print(f"  - outputs/matsumoto_M3_screenshots/04_facility_detail.png を確認")
    console.print(f"  - 空き状況/カレンダー画面に到達できたか判定")

    return 0


if __name__ == "__main__":
    sys.exit(main())
