"""
Stage M2: 松本市 webR から施設一覧を取得し、IDマッピング作成

戦略:
  1. Playwright で webR トップ → 検索/予約画面へ進む (__doPostBack をクリックで再現)
  2. 施設一覧画面で全 (facility_id, facility_name) を抽出
  3. DB の facilities テーブルとマッチング (名前で fuzzy)
  4. JSON + 候補 SQL を出力

注意:
  - ASP.NET WebForms 系なので Playwright が必須
  - 速度より動作優先

出力:
  - outputs/matsumoto_M2_facility_list.json  webR内施設リスト
  - outputs/matsumoto_M2_matching.csv         DB施設とのマッチング結果
  - outputs/matsumoto_M2_screenshots/         各画面のスクリーンショット
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from rich.console import Console
from rich.table import Table

SCRIPT_DIR = Path(__file__).parent.parent  # scraper/
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
TOP_URL = f"{BASE_URL}/WebR/Home/WgR_ModeSelect"
OUTPUTS = SCRIPT_DIR / "outputs"
OUTPUTS.mkdir(exist_ok=True)
SHOTS = OUTPUTS / "matsumoto_M2_screenshots"
SHOTS.mkdir(exist_ok=True)

console = Console()


def snapshot(page, name: str) -> None:
    """画面遷移ごとに HTML + PNG を保存 (デバッグ用)"""
    html_path = SHOTS / f"{name}.html"
    png_path = SHOTS / f"{name}.png"
    html_path.write_text(page.content(), encoding="utf-8")
    page.screenshot(path=str(png_path), full_page=True)
    console.print(f"  [dim]→ {html_path.name}, {png_path.name}[/dim]")


def main() -> int:
    console.print(f"[bold green]Stage M2: 松本市 webR 施設マッピング[/bold green]\n")

    facilities_found: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=USER_AGENT,
            locale="ja-JP",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        # =================================================================
        # Step 1: トップ → 使用予約モード
        # =================================================================
        console.print("[cyan]Step 1: webR トップに遷移[/cyan]")
        page.goto(TOP_URL, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2000)
        console.print(f"  → {page.url}")
        snapshot(page, "01_top")

        # 「空き照会・予約の申込」を探してクリック (M1解析で判明したラベル)
        console.print("\n[cyan]Step 2: 「空き照会・予約の申込」を選択[/cyan]")
        clicked = False
        for selector in [
            "text=空き照会・予約の申込",
            "text=空き照会",
            "a:has-text('空き照会')",
            "a:has-text('予約の申込')",
            "input[value*='空き']",
            "button:has-text('空き')",
        ]:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=2000):
                    el.click()
                    clicked = True
                    console.print(f"  → clicked: {selector}")
                    break
            except Exception:
                continue

        if not clicked:
            # フォールバック: ページ上のボタンを列挙
            console.print("[yellow]  → 「使用予約」が見つからない。ボタン一覧表示:[/yellow]")
            for el in page.locator("input[type=button], input[type=submit], button, a").all()[:20]:
                try:
                    text = el.inner_text() or el.get_attribute("value") or ""
                    if text.strip():
                        console.print(f"    [{el.evaluate('el => el.tagName')}] {text[:50]}")
                except Exception:
                    pass
            console.print("[red]  → 自動継続は中断。outputs/matsumoto_M2_screenshots/01_top.html を確認[/red]")
            browser.close()
            return 1

        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        console.print(f"  → 遷移後 URL: {page.url}")
        snapshot(page, "02_after_mode")

        # =================================================================
        # Step 3: 施設一覧/検索画面の解析
        # =================================================================
        console.print("\n[cyan]Step 3: 施設一覧/検索画面解析[/cyan]")

        html = page.content()
        soup = BeautifulSoup(html, "lxml")

        # 想定: ドロップダウン or リンクリストで施設名が並んでいる
        # SELECT options
        console.print(f"\n[bold]SELECT > OPTION 一覧:[/bold]")
        for select in soup.find_all("select"):
            name = select.get("name", "?")
            options = select.find_all("option")
            console.print(f"  <select name='{name}'> ({len(options)} options)")
            for opt in options[:10]:
                val = opt.get("value", "")
                text = opt.get_text(strip=True)
                console.print(f"    value='{val[:30]}' label='{text[:60]}'")
            if len(options) > 10:
                console.print(f"    [dim]...+ {len(options)-10}件[/dim]")

        # リンク (施設詳細遷移用?)
        console.print(f"\n[bold]リンク一覧 (上位20):[/bold]")
        link_counter = Counter()
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            text = a.get_text(strip=True)[:40]
            if href and not href.startswith("#"):
                link_counter[(href, text)] += 1
        for (href, text), count in link_counter.most_common(20):
            console.print(f"  [{count:2d}x] {text[:40]:<40s} {href[:80]}")

        # 施設候補テキスト抽出 (体育館・テニス・サッカー等のキーワード)
        console.print(f"\n[bold]施設名候補のテキスト抽出:[/bold]")
        keywords = ["体育館", "テニス", "庭球", "サッカー", "アリーナ", "屋内運動場", "グリーンフィールド"]
        all_text = soup.get_text()
        for kw in keywords:
            count = all_text.count(kw)
            console.print(f"  '{kw}': {count}回")

        # 画面上の全テキスト抽出 (施設名らしきもの)
        # __doPostBack の引数として施設IDが入っているはず
        postback_pattern = re.compile(r"__doPostBack\([\"']([^\"']+)[\"'],\s*[\"']([^\"']*)[\"']\)")
        postbacks = postback_pattern.findall(html)
        if postbacks:
            console.print(f"\n[bold]__doPostBack 呼び出し (上位30):[/bold]")
            for target, arg in postbacks[:30]:
                console.print(f"  target='{target[:40]}' arg='{arg[:40]}'")

        # ASP.NET の VIEWSTATE 確認
        viewstate = soup.find("input", {"name": "__VIEWSTATE"})
        if viewstate:
            v = viewstate.get("value", "")
            console.print(f"\n[bold]__VIEWSTATE 検出: length={len(v)} chars[/bold]")
            console.print(f"  先頭: {v[:80]}...")

        # =================================================================
        # Step 4: 「全施設」(zenshisetsu) で施設一覧を表示
        # =================================================================
        console.print("\n[cyan]Step 4: zenshisetsu (全施設) で一覧表示[/cyan]")
        try:
            # __doPostBack を直接実行 (ASP.NET WebForms PostBack)
            page.evaluate("() => __doPostBack('zenshisetsu', '')")
            page.wait_for_load_state("networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            snapshot(page, "03_zenshisetsu")
            console.print(f"  → zenshisetsu PostBack 成功 (URL: {page.url})")
        except Exception as e:
            console.print(f"  → zenshisetsu 失敗: {e}")
            console.print("[yellow]  代替: btnSearchViaShisetsu を試行[/yellow]")
            try:
                page.evaluate("() => __doPostBack('btnSearchViaShisetsu', '')")
                page.wait_for_load_state("networkidle", timeout=30000)
                page.wait_for_timeout(2000)
                snapshot(page, "03_searchViaShisetsu")
                console.print(f"  → btnSearchViaShisetsu 成功 (URL: {page.url})")
            except Exception as e2:
                console.print(f"[red]  → 両方失敗: {e2}[/red]")

        # =================================================================
        # Step 5: 施設一覧解析
        # =================================================================
        console.print("\n[cyan]Step 5: 施設一覧解析[/cyan]")
        html = page.content()
        soup = BeautifulSoup(html, "lxml")

        # 競技別キーワード再カウント
        all_text = soup.get_text()
        console.print(f"\n[bold]施設名候補のキーワード再カウント:[/bold]")
        for kw in ["体育館", "テニス", "庭球", "サッカー", "アリーナ", "屋内運動場",
                   "グリーンフィールド", "扇子田", "美須々", "南部"]:
            count = all_text.count(kw)
            color = "green" if count > 0 else "dim"
            console.print(f"  [{color}]'{kw}': {count}回[/{color}]")

        # 施設リンク(__doPostBack)を抽出: 「shisetsu_」「facility_」「lstShisetsu」等
        postbacks2 = postback_pattern.findall(html)
        facility_targets = []
        for target, arg in postbacks2:
            # 施設候補と思われるターゲット名
            if any(kw in target.lower() for kw in ["shisetsu", "facility"]):
                # 既知の絞り込み系は除外
                if target not in ("searchShisetsuName", "shisetsuName", "zenshisetsu"):
                    facility_targets.append({"target": target, "arg": arg})

        console.print(f"\n[bold]施設候補 __doPostBack ターゲット ({len(facility_targets)}件):[/bold]")
        for ft in facility_targets[:30]:
            console.print(f"  target='{ft['target']}' arg='{ft['arg']}'")

        # __doPostBack 以外: リンクテキストで施設名らしきもの抽出
        console.print(f"\n[bold]リンクテキスト (上位30):[/bold]")
        for a in soup.find_all("a")[:50]:
            text = a.get_text(strip=True)
            if text and len(text) > 3:
                href = a.get("href", "")
                onclick = a.get("onclick", "")
                target_arg = ""
                # onclick 内の __doPostBack 引数も
                m = postback_pattern.search(onclick)
                if m:
                    target_arg = f"  → {m.group(1)} / {m.group(2)}"
                # 体育館/テニス等のキーワードを含むテキストだけ
                if any(kw in text for kw in ["体育館", "テニス", "庭球", "アリーナ",
                                              "サッカー", "屋内運動場", "扇子田",
                                              "グリーンフィールド", "美須々", "南部"]):
                    console.print(f"  [bold green]{text[:50]}[/bold green] {target_arg}")

        # テーブル(table)内に施設リストがある可能性
        tables = soup.find_all("table")
        console.print(f"\n[bold]table 要素: {len(tables)} 個[/bold]")
        for i, tbl in enumerate(tables[:3]):
            rows = tbl.find_all("tr")
            if len(rows) >= 3:
                console.print(f"  table[{i}]: {len(rows)} 行")
                for j, row in enumerate(rows[:5]):
                    text = row.get_text(separator="|", strip=True)
                    console.print(f"    行{j}: {text[:100]}")

        # =================================================================
        # Step 6: table[0] の施設行を解析 (施設名 + 案内リンクの onclick)
        # =================================================================
        console.print("\n[cyan]Step 6: table[0] の施設行から (name, postback_target) を抽出[/cyan]")
        extracted_facilities: list[dict] = []
        if tables:
            tbl = tables[0]
            rows = tbl.find_all("tr")
            for row in rows[1:]:  # ヘッダーをスキップ
                cells = row.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                # 施設名は 2番目のセル (お知らせ|施設名|...)
                name = cells[1].get_text(strip=True) if len(cells) >= 2 else ""
                if not name or name in ("施設名",):
                    continue

                # 「案内」リンクを探す: a タグの onclick or href
                onclick_target = None
                onclick_arg = None
                for a in row.find_all("a"):
                    onclick = a.get("onclick", "") or a.get("href", "")
                    m = postback_pattern.search(onclick)
                    if m:
                        onclick_target = m.group(1)
                        onclick_arg = m.group(2)
                        break
                    # input[onclick] の場合
                # input ボタンも確認
                for inp in row.find_all("input"):
                    onclick = inp.get("onclick", "")
                    m = postback_pattern.search(onclick)
                    if m:
                        onclick_target = m.group(1)
                        onclick_arg = m.group(2)
                        break

                extracted_facilities.append({
                    "name": name,
                    "postback_target": onclick_target,
                    "postback_arg": onclick_arg,
                    "category_id": "?",  # 後でssCategory別に取得する場合に使用
                })

        console.print(f"  → 抽出: [bold]{len(extracted_facilities)}件[/bold]")
        for ef in extracted_facilities[:15]:
            tgt = ef['postback_target'] or "(no link)"
            arg = ef['postback_arg'] or ""
            console.print(f"  [{ef['name'][:30]:<30s}] target={tgt} arg={arg}")
        if len(extracted_facilities) > 15:
            console.print(f"  [dim]... 他 {len(extracted_facilities) - 15}件[/dim]")

        # =================================================================
        # Step 7: カテゴリ別に全施設を巡回 (ssCategory=10, 20, 30, 40, 50)
        # =================================================================
        console.print("\n[cyan]Step 7: カテゴリ別に全施設を巡回[/cyan]")
        all_facilities_by_category: dict[str, list[dict]] = {}
        for cat_id in ["10", "20", "30", "40", "50"]:
            console.print(f"\n  [yellow]ssCategory={cat_id} をクリック[/yellow]")
            try:
                page.evaluate(f"() => __doPostBack('ssCategory', '{cat_id}')")
                page.wait_for_load_state("networkidle", timeout=20000)
                page.wait_for_timeout(1500)
                snapshot(page, f"04_category_{cat_id}")

                # 解析
                html_cat = page.content()
                soup_cat = BeautifulSoup(html_cat, "lxml")
                tables_cat = soup_cat.find_all("table")

                cat_facilities = []
                if tables_cat:
                    tbl_cat = tables_cat[0]
                    rows_cat = tbl_cat.find_all("tr")
                    for row in rows_cat[1:]:
                        cells = row.find_all(["td", "th"])
                        if len(cells) < 2:
                            continue
                        name = cells[1].get_text(strip=True) if len(cells) >= 2 else ""
                        if not name or name == "施設名":
                            continue

                        onclick_target = None
                        onclick_arg = None
                        for elem in row.find_all(["a", "input"]):
                            oc = elem.get("onclick", "") or elem.get("href", "")
                            m = postback_pattern.search(oc)
                            if m:
                                onclick_target = m.group(1)
                                onclick_arg = m.group(2)
                                break

                        cat_facilities.append({
                            "name": name,
                            "postback_target": onclick_target,
                            "postback_arg": onclick_arg,
                            "category_id": cat_id,
                        })

                all_facilities_by_category[cat_id] = cat_facilities
                console.print(f"    → {len(cat_facilities)}件取得")
            except Exception as e:
                console.print(f"    [red]→ 失敗: {e}[/red]")
                all_facilities_by_category[cat_id] = []

        # サマリー
        console.print(f"\n[bold]カテゴリ別件数:[/bold]")
        total = 0
        for cat_id, facs in all_facilities_by_category.items():
            console.print(f"  ssCategory={cat_id}: {len(facs)}件")
            total += len(facs)
        console.print(f"  [bold]合計: {total}件[/bold]")

        # 重複除去 (同じ施設名)
        seen = set()
        unique_facilities = []
        for cat_id, facs in all_facilities_by_category.items():
            for f in facs:
                if f["name"] not in seen:
                    seen.add(f["name"])
                    unique_facilities.append(f)
        console.print(f"  [bold green]ユニーク施設: {len(unique_facilities)}件[/bold green]")

        # 結果整形
        facilities_found = unique_facilities

        # 結果保存
        json_path = OUTPUTS / "matsumoto_M2_facility_list.json"
        json_path.write_text(
            json.dumps({"url": page.url, "found_facilities": facilities_found}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        console.print(f"\n[green]✓ 保存: {json_path.relative_to(SCRIPT_DIR)}[/green]")

        context.close()
        browser.close()

    console.print(f"\n[bold]次のステップ:[/bold]")
    console.print(f"  - outputs/matsumoto_M2_screenshots/ の HTML/PNG を確認")
    console.print(f"  - 施設選択方法 (SELECT or リンク) を特定")
    console.print(f"  - Stage M3 を該当方式で実装")

    return 0


if __name__ == "__main__":
    sys.exit(main())
