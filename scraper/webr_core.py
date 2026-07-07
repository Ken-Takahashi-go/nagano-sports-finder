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


def supa_delete(path: str, params: dict) -> None:
    """PostgREST DELETE (フィルタ必須 — 全件削除を防ぐため params が空なら拒否)"""
    if not params:
        raise ValueError("supa_delete: フィルタ無しの削除は禁止")
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{path}"
    r = httpx.request("DELETE", url, params=params,
                      headers=_headers({"Prefer": "return=minimal"}), timeout=60.0)
    if r.status_code >= 400:
        raise RuntimeError(f"delete {path}: {r.status_code} {r.text[:300]}")


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
# 時間帯別 (WgR_JikantaibetsuAkiJoukyou) パース & 集約
# --------------------------------------------------------------------
JP_DATE_RE = re.compile(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日")
TIME_RANGE_RE = re.compile(r"(\d{1,2}):(\d{2})\s*[～~〜\-－]\s*(\d{1,2}):(\d{2})")


def _hhmm(h: str, m: str) -> str:
    return f"{int(h):02d}:{int(m):02d}:00"


def parse_timeband_html(html: str) -> list[dict]:
    """
    時間帯別空き状況 HTML → [{date, bands:[{start,end,statuses:[...]}]}]
    table.calendar が1つ=1日。thead th[0]=日付, th[1]=定員, th[2..]=時間帯。
    tbody tr=部屋, td[idx] は thead の列 idx に整列 (td[0]=部屋名, td[1]=定員, td[2..]=○△×)。
    """
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []
    for table in soup.select("table.calendar"):
        thead = table.find("thead")
        if not thead:
            continue
        ths = thead.find_all("th")
        if not ths:
            continue
        dm = JP_DATE_RE.search(ths[0].get_text(" ", strip=True))
        if not dm:
            continue
        date = f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}"
        # 時間帯の列インデックスを特定
        band_cols: list[tuple[int, str, str]] = []
        for idx, th in enumerate(ths):
            tm = TIME_RANGE_RE.search(th.get_text(" ", strip=True))
            if tm:
                band_cols.append((idx, _hhmm(tm.group(1), tm.group(2)),
                                  _hhmm(tm.group(3), tm.group(4))))
        if not band_cols:
            continue
        col_status: dict[int, list[str]] = {c[0]: [] for c in band_cols}
        for tr in table.select("tbody tr"):
            tds = tr.find_all("td")
            for idx in col_status:
                if idx < len(tds):
                    label = tds[idx].find("label")
                    raw = label.get_text(strip=True) if label else tds[idx].get_text(strip=True)
                    col_status[idx].append(normalize_status(raw))
        bands = [{"start": s, "end": e, "statuses": col_status[idx]}
                 for (idx, s, e) in band_cols]
        results.append({"date": date, "bands": bands})
    return results


def aggregate_timeband(parsed: list[dict]) -> list[dict]:
    """
    時間帯別パース結果 → DB行 [{target_date, start_time, end_time, status,
    available_count, total_count}]。各 (日付×時間帯) で部屋を横断集約。
    """
    rows: list[dict] = []
    for day in parsed:
        for b in day["bands"]:
            st = b["statuses"]
            avail = st.count("available")
            partial = st.count("partial")
            full = st.count("full")
            bookable = avail + partial + full  # 予約可能ユニット数 (－/unknown 除外)
            if bookable == 0:
                status, ac, tc = "休館", 0, len(st)
            elif full == bookable:
                status, ac, tc = "満", 0, bookable
            elif avail == bookable:
                status, ac, tc = "空き", avail, bookable
            elif (avail + partial) > 0:
                status, ac, tc = "一部空き", avail, bookable
            else:
                status, ac, tc = "不明", avail, bookable
            rows.append({"target_date": day["date"], "start_time": b["start"],
                         "end_time": b["end"], "status": status,
                         "available_count": ac, "total_count": tc})
    return rows


