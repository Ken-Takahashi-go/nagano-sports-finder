"""
webR 共通コア (富士通系 公共施設予約システム webR版)

松本市 stageM6 のロジックを一般化し、自治体ごとに以下を差し替えて使う:
  - base_url        : webR のホスト (例 https://www.pf489.com/shiojiri)
  - external_system : DB の external_system 値 (例 shiojiri_webR)
  - type_map        : facility_code prefix → webR 施設種類番号(radioShisetsuMiddle)
                      ※施設種類番号は自治体ごとにカスタム (松本01=体育館, 塩尻00=アリーナ 等)

webR 共通仕様 (松本・塩尻で実証):
  空き照会 → 施設種類タブ → radioShisetsuMiddle → searchShisetsu()
  → 検索結果 checkShisetsu → __doPostBack('next') → カレンダー
  カレンダー value = YYYYMMDD + TTT(時間帯) + RR(部屋枝番) + 空白 + flag

使い方 (各市の薄いラッパから):
  from webr_core import CityConfig, run_scrape, build_arg_parser
  cfg = CityConfig(name="塩尻市", external_system="shiojiri_webR",
                   base_url="https://www.pf489.com/shiojiri",
                   type_map={"SIO-GYM":"00","SIO-TEN":"13","SIO-SOC":"10"})
  sys.exit(run_scrape(cfg, build_arg_parser().parse_args()))
"""
from __future__ import annotations

import io
import os
import re
import sys
import time
from dataclasses import dataclass, field
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

SCRIPT_DIR = Path(__file__).parent
load_dotenv(SCRIPT_DIR / ".env")
console = Console()

SCRAPER_NAME = os.getenv("SCRAPER_NAME", "NaganoSportsFinder")
SCRAPER_VERSION = os.getenv("SCRAPER_VERSION", "0.1.0")
SCRAPER_CONTACT = os.getenv("SCRAPER_CONTACT", "contact@example.com")
USER_AGENT = (
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    f"AppleWebKit/537.36 (KHTML, like Gecko) "
    f"Chrome/120.0.0.0 Safari/537.36 "
    f"{SCRAPER_NAME}/{SCRAPER_VERSION} (+{SCRAPER_CONTACT})"
)
INTERVAL = 3.0
DEFAULT_OPEN = "09:00"
DEFAULT_CLOSE = "21:00"

VALUE_PATTERN = re.compile(r"^(\d{8})(\d{3})(\d{2})\s*(\d*)$")
STATUS_MAP = {
    "○": "available", "△": "partial", "×": "full",
    "－": "unavailable", "ー": "unavailable", "休館日": "closed",
}


def _ascii_safe(s: str | None) -> str:
    if s is None:
        return ""
    return str(s).replace("﻿", "").strip().encode("ascii", errors="ignore").decode("ascii")


