"""
NELCS 共通コア (Playwright)

NELCS系(nelcs.ne.jp)を Playwright で攻略。Phase 2コンプリート用(伊那・千曲・中野・箕輪)。
全段階 POST→HTML だが5段階のhidden連鎖が複雑なため Playwright のJS関数呼び出しで遷移。

フロー:
  RsvIndex → RsvSelCategory(cat) → RsvSelItemId(item) → RsvSelDestrict(district)
  → registDistrict() → RsvResult(施設一覧) → calendar_submit('0',施設コード,item)
  → RsvCalendar.php5 (月間カレンダー)

カレンダー状態(td[id^=calendar_] の class):
  normal/today/sun/sat (sel_dayリンクあり) = 空きあり
  full = 満 / padding = 対象外(前月末等)
→ MVPは日別の空き有無に集約 (時間帯詳細は sel_day 後だが当面は日別)

施設は施設名ベースで照合 (external_facility_id=施設コード)。

競技(itemcode):
  屋内(category=1): バスケ00002 バレー00001 バドミントン00003 フットサル00004
  屋外(category=2): 要probe確認 (サッカー/テニス)
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
    f"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 "
    f"{SCRAPER_NAME}/{SCRAPER_VERSION} (+{SCRAPER_CONTACT})"
)
INTERVAL = 2.0
DEFAULT_OPEN = "09:00"
DEFAULT_CLOSE = "21:00"

# 空き状態クラス: 予約可(リンクあり)
AVAILABLE_CLASSES = {"normal", "today", "sun", "sat"}
FULL_CLASSES = {"full"}
SKIP_CLASSES = {"padding"}

# 競技 → (category, itemcode) ※屋内のみ確定。屋外は probe で確認
SPORT_ITEM: dict[str, tuple[str, str]] = {
    # 屋内スポーツ (category=1)
    "basketball": ("1", "00002"),
    "volleyball": ("1", "00001"),
    "badminton": ("1", "00003"),
    "futsal": ("1", "00004"),
    # 屋外スポーツ (category=2) ※伊那で確認
    "tennis_hard": ("2", "00015"),
    "tennis_soft": ("2", "00016"),
    "soccer": ("2", "00017"),
}


def _ascii_safe(s: str | None) -> str:
    if s is None:
        return ""
    return str(s).replace("﻿", "").strip().encode("ascii", errors="ignore").decode("ascii")


SUPABASE_URL = _ascii_safe(os.getenv("SUPABASE_URL"))
SUPABASE_KEY = _ascii_safe(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


@dataclass
class NelcsCityConfig:
    name: str
    external_system: str       # nelcs_ina 等
    municipality_id: str       # 2020900 等(URL)
    sports: list[str] = field(default_factory=lambda: ["basketball", "futsal"])
    open_time: str = DEFAULT_OPEN
    close_time: str = DEFAULT_CLOSE
    shots_dir: Path = field(default=None)

    @property
    def base(self) -> str:
        return f"https://nelcs.ne.jp/Facilityrsv/Smartphone/{self.municipality_id}/user/rsvlot"

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
# Playwright フロー
# --------------------------------------------------------------------
def _eval_fn(page, js: str) -> None:
    page.evaluate(js)
    page.wait_for_load_state("networkidle", timeout=20000)
    page.wait_for_timeout(1200)


def reach_facility_list(page, cfg: NelcsCityConfig, category: str, itemcode: str) -> None:
    """RsvIndex → カテゴリ → 種目 → 全地区確定 → RsvResult(施設一覧)"""
    page.goto(f"{cfg.base}/RsvIndex.php5", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(1200)
    _eval_fn(page, f"() => {{ if(typeof RsvSelCategory==='function') RsvSelCategory('{category}'); }}")
    _eval_fn(page, f"() => {{ if(typeof RsvSelItemId==='function') RsvSelItemId('{itemcode}'); }}")
    # 地区: 全地区を選択して確定
    districts = page.evaluate("""
        () => Array.from(document.querySelectorAll("a[onclick*='RsvSelDestrict']"))
            .map(a => (a.getAttribute('onclick').match(/RsvSelDestrict\\('([^']+)'\\)/)||[])[1])
            .filter(Boolean)
    """)
    for d in districts:
        page.evaluate(f"() => {{ if(typeof RsvSelDestrict==='function') RsvSelDestrict('{d}'); }}")
        page.wait_for_timeout(300)
    _eval_fn(page, "() => { if(typeof registDistrict==='function') registDistrict(); }")


def get_facilities(page) -> list[dict]:
    """RsvResult から施設リスト [{code, name}] (calendar_submit の引数とラベル)"""
    return page.evaluate("""
        () => Array.from(document.querySelectorAll("a[onclick*='calendar_submit']")).map(a => {
            const m = (a.getAttribute('onclick')||'').match(/calendar_submit\\('([^']*)','([^']*)','([^']*)'\\)/);
            return { code: m ? m[2] : null, item: m ? m[3] : null, name: a.innerText.trim() };
        }).filter(x => x.code)
    """)


def fetch_calendar(page, cfg: NelcsCityConfig, code: str, itemcode: str) -> str:
    """calendar_submit → RsvCalendar(月間)。content取得リトライ"""
    page.evaluate(f"() => {{ if(typeof calendar_submit==='function') calendar_submit('0','{code}','{itemcode}'); }}")
    page.wait_for_load_state("networkidle", timeout=20000)
    page.wait_for_timeout(1500)
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
# パース: 月間カレンダー (class normal/full)
# --------------------------------------------------------------------
def parse_month_calendar(html: str) -> dict[str, str]:
    """RsvCalendar.php5 → {date: status}。status: '空き'/'満'"""
    soup = BeautifulSoup(html, "lxml")
    # 年月
    month_li = soup.find(id="month")
    ym = None
    if month_li:
        m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月", month_li.get_text())
        if m:
            ym = (int(m.group(1)), int(m.group(2)))
    result: dict[str, str] = {}
    for td in soup.select("td[id^='calendar_']"):
        classes = set(td.get("class") or [])
        if classes & SKIP_CLASSES:
            continue
        # 日付: sel_day('YYYY-MM-DD') があれば優先
        a = td.find("a")
        date_str = None
        if a and a.get("onclick"):
            dm = re.search(r"sel_day\('(\d{4}-\d{2}-\d{2})'\)", a["onclick"])
            if dm:
                date_str = dm.group(1)
        if not date_str and ym:
            mday = re.match(r"calendar_(\d+)", td.get("id", ""))
            daynum = td.get_text(strip=True)
            if daynum.isdigit():
                date_str = f"{ym[0]:04d}-{ym[1]:02d}-{int(daynum):02d}"
        if not date_str:
            continue
        if classes & FULL_CLASSES:
            result[date_str] = "満"
        elif classes & AVAILABLE_CLASSES or a:
            result[date_str] = "空き"
    return result


# --------------------------------------------------------------------
# 施設名クリーニング
# --------------------------------------------------------------------
def clean_name(name: str) -> str:
    """RsvResult の施設リンクは施設名+通称が連結 → 整理。
    例: 'サンビレッジサンビレッジ体育館' → 'サンビレッジ体育館'
        'サブアリーナ（伊那市民体育館）エレコムアリーナ（…）' → 'サブアリーナ（伊那市民体育館）'
    """
    name = (name or "").strip().replace("\n", "")
    # 連続重複語(先頭AAパターン)を除去
    for L in range(len(name) // 2, 1, -1):
        if name[:L] == name[L:2 * L]:
            name = name[L:]
            break
    # ネーミングライツ通称(2つ目の括弧以降)を落とす: '正式（施設）通称（…）' → '正式（施設）'
    m = re.match(r"^(.+?（[^）]*）)[^（]*（", name)
    if m:
        name = m.group(1)
    return name.strip()


# --------------------------------------------------------------------
# メイン
# --------------------------------------------------------------------
def build_arg_parser():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sports", default=None, help="カンマ区切り競技 (省略時cfg.sports)")
    return ap


def collect_all(page, cfg: NelcsCityConfig, sports: list[str]) -> dict[str, dict]:
    """全競技を巡回し {施設コード: {'name':.., 'cal':{date:status}}} を返す"""
    facilities: dict[str, dict] = {}
    for sport in sports:
        if sport not in SPORT_ITEM:
            console.print(f"  [yellow]未知の競技 {sport} skip[/yellow]")
            continue
        cat, item = SPORT_ITEM[sport]
        try:
            reach_facility_list(page, cfg, cat, item)
            facs = get_facilities(page)
            console.print(f"  [{sport}] 施設{len(facs)}件")
            for f in facs:
                code = f["code"]
                ok = False
                try:
                    # 各施設前に RsvResult を再取得 (go_backがPOST遷移で不安定なため確実策)
                    reach_facility_list(page, cfg, cat, item)
                    html = fetch_calendar(page, cfg, code, item)
                    cal = parse_month_calendar(html)
                    ok = True
                except Exception as e:
                    console.print(f"    [yellow]{code} カレンダー失敗: {str(e)[:40]}[/yellow]")
                if ok:
                    if code not in facilities:
                        facilities[code] = {"name": clean_name(f["name"]), "cal": {}}
                    for d, st in cal.items():
                        if d not in facilities[code]["cal"] or st == "空き":
                            facilities[code]["cal"][d] = st
                time.sleep(INTERVAL)
        except Exception as e:
            console.print(f"  [red]{sport} 失敗: {str(e)[:50]}[/red]")
    return facilities


def run_scrape(cfg: NelcsCityConfig, args) -> int:
    console.print(f"[bold green]NELCS スクレイプ: {cfg.name} ({cfg.external_system})[/bold green]\n")
    if not SUPABASE_URL or not SUPABASE_KEY:
        console.print("[red]ERROR: SUPABASE 認証情報 未設定[/red]")
        return 1

    db_facs = supa_get("facilities", {
        "external_system": f"eq.{cfg.external_system}",
        "select": "id,facility_code,facility_name,external_facility_id",
    })
    code_to_fac = {f["external_facility_id"]: f for f in db_facs}
    console.print(f"[cyan]DB登録施設: {len(db_facs)}件[/cyan]")

    sports = (args.sports.split(",") if args.sports else cfg.sports)
    now_iso = datetime.now(timezone.utc).isoformat()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(user_agent=USER_AGENT, locale="ja-JP",
                                   viewport={"width": 400, "height": 800}).new_page()
        page.set_default_timeout(20000)
        facilities = collect_all(page, cfg, sports)
        browser.close()

    console.print(f"\n[cyan]取得施設: {len(facilities)}件[/cyan]")
    matched, unmatched = 0, []
    pc, ps = [], []
    for code, data in facilities.items():
        fac = code_to_fac.get(code)
        if not fac:
            unmatched.append((code, data["name"]))
            continue
        matched += 1
        for d, st in data["cal"].items():
            avail = 1 if st == "空き" else 0
            common = {
                "facility_id": fac["id"], "court_name": "", "target_date": d,
                "start_time": cfg.open_time, "end_time": cfg.close_time,
                "availability_status": st,
                "available_court_count": avail, "total_court_count": 1,
                "source": "scrape",
            }
            pc.append({**common, "last_checked_at": now_iso})
            ps.append({**common, "snapshot_at": now_iso})

    console.print(f"  DB照合: {matched}施設 / 未照合: {len(unmatched)}")
    if unmatched:
        console.print(f"  [yellow]未照合(コード): {unmatched[:6]}[/yellow]")

    if not args.dry_run and pc:
        supa_upsert("availability_current", pc,
                    on_conflict="facility_id,court_name,target_date,start_time,end_time")
        supa_insert("availability_snapshots", ps)
        console.print(f"  [green]→ DB投入: {len(pc)}行[/green]")
    elif args.dry_run:
        console.print("  [yellow][dry-run] DB投入スキップ[/yellow]")

    console.print(f"\n[bold]完了: {matched}施設 / {len(pc)}行[/bold]")
    return 0 if matched > 0 else 1