# --------------------------------------------------------------------
# コート(部屋)別 パース  ※Phase1: 1施設内の設備ごとに分離
# --------------------------------------------------------------------
COURT_STATUS_TO_AVAIL = {
    "available": ("空き", 1), "partial": ("一部空き", 1),
    "full": ("満", 0), "unavailable": ("休館", 0), "closed": ("休館", 0),
    "unknown": ("不明", 0),
}


def parse_timeband_with_rooms(html: str) -> list[dict]:
    """
    時間帯別HTML → [{court, date, start, end, status}]
    court = tbody各行の td.shisetsu(部屋/コート名)。1施設に複数コートがある場合、
    コートごとに1セル=1行で返す(全面/半面東/多目的広場 等を区別)。
    """
    soup = BeautifulSoup(html, "lxml")
    out: list[dict] = []
    for table in soup.select("table.calendar"):
        thead = table.find("thead")
        if not thead:
            continue
        ths = thead.find_all("th")
        if not ths:
            continue
        dm = JP_DATE_RE.search(ths[0].get_text(" ", strip=True))
        if not dm:
            continue
        date = f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}"
        band_cols: list[tuple[int, str, str]] = []
        for idx, th in enumerate(ths):
            tm = TIME_RANGE_RE.search(th.get_text(" ", strip=True))
            if tm:
                band_cols.append((idx, _hhmm(tm.group(1), tm.group(2)),
                                  _hhmm(tm.group(3), tm.group(4))))
        if not band_cols:
            continue
        for tr in table.select("tbody tr"):
            tds = tr.find_all("td")
            if not tds:
                continue
            court_cell = tr.find("td", class_="shisetsu")
            court = court_cell.get_text(strip=True) if court_cell else ""
            if not court:
                continue
            for (idx, s, e) in band_cols:
                if idx < len(tds):
                    label = tds[idx].find("label")
                    raw = label.get_text(strip=True) if label else tds[idx].get_text(strip=True)
                    out.append({"court": court, "date": date, "start": s, "end": e,
                                "status": normalize_status(raw)})
    return out


def aggregate_rooms(cells: dict) -> list[dict]:
    """
    cells: dict[(court,date,start,end)] = status(normalized)
    → DB行 [{court_name, target_date, start_time, end_time, status, available_count, total_count}]
    コートは原子単位なので total=1, available=1/0。
    """
    rows = []
    for (court, date, start, end), st in cells.items():
        status, avail = COURT_STATUS_TO_AVAIL.get(st, ("不明", 0))
        rows.append({
            "court_name": court, "target_date": date,
            "start_time": start, "end_time": end,
            "status": status, "available_count": avail, "total_count": 1,
        })
    return rows


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


def fetch_timeband_html(page, cfg: CityConfig, ext_id: str, name: str, type_value: str) -> str:
    """
    施設別空き状況(カレンダー)に到達 → 全日付(各日1つ)を一括選択 → 次へ進む
    → 時間帯別空き状況(WgR_JikantaibetsuAkiJoukyou) HTML を返す。
    1施設=1遷移で全日分(通常14日)取得できる。
    """
    fetch_facility_calendar(page, cfg, ext_id, name, type_value)  # page をカレンダーに残す
    # checkdate を日付ごとに1つ収集 (value 先頭8桁=日付)
    cds = page.evaluate("""
        () => Array.from(document.querySelectorAll("input[name='checkdate']"))
            .map(c => ({ id: c.id, value: c.value }))
    """)
    by_date: dict[str, str] = {}
    for c in cds:
        by_date.setdefault(c["value"][:8], c["id"])
    if not by_date:
        raise RuntimeError("checkdate が見つからない (日付選択不可)")
    for cid in by_date.values():
        try:
            page.locator(f"#{cid}").check(force=True)
        except Exception:
            page.locator(f"label[for='{cid}']").first.click(force=True)
    page.wait_for_timeout(500)
    # 次へ進む → 時間帯別
    page.evaluate("() => __doPostBack('next', '')")
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(1500)
    html = ""
    for _ in range(3):
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            html = page.content()
            if html:
                break
        except Exception:
            page.wait_for_timeout(2000)
    if "JikantaibetsuAkiJoukyou" not in html and "時間帯別" not in html:
        (cfg.shots_dir / f"FAIL_timeband_{ext_id}.html").write_text(html or "", encoding="utf-8")
        raise RuntimeError("時間帯別画面に未到達")
    return html


