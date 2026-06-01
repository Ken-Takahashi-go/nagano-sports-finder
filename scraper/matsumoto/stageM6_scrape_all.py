"""
Stage M6: 松本市 紐付け済み施設の空き状況を全件スクレイプ → DB投入

フロー (1施設あたり):
  1. webR top → 空き照会
  2. zenshisetsu (全施設) → filterAll で table 表示
  3. checkShisetsu[value=external_facility_id] の label をクリックして選択
  4. __doPostBack('next','') で「次へ進む」→ カレンダー画面
  5. HTML を M4 ロジックで解析 → M5 ロジックで日次集約
  6. availability_current に UPSERT + availability_snapshots に INSERT
  7. メニューに戻って次施設へ (fault-tolerant: 1施設失敗でも継続)

対象:
  facilities WHERE external_system='matsumoto_webR' AND external_facility_id IS NOT NULL

使い方:
  python matsumoto/stageM6_scrape_all.py --dry-run     # DB書き込みなし
  python matsumoto/stageM6_scrape_all.py               # 実投入
  python matsumoto/stageM6_scrape_all.py --limit 2     # 先頭2施設だけ
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.table import Table

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.parent
load_dotenv(SCRIPT_DIR / ".env")
console = Console()

# --------------------------------------------------------------------
# 設定
# --------------------------------------------------------------------
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
EXTERNAL_SYSTEM = "matsumoto_webR"
INTERVAL = 3.0  # 施設間の待機秒 (負荷配慮)
DEFAULT_OPEN = "09:00"
DEFAULT_CLOSE = "21:00"
SHOTS = SCRIPT_DIR / "outputs" / "matsumoto_M6_screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)


def _ascii_safe(s: str | None) -> str:
    if s is None:
        return ""
    return str(s).replace("﻿", "").strip().encode("ascii", errors="ignore").decode("ascii")


SUPABASE_URL = _ascii_safe(os.getenv("SUPABASE_URL"))
SUPABASE_KEY = _ascii_safe(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

VALUE_PATTERN = re.compile(r"^(\d{8})(\d{3})(\d{2})\s*(\d*)$")
STATUS_MAP = {
    "○": "available", "△": "partial", "×": "full",
    "－": "unavailable", "ー": "unavailable", "休館日": "closed",
}


# --------------------------------------------------------------------
# Supabase REST helpers
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
# パース (Stage M4 ロジック)
# --------------------------------------------------------------------
def parse_value(value: str) -> dict | None:
    m = VALUE_PATTERN.match(value.strip())
    if not m:
        return None
    ymd, time_band, room_part, flag = m.groups()
    return {
        "date": f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}",
        "time_band_id": time_band,
        "room_part_id": room_part,
        "flag": flag,
    }


def normalize_status(text: str) -> str:
    return STATUS_MAP.get((text or "").strip(), "unknown")


def parse_calendar_html(html: str) -> list[dict]:
    """カレンダー HTML → 部屋別スロット [{room_part_id, room_name, slots:[...]}]"""
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    if not tables:
        return []
    main_table = max(tables, key=lambda t: len(t.find_all("tr")))
    parsed_rooms: list[dict] = []
    for tr in main_table.find_all("tr"):
        room_name_cell = tr.find("td", class_="shisetsu")
        if not room_name_cell:
            continue
        room_name = room_name_cell.get_text(strip=True)
        slots = []
        for td in tr.find_all("td"):
            cb = td.find("input", attrs={"name": "checkdate"})
            if not cb:
                continue
            parsed = parse_value(cb.get("value", ""))
            if not parsed:
                continue
            label = td.find("label")
            raw = label.get_text(strip=True) if label else ""
            slots.append({
                "date": parsed["date"],
                "time_band_id": parsed["time_band_id"],
                "room_part_id": parsed["room_part_id"],
                "status": normalize_status(raw),
                "raw": raw,
            })
        if slots:
            parsed_rooms.append({
                "room_part_id": slots[0]["room_part_id"],
                "room_name": room_name,
                "slots": slots,
            })
    return parsed_rooms


# --------------------------------------------------------------------
# 集約 (Stage M5 ロジック)
# --------------------------------------------------------------------
def aggregate_daily(rooms: list[dict]) -> list[dict]:
    by_date: dict[str, dict[str, int]] = {}
    for r in rooms:
        for s in r["slots"]:
            d = s["date"]
            by_date.setdefault(d, {"available": 0, "partial": 0, "full": 0,
                                   "unavailable": 0, "closed": 0, "total": 0})
            by_date[d]["total"] += 1
            if s["status"] in by_date[d]:
                by_date[d][s["status"]] += 1
    results = []
    for d in sorted(by_date.keys()):
        c = by_date[d]
        total = c["total"]
        open_count = c["available"] + c["partial"]
        non_closed = total - c["closed"] - c["unavailable"]
        if c["closed"] + c["unavailable"] == total:
            status, avail = "休館", 0
        elif non_closed > 0 and c["full"] == non_closed:
            status, avail = "満", 0
        elif non_closed > 0 and c["available"] == non_closed:
            status, avail = "空き", open_count
        elif open_count > 0:
            status, avail = "一部空き", open_count
        else:
            status, avail = "不明", open_count
        results.append({
            "target_date": d, "status": status,
            "available_count": avail, "total_count": total,
        })
    return results


# --------------------------------------------------------------------
# Playwright: 1施設のカレンダー HTML を取得
# --------------------------------------------------------------------
def goto_zenshisetsu(page) -> None:
    """webR → 空き照会 → 全施設一覧 (filterAll)"""
    page.goto(f"{BASE_URL}/WebR/", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(1500)
    page.locator("text=空き照会").first.click()
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(1500)
    page.evaluate("() => __doPostBack('zenshisetsu', '')")
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(1500)


def fetch_facility_calendar(page, ext_id: str, name: str) -> str | None:
    """external_facility_id の施設を選択 → 次へ進む → カレンダー HTML 返却"""
    goto_zenshisetsu(page)

    # checkShisetsu[value=ext_id] の label をクリック
    cb_id = f"checkShisetsu{ext_id}"
    label = page.locator(f"label[for='{cb_id}']").first
    if not label.is_visible(timeout=4000):
        # フォールバック: 施設名でラベル検索
        label = page.locator(f"label:has-text('{name}')").first
        if not label.is_visible(timeout=3000):
            raise RuntimeError(f"checkbox label 未発見 (id={cb_id}, name={name})")
    label.click(force=True)
    page.wait_for_timeout(400)

    # 「次へ進む」 = __doPostBack('next','')
    page.evaluate("() => __doPostBack('next', '')")
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(1500)

    html = page.content()
    # カレンダー画面か検証 (checkdate が含まれるか)
    if "checkdate" not in html:
        # 念のためスクショ保存
        (SHOTS / f"FAIL_{ext_id}.html").write_text(html, encoding="utf-8")
        raise RuntimeError("カレンダー画面に未到達 (checkdate 無し)")
    return html


# --------------------------------------------------------------------
# main
# --------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    console.print("[bold green]Stage M6: 松本市 全件空き状況スクレイプ[/bold green]\n")
    if not SUPABASE_URL or not SUPABASE_KEY:
        console.print("[red]ERROR: SUPABASE 認証情報 未設定[/red]")
        return 1

    # 対象施設取得
    facilities = supa_get("facilities", {
        "external_system": f"eq.{EXTERNAL_SYSTEM}",
        "external_facility_id": "not.is.null",
        "select": "id,facility_code,facility_name,external_facility_id",
        "order": "external_facility_id",
    })
    if args.limit:
        facilities = facilities[:args.limit]
    console.print(f"[cyan]対象施設: {len(facilities)}件[/cyan]\n")

    now = datetime.now(timezone.utc).isoformat()
    results_summary = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, locale="ja-JP",
                                      viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.set_default_timeout(20000)

        for i, fac in enumerate(facilities, start=1):
            ext_id = fac["external_facility_id"]
            name = fac["facility_name"]
            code = fac["facility_code"]
            console.print(f"[bold][{i}/{len(facilities)}] {code} {name} (webR={ext_id})[/bold]")
            try:
                html = fetch_facility_calendar(page, ext_id, name)
                rooms = parse_calendar_html(html)
                daily = aggregate_daily(rooms)
                n_open = sum(1 for d in daily if d["status"] in ("空き", "一部空き"))
                console.print(f"  → 部屋{len(rooms)} / {len(daily)}日 (空き含む {n_open}日)")

                if not args.dry_run and daily:
                    payloads_current, payloads_snapshot = [], []
                    for d in daily:
                        common = {
                            "facility_id": fac["id"],
                            "target_date": d["target_date"],
                            "start_time": DEFAULT_OPEN, "end_time": DEFAULT_CLOSE,
                            "availability_status": d["status"],
                            "available_court_count": d["available_count"],
                            "total_court_count": d["total_count"],
                            "source": "scrape",
                        }
                        payloads_current.append({**common, "last_checked_at": now})
                        payloads_snapshot.append({**common, "snapshot_at": now})
                    supa_upsert("availability_current", payloads_current,
                                on_conflict="facility_id,target_date,start_time,end_time")
                    supa_insert("availability_snapshots", payloads_snapshot)
                    console.print(f"  [green]→ DB: {len(payloads_current)}行 投入[/green]")

                results_summary.append((code, name, len(daily), n_open, "OK"))
            except Exception as e:
                console.print(f"  [red]→ 失敗: {e}[/red]")
                results_summary.append((code, name, 0, 0, f"NG: {str(e)[:40]}"))

            if i < len(facilities):
                time.sleep(INTERVAL)

        browser.close()

    # サマリ
    console.print("\n[bold]=== 実行サマリ ===[/bold]")
    tbl = Table()
    tbl.add_column("code"); tbl.add_column("施設名")
    tbl.add_column("日数", justify="right"); tbl.add_column("空き日", justify="right")
    tbl.add_column("結果")
    for code, name, days, n_open, status in results_summary:
        style = "green" if status == "OK" else "red"
        tbl.add_row(code, name[:20], str(days), str(n_open), f"[{style}]{status}[/{style}]")
    console.print(tbl)

    n_ok = sum(1 for r in results_summary if r[4] == "OK")
    console.print(f"\n[bold]成功 {n_ok}/{len(results_summary)}[/bold]")
    return 0 if n_ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
