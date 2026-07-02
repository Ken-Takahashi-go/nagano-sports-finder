"""
P-Kashikan 共通コア (Playwright)

P-Kashikan(PHP系・VIEWSTATEなし)を Playwright で攻略する共通ロジック。
webR(webr_core)と取得モデルが異なる:
  - 目的検索(競技)1回で「該当全施設 × 本日の時間別(9-21時)空き状況」が取れる
  - 施設は施設名(h3)ベース、setNaviDate(YYYYMMDD)で日送り
  - 状態記号: ● = 空き, × = 満/不可, 空白 = 対象外時間

自治体差し替え: base_url / external_system / 競技コード(市で共通の見込みだが要確認)

使い方(各市ラッパから):
  from pkashikan_core import PKCityConfig, run_scrape, build_arg_parser
"""
from __future__ import annotations

import io
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.table import Table

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
load_dotenv(SCRIPT_DIR / ".env")
console = Console()

SCRAPER_NAME = os.getenv("SCRAPER_NAME", "NaganoSportsFinder")
SCRAPER_VERSION = os.getenv("SCRAPER_VERSION", "0.1.0")
SCRAPER_CONTACT = os.getenv("SCRAPER_CONTACT", "contact@example.com")
USER_AGENT = (
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    f"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 "
    f"{SCRAPER_NAME}/{SCRAPER_VERSION} (+{SCRAPER_CONTACT})"
)
INTERVAL = 2.5
DEFAULT_OPEN = "09:00"
DEFAULT_CLOSE = "21:00"

# P-Kashikan 状態記号 → 内部ステータス
STATUS_MARK = {
    "●": "available", "○": "available", "◎": "available",
    "△": "partial", "▲": "partial",
    "×": "full", "✕": "full", "－": "unavailable", "-": "unavailable",
}

# 競技 → (Type, MokutekiCode)  ※P-Kashikan標準コード(須坂で確認、市差は probe で要検証)
SPORT_SEARCH: dict[str, tuple[str, str]] = {
    # 屋内スポーツ (Type=6)
    "basketball": ("6", "022"),
    "volleyball": ("6", "024"),
    "badminton": ("6", "026"),
    "futsal": ("6", "028"),
    "tennis_indoor": ("6", "045"),
    # 屋外スポーツ (Type=7)  ※須坂で確認(市差は要検証)
    "soccer": ("7", "033"),
    "tennis_hard": ("7", "035"),
    "tennis_soft": ("7", "036"),
}


def _ascii_safe(s: str | None) -> str:
    if s is None:
        return ""
    return str(s).replace("﻿", "").strip().encode("ascii", errors="ignore").decode("ascii")