def _collect_checkdates(page) -> list[dict]:
    return page.evaluate("""
        () => Array.from(document.querySelectorAll("input[name='checkdate']"))
            .map(c => ({ id: c.id, value: c.value }))
    """)


def _on_calendar(page) -> bool:
    """施設別空き状況(カレンダー)画面にいるか"""
    try:
        return page.locator("input[name='checkdate']").count() > 0
    except Exception:
        return False


def _back_to_calendar(page) -> bool:
    """時間帯別画面から「前に戻る」でカレンダーへ高速復帰 (フル再到達 ~15s → ~3s)"""
    try:
        page.evaluate("() => __doPostBack('back', '')")
        page.wait_for_selector("input[name='checkdate']", timeout=10000, state="attached")
        page.wait_for_timeout(400)
        return True
    except Exception:
        return False


def _clear_checked(page) -> None:
    """チェック残りをクリア (前パスの選択が残ると次パスに混入するため)"""
    try:
        page.evaluate("""
            () => document.querySelectorAll("input[name='checkdate']:checked")
                .forEach(c => c.click())
        """)
        page.wait_for_timeout(200)
    except Exception:
        pass


def fetch_timeband_rooms(page, cfg: CityConfig, ext_id: str, name: str, type_value: str) -> dict:
    """
    1施設の全コート(部屋)の時間帯別空き状況を取得。

    webRは一度に約20枠しか選択できないため、checkdate を room_part(値の11-13桁目)
    ごとに分けて選択し、部屋ごとに calendar→時間帯別 を辿る。
    ハードニング:
      - 復帰は「前に戻る」優先 (フル再到達は最後の手段)
      - 遷移判定は URL (WgR_Jikantaibetsu) 12秒。来ない部屋(多目的広場等の
        別予約モデル)はデッドパスとして高速スキップし再試行しない
      - 取りこぼした部屋(遷移成功だが新規セル0)は1回だけリトライ
      - 取得コート数がカレンダーの部屋数に達したら early-exit (体育館は通常1パス)
    returns: dict[(court,date,start,end)] = status(normalized)  ※重複は後勝ちで統合
    """
    cells: dict = {}

    fetch_facility_calendar(page, cfg, ext_id, name, type_value)
    cds = _collect_checkdates(page)
    if not cds:
        raise RuntimeError("checkdate が見つからない")
    room_parts = sorted({c["value"][11:13] for c in cds})
    # カレンダー画面の部屋数 (early-exit 判定用)
    try:
        total_rooms = page.evaluate("() => document.querySelectorAll('td.shisetsu').length")
    except Exception:
        total_rooms = 0

    dead: set[str] = set()      # 時間帯別を返さない部屋 (再試行しない)
    pending = list(room_parts)

    for attempt in range(2):    # 取りこぼしリトライ最大1回
        failed: list[str] = []
        for rr in pending:
            # カレンダーへ復帰: back優先 → 失敗時のみフル再到達
            if not _on_calendar(page):
                if not _back_to_calendar(page):
                    fetch_facility_calendar(page, cfg, ext_id, name, type_value)
            _clear_checked(page)
            cds = _collect_checkdates(page)
            ids = [c["id"] for c in cds if c["value"][11:13] == rr][:20]
            if not ids:
                continue
            n_checked = 0
            for cid in ids:
                try:
                    page.locator(f"#{cid}").check(force=True)
                    n_checked += 1
                except Exception:
                    pass
            if n_checked == 0:
                failed.append(rr)
                continue
            page.wait_for_timeout(300)
            before = len(cells)
            page.evaluate("() => __doPostBack('next', '')")
            try:
                page.wait_for_url("**/WgR_Jikantaibetsu**", timeout=12000)
                page.wait_for_timeout(800)
            except Exception:
                # 時間帯別に来ない部屋 (多目的広場/会議室等の別予約モデル)
                console.print(f"    [dim]room {rr}: 時間帯別なし → skip[/dim]")
                dead.add(rr)
                _clear_checked(page)
                continue
            for cell in parse_timeband_with_rooms(page.content()):
                cells[(cell["court"], cell["date"], cell["start"], cell["end"])] = cell["status"]
            gained = len(cells) - before
            if gained == 0:
                failed.append(rr)
            # early-exit: 全部屋分のコートを取得済みなら残りパスは不要
            n_courts = len({k[0] for k in cells})
            if total_rooms and n_courts >= total_rooms:
                return cells
        pending = [rr for rr in failed if rr not in dead]
        if not pending:
            break
        console.print(f"    [yellow]取りこぼしリトライ: {pending}[/yellow]")
    return cells