SUPABASE_URL = _ascii_safe(os.getenv("SUPABASE_URL"))
SUPABASE_KEY = _ascii_safe(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


@dataclass
class CityConfig:
    name: str
    external_system: str
    base_url: str
    type_map: dict[str, str]  # facility_code prefix → 施設種類番号
    open_time: str = DEFAULT_OPEN
    close_time: str = DEFAULT_CLOSE
    shots_dir: Path = field(default=None)

    def __post_init__(self):
        if self.shots_dir is None:
            self.shots_dir = SCRIPT_DIR / "outputs" / f"{self.external_system}_screenshots"
        self.shots_dir.mkdir(parents=True, exist_ok=True)

    def type_value_for(self, code: str) -> str | None:
        for prefix, tv in self.type_map.items():
            if code.startswith(prefix):
                return tv
        return None


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
# パース & 集約
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
        results.append({"target_date": d, "status": status,
                        "available_count": avail, "total_count": total})
    return results


# --------------------------------------------------------------------
# Playwright
# --------------------------------------------------------------------
def goto_kuki(page, base_url: str) -> None:
    page.goto(f"{base_url}/WebR/", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(1500)
    page.locator("text=空き照会").first.click()
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(1500)


def fetch_facility_calendar(page, cfg: CityConfig, ext_id: str, name: str, type_value: str) -> str:
    goto_kuki(page, cfg.base_url)
    # 施設種類タブ
    try:
        tab = page.locator("a:has-text('施設種類から探す')").first
        if tab.is_visible(timeout=3000):
            tab.click()
            page.wait_for_timeout(600)
    except Exception:
        pass
    # 種別 radio
    page.locator(f"label[for='radioShisetsuMiddle{type_value}']").first.click(force=True)
    page.wait_for_timeout(400)
    # 検索
    try:
        page.evaluate("() => searchShisetsu()")
    except Exception:
        page.locator("#btnSearchViaShisetsu").first.click(force=True)
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(1500)
    # 対象 checkbox を待って選択
    cb_id = f"checkShisetsu{ext_id}"
    try:
        page.wait_for_selector(f"#{cb_id}", timeout=15000, state="attached")
    except Exception:
        page.wait_for_timeout(2500)
        if page.locator(f"#{cb_id}").count() == 0 and page.locator(f"label:has-text('{name}')").count() == 0:
            (cfg.shots_dir / f"FAIL_select_{ext_id}.html").write_text(page.content(), encoding="utf-8")
            raise RuntimeError(f"checkbox 未出現 (id={cb_id}, name={name})")
    label = page.locator(f"label[for='{cb_id}']").first
    if label.count() == 0:
        label = page.locator(f"label:has-text('{name}')").first
    label.click(force=True)
    page.wait_for_timeout(400)
    # 次へ進む
    page.evaluate("() => __doPostBack('next', '')")
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(1500)
    # content取得をリトライ (ナビゲーション中の "page is navigating" レース対策)
    html = ""
    for _ in range(3):
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            html = page.content()
            if html:
                break
        except Exception:
            page.wait_for_timeout(2000)
    if "checkdate" not in html:
        (cfg.shots_dir / f"FAIL_calendar_{ext_id}.html").write_text(html or "", encoding="utf-8")
        raise RuntimeError("カレンダー画面に未到達 (checkdate 無し)")
    return html


# --------------------------------------------------------------------
# メイン
# --------------------------------------------------------------------
def build_arg_parser():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--code", default=None, help="カンマ区切り facility_code でフィルタ")
    return ap


def run_scrape(cfg: CityConfig, args) -> int:
    console.print(f"[bold green]webR スクレイプ: {cfg.name} ({cfg.external_system})[/bold green]\n")
    if not SUPABASE_URL or not SUPABASE_KEY:
        console.print("[red]ERROR: SUPABASE 認証情報 未設定[/red]")
        return 1

    facilities = supa_get("facilities", {
        "external_system": f"eq.{cfg.external_system}",
        "external_facility_id": "not.is.null",
        "select": "id,facility_code,facility_name,external_facility_id",
        "order": "external_facility_id",
    })
    if args.code:
        wanted = set(c.strip() for c in args.code.split(","))
        facilities = [f for f in facilities if f["facility_code"] in wanted]
    if args.limit:
        facilities = facilities[:args.limit]
    console.print(f"[cyan]対象施設: {len(facilities)}件[/cyan]\n")

    now = datetime.now(timezone.utc).isoformat()
    summary = []

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
            type_value = cfg.type_value_for(code)
            console.print(f"[bold][{i}/{len(facilities)}] {code} {name} (webR={ext_id}, 種別={type_value})[/bold]")
            if not type_value:
                console.print(f"  [yellow]→ スキップ: 種別未定義 (code={code})[/yellow]")
                summary.append((code, name, 0, 0, "SKIP"))
                continue
            try:
                html = fetch_facility_calendar(page, cfg, ext_id, name, type_value)
                rooms = parse_calendar_html(html)
                daily = aggregate_daily(rooms)
                n_open = sum(1 for d in daily if d["status"] in ("空き", "一部空き"))
                console.print(f"  → 部屋{len(rooms)} / {len(daily)}日 (空き含む {n_open}日)")

                if not args.dry_run and daily:
                    pc, ps = [], []
                    for d in daily:
                        common = {
                            "facility_id": fac["id"], "target_date": d["target_date"],
                            "start_time": cfg.open_time, "end_time": cfg.close_time,
                            "availability_status": d["status"],
                            "available_court_count": d["available_count"],
                            "total_court_count": d["total_count"], "source": "scrape",
                        }
                        pc.append({**common, "last_checked_at": now})
                        ps.append({**common, "snapshot_at": now})
                    supa_upsert("availability_current", pc,
                                on_conflict="facility_id,target_date,start_time,end_time")
                    supa_insert("availability_snapshots", ps)
                    console.print(f"  [green]→ DB: {len(pc)}行 投入[/green]")
                summary.append((code, name, len(daily), n_open, "OK"))
            except Exception as e:
                console.print(f"  [red]→ 失敗: {e}[/red]")
                summary.append((code, name, 0, 0, f"NG: {str(e)[:40]}"))
            if i < len(facilities):
                time.sleep(INTERVAL)

        browser.close()

    # サマリ
    console.print("\n[bold]=== 実行サマリ ===[/bold]")
    tbl = Table()
    tbl.add_column("code"); tbl.add_column("施設名")
    tbl.add_column("日数", justify="right"); tbl.add_column("空き日", justify="right")
    tbl.add_column("結果")
    for code, name, days, n_open, status in summary:
        style = "green" if status == "OK" else "red"
        tbl.add_row(code, name[:20], str(days), str(n_open), f"[{style}]{status}[/{style}]")
    console.print(tbl)
    n_ok = sum(1 for r in summary if r[4] == "OK")
    console.print(f"\n[bold]成功 {n_ok}/{len(summary)}[/bold]")
    return 0 if n_ok > 0 else 1