SUPABASE_URL = _ascii_safe(os.getenv("SUPABASE_URL"))
SUPABASE_KEY = _ascii_safe(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


@dataclass
class PKCityConfig:
    name: str
    external_system: str          # 例 pkashikan_suzaka
    base_url: str                 # 例 https://k3.p-kashikan.jp/suzaka-city
    sports: list[str] = field(default_factory=lambda: ["basketball", "tennis", "futsal"])
    open_time: str = DEFAULT_OPEN
    close_time: str = DEFAULT_CLOSE
    shots_dir: Path = field(default=None)

    def __post_init__(self):
        if self.shots_dir is None:
            self.shots_dir = SCRIPT_DIR / "outputs" / f"{self.external_system}_screenshots"
        self.shots_dir.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------
# Supabase REST
# --------------------------------------------------------------------
def _headers(extra: dict | None = None) -> dict:
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    if extra:
        h.update(extra)
    return h


def supa_get(path: str, params: dict | None = None) -> list[dict]:
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{path}"
    r = httpx.get(url, params=params, headers=_headers(), timeout=30.0)
    r.raise_for_status()
    return r.json()


def supa_upsert(path: str, rows: list[dict], on_conflict: str) -> None:
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{path}"
    r = httpx.post(url, params={"on_conflict": on_conflict},
                   headers=_headers({"Content-Type": "application/json",
                                     "Prefer": "resolution=merge-duplicates,return=minimal"}),
                   json=rows, timeout=60.0)
    if r.status_code >= 400:
        raise RuntimeError(f"upsert {path}: {r.status_code} {r.text[:300]}")


def supa_insert(path: str, rows: list[dict]) -> None:
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{path}"
    r = httpx.post(url, headers=_headers({"Content-Type": "application/json",
                                          "Prefer": "return=minimal"}),
                   json=rows, timeout=60.0)
    if r.status_code >= 400:
        raise RuntimeError(f"insert {path}: {r.status_code} {r.text[:300]}")


# --------------------------------------------------------------------
# Playwright: 目的検索 → 指定日のカレンダーHTML
# --------------------------------------------------------------------
def goto_search(page, base_url: str) -> None:
    """トップ → 目的で検索画面(srch_mkt)"""
    page.goto(f"{base_url}/", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(1200)
    # 「空き状況の確認」→「目的で検索」へ
    try:
        page.evaluate("() => { if (typeof gotoPage === 'function') gotoPage('srch_mkt'); }")
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(1200)
    except Exception:
        pass


def fetch_sport_day(page, base_url: str, type_v: str, mokuteki: str, yyyymmdd: str) -> str:
    """競技(Type+Mokuteki)を選択し、指定日のカレンダーHTMLを取得"""
    goto_search(page, base_url)
    # Type 選択 (make_mokuteki_menu)
    page.evaluate(f"() => {{ const r=document.querySelector(\"input[name='Type'][value='{type_v}']\"); "
                  f"if(r){{r.checked=true; if(typeof make_mokuteki_menu==='function') make_mokuteki_menu({type_v});}} }}")
    page.wait_for_timeout(1200)
    # MokutekiCode 選択 (makeShisetsuList)
    page.evaluate(f"() => {{ const r=document.querySelector(\"input[name='MokutekiCode'][value='{mokuteki}']\"); "
                  f"if(r){{r.checked=true; if(typeof makeShisetsuList==='function') makeShisetsuList();}} }}")
    page.wait_for_timeout(1500)
    # 検索
    page.locator("button[name='searchBtn'], input[name='searchBtn']").first.click()
    page.wait_for_load_state("networkidle", timeout=25000)
    page.wait_for_timeout(1800)
    # 指定日へ移動
    page.evaluate(f"() => {{ if (typeof setNaviDate === 'function') setNaviDate('{yyyymmdd}'); }}")
    page.wait_for_load_state("networkidle", timeout=20000)
    page.wait_for_timeout(1500)
    # content取得をリトライ (page navigating race対策)
    html = ""
    for _ in range(3):
        try:
            page.wait_for_load_state("domcontentloaded", timeout=8000)
            html = page.content()
            if html:
                break
        except Exception:
            page.wait_for_timeout(1500)
    return html


# --------------------------------------------------------------------
# パース: koma-area(施設) × koma-table(部屋×時間 ●×)
# --------------------------------------------------------------------
def parse_calendar(html: str) -> dict[str, dict]:
    """
    return { 施設名: { "rooms": [ {room, marks:[状態...]} ], } }
    各 koma-area = 1施設(h3), 中の koma-table 群 = 部屋ごとの時間セル
    """
    soup = BeautifulSoup(html, "lxml")
    result: dict[str, dict] = {}
    for area in soup.select("div.koma-area"):
        h3 = area.find("h3")
        if not h3:
            continue
        fac_name = h3.get_text(strip=True)
        rooms = []
        for tbl in area.select("table.koma-table"):
            name_cell = tbl.find("td", class_="name")
            if not name_cell:
                continue  # ヘッダーテーブル(施設/時間)はスキップ
            room_name = name_cell.get_text(strip=True)
            marks = []
            for td in name_cell.find_next_siblings("td"):
                t = td.get_text(strip=True)
                if t:
                    marks.append(STATUS_MARK.get(t, "other"))
            rooms.append({"room": room_name, "marks": marks})
        if rooms:
            result[fac_name] = {"rooms": rooms}
    return result


def aggregate_facility_day(facility_data: dict) -> tuple[str, int, int]:
    """1施設・1日の部屋×時間 → (status, available_rooms, total_rooms)"""
    rooms = facility_data["rooms"]
    total = len(rooms)
    open_rooms = 0
    for r in rooms:
        # その部屋に1コマでも available があれば「空きあり部屋」
        if any(m == "available" for m in r["marks"]):
            open_rooms += 1
    if total == 0:
        return "不明", 0, 0
    if open_rooms == total:
        return "空き", open_rooms, total
    if open_rooms == 0:
        return "満", 0, total
    return "一部空き", open_rooms, total


# --------------------------------------------------------------------
# メイン
# --------------------------------------------------------------------
def build_arg_parser():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14, help="取得日数")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sports", default=None, help="カンマ区切り競技 (省略時はcfg.sports)")
    return ap


def run_scrape(cfg: PKCityConfig, args) -> int:
    console.print(f"[bold green]P-Kashikan スクレイプ: {cfg.name} ({cfg.external_system})[/bold green]\n")
    if not SUPABASE_URL or not SUPABASE_KEY:
        console.print("[red]ERROR: SUPABASE 認証情報 未設定[/red]")
        return 1

    # DB の対象施設 (external_system一致, 施設名→facility_id)
    facilities = supa_get("facilities", {
        "external_system": f"eq.{cfg.external_system}",
        "select": "id,facility_code,facility_name,external_facility_id",
    })
    name_to_fac = {f["facility_name"]: f for f in facilities}
    console.print(f"[cyan]DB登録施設: {len(facilities)}件[/cyan]")

    sports = (args.sports.split(",") if args.sports else cfg.sports)
    today = datetime.now()
    dates = [(today + timedelta(days=i)).strftime("%Y%m%d") for i in range(args.days)]
    now_iso = datetime.now(timezone.utc).isoformat()

    # 施設×日 の集約結果 { (fac_name, date): (status, avail, total) }
    collected: dict[tuple, tuple] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, locale="ja-JP",
                                      viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.set_default_timeout(20000)

        for sport in sports:
            if sport not in SPORT_SEARCH:
                console.print(f"  [yellow]未知の競技 {sport} skip[/yellow]")
                continue
            type_v, mokuteki = SPORT_SEARCH[sport]
            console.print(f"\n[cyan]競技={sport} (Type={type_v}, Mokuteki={mokuteki})[/cyan]")
            for d in dates:
                try:
                    html = fetch_sport_day(page, cfg.base_url, type_v, mokuteki, d)
                    parsed = parse_calendar(html)
                    iso_date = f"{d[:4]}-{d[4:6]}-{d[6:]}"
                    n_fac = 0
                    for fac_name, fdata in parsed.items():
                        status, avail, total = aggregate_facility_day(fdata)
                        key = (fac_name, iso_date)
                        # 競技をまたぐ同一施設は「より空き」を優先(maxで上書きはせず、初回優先+空き優先)
                        if key not in collected or avail > collected[key][1]:
                            collected[key] = (status, avail, total)
                        n_fac += 1
                    console.print(f"  {iso_date}: {n_fac}施設")
                except Exception as e:
                    console.print(f"  [red]{d} 失敗: {str(e)[:60]}[/red]")
                time.sleep(INTERVAL)

        browser.close()

    # DB投入
    console.print(f"\n[cyan]集約: {len(collected)} (施設×日)[/cyan]")
    matched, unmatched = 0, set()
    payloads_current, payloads_snapshot = [], []
    for (fac_name, iso_date), (status, avail, total) in collected.items():
        fac = name_to_fac.get(fac_name)
        if not fac:
            unmatched.add(fac_name)
            continue
        matched += 1
        common = {
            "facility_id": fac["id"], "court_name": "", "target_date": iso_date,
            "start_time": cfg.open_time, "end_time": cfg.close_time,
            "availability_status": status,
            "available_court_count": avail, "total_court_count": total,
            "source": "scrape",
        }
        payloads_current.append({**common, "last_checked_at": now_iso})
        payloads_snapshot.append({**common, "snapshot_at": now_iso})

    console.print(f"  DB照合: {matched}行 / 未照合施設名: {len(unmatched)}")
    if unmatched:
        console.print(f"  [yellow]未照合(DB未登録): {sorted(list(unmatched))[:10]}[/yellow]")

    if not args.dry_run and payloads_current:
        # 日付ごとにまとめてupsert (バッチ)
        supa_upsert("availability_current", payloads_current,
                    on_conflict="facility_id,court_name,target_date,start_time,end_time")
        supa_insert("availability_snapshots", payloads_snapshot)
        console.print(f"  [green]→ DB投入: current {len(payloads_current)} / snapshot {len(payloads_snapshot)}[/green]")
    elif args.dry_run:
        console.print("  [yellow][dry-run] DB投入スキップ[/yellow]")

    console.print(f"\n[bold]完了: 施設照合 {matched}件投入[/bold]")
    return 0 if matched > 0 else 1