# --------------------------------------------------------------------
# メイン
# --------------------------------------------------------------------
def build_arg_parser():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--code", default=None, help="カンマ区切り facility_code でフィルタ")
    ap.add_argument("--timeband", action="store_true",
                    help="時間帯別モードで取得 (公式と同じ時間帯バケット)")
    return ap


def run_scrape(cfg: CityConfig, args) -> int:
    if getattr(args, "timeband", False):
        return run_scrape_rooms(cfg, args)
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
                            "facility_id": fac["id"], "court_name": "",
                            "target_date": d["target_date"],
                            "start_time": cfg.open_time, "end_time": cfg.close_time,
                            "availability_status": d["status"],
                            "available_court_count": d["available_count"],
                            "total_court_count": d["total_count"], "source": "scrape",
                        }
                        pc.append({**common, "last_checked_at": now})
                        ps.append({**common, "snapshot_at": now})
                    supa_upsert("availability_current", pc,
                                on_conflict="facility_id,court_name,target_date,start_time,end_time")
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


def run_scrape_timeband(cfg: CityConfig, args) -> int:
    """時間帯別モード: 公式と同じ時間帯バケットで availability を投入。

    旧来の1日1枠(09:00-21:00)行は、対象日について削除してから時間帯別行を投入する
    (詳細マトリクスに旧バケット列が混在するのを防ぐ)。
    """
    console.print(f"[bold green]webR 時間帯別スクレイプ: {cfg.name} ({cfg.external_system})[/bold green]\n")
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
    legacy_start, legacy_end = cfg.open_time, cfg.close_time  # 09:00 / 21:00
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
                html = fetch_timeband_html(page, cfg, ext_id, name, type_value)
                parsed = parse_timeband_html(html)
                rows = aggregate_timeband(parsed)
                dates = sorted({r["target_date"] for r in rows})
                n_days = len(dates)
                n_bands = len(rows)
                n_open = sum(1 for r in rows if r["status"] in ("空き", "一部空き"))
                console.print(f"  → {n_days}日 × 時間帯 = {n_bands}行 (空き含む {n_open}枠)")

                if not args.dry_run and rows:
                    # 旧 1日1枠(09:00-21:00)行を全削除 (webRは時間帯別に統一)
                    supa_delete("availability_current", {
                        "facility_id": f"eq.{fac['id']}",
                        "start_time": f"eq.{legacy_start}",
                        "end_time": f"eq.{legacy_end}",
                    })
                    pc, ps = [], []
                    for r in rows:
                        common = {
                            "facility_id": fac["id"], "court_name": "",
                            "target_date": r["target_date"],
                            "start_time": r["start_time"], "end_time": r["end_time"],
                            "availability_status": r["status"],
                            "available_court_count": r["available_count"],
                            "total_court_count": r["total_count"], "source": "scrape",
                        }
                        pc.append({**common, "last_checked_at": now})
                        ps.append({**common, "snapshot_at": now})
                    supa_upsert("availability_current", pc,
                                on_conflict="facility_id,court_name,target_date,start_time,end_time")
                    supa_insert("availability_snapshots", ps)
                    console.print(f"  [green]→ DB: {len(pc)}行 投入 (旧1日枠は削除済)[/green]")
                summary.append((code, name, n_bands, n_open, "OK"))
            except Exception as e:
                console.print(f"  [red]→ 失敗: {e}[/red]")
                summary.append((code, name, 0, 0, f"NG: {str(e)[:40]}"))
            if i < len(facilities):
                time.sleep(INTERVAL)

        browser.close()

    console.print("\n[bold]=== 実行サマリ (時間帯別) ===[/bold]")
    tbl = Table()
    tbl.add_column("code"); tbl.add_column("施設名")
    tbl.add_column("行数", justify="right"); tbl.add_column("空き枠", justify="right")
    tbl.add_column("結果")
    for code, name, n_rows, n_open, status in summary:
        style = "green" if status == "OK" else "red"
        tbl.add_row(code, name[:20], str(n_rows), str(n_open), f"[{style}]{status}[/{style}]")
    console.print(tbl)
    n_ok = sum(1 for r in summary if r[4] == "OK")
    console.print(f"\n[bold]成功 {n_ok}/{len(summary)}[/bold]")
    return 0 if n_ok > 0 else 1


def run_scrape_rooms(cfg: CityConfig, args) -> int:
    """コート(部屋)別モード: 1施設内の設備ごと(人工芝全面/半面/多目的広場 等)に
    時間帯別空き状況を取得し、court_name 付きで投入する。

    --timeband フラグからディスパッチされる(従来の集約版 run_scrape_timeband を置換)。
    投入前に当該施設の既存 availability_current 行を全削除し、コート別行に置換する。
    """
    console.print(f"[bold green]webR コート別スクレイプ: {cfg.name} ({cfg.external_system})[/bold green]\n")
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
                cells = fetch_timeband_rooms(page, cfg, ext_id, name, type_value)
                rows = aggregate_rooms(cells)
                courts = sorted({r["court_name"] for r in rows})
                n_open = sum(1 for r in rows if r["status"] in ("空き", "一部空き"))
                console.print(f"  → {len(courts)}コート / {len(rows)}行 (空き枠 {n_open}) : {courts}")

                if not args.dry_run and rows:
                    # 既存行を全削除してコート別行に置換 (旧集約行 court_name='' も除去)
                    supa_delete("availability_current", {"facility_id": f"eq.{fac['id']}"})
                    pc, ps = [], []
                    for r in rows:
                        common = {
                            "facility_id": fac["id"], "court_name": r["court_name"],
                            "target_date": r["target_date"],
                            "start_time": r["start_time"], "end_time": r["end_time"],
                            "availability_status": r["status"],
                            "available_court_count": r["available_count"],
                            "total_court_count": r["total_count"], "source": "scrape",
                        }
                        pc.append({**common, "last_checked_at": now})
                        ps.append({**common, "snapshot_at": now})
                    supa_upsert("availability_current", pc,
                                on_conflict="facility_id,court_name,target_date,start_time,end_time")
                    supa_insert("availability_snapshots", ps)
                    console.print(f"  [green]→ DB: {len(pc)}行 投入 ({len(courts)}コート)[/green]")
                summary.append((code, name, len(rows), n_open, "OK"))
            except Exception as e:
                console.print(f"  [red]→ 失敗: {e}[/red]")
                summary.append((code, name, 0, 0, f"NG: {str(e)[:40]}"))
            if i < len(facilities):
                time.sleep(INTERVAL)

        browser.close()

    console.print("\n[bold]=== 実行サマリ (コート別) ===[/bold]")
    tbl = Table()
    tbl.add_column("code"); tbl.add_column("施設名")
    tbl.add_column("行数", justify="right"); tbl.add_column("空き枠", justify="right")
    tbl.add_column("結果")
    for code, name, n_rows, n_open, status in summary:
        style = "green" if status == "OK" else "red"
        tbl.add_row(code, name[:20], str(n_rows), str(n_open), f"[{style}]{status}[/{style}]")
    console.print(tbl)
    n_ok = sum(1 for r in summary if r[4] == "OK")
    console.print(f"\n[bold]成功 {n_ok}/{len(summary)}[/bold]")
    return 0 if n_ok > 0 else 1
