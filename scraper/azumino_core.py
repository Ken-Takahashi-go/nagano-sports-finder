"""
安曇野市 公共施設予約システム(富士通Wg_系/ASP.NET WebForms) スクレイパー (Playwright)

フロー(4段階, 全て __doPostBack):
  Wg_ModeSelect → 「スポーツ施設」(btnSSCategory) → Wg_ShisetsuIchiran(施設選択)
  → btnForward → Wg_NichijiSentaku(日時/表示形式) → btnForward
  → Wg_ShisetsubetsuAkiJoukyou(施設別空き状況)

空き状況: hidden input name に
  h_dlRepeat_ctlXX_tpItem_dgTable_ctlYY_bYYYYMMDD, value=○/△/×/－
  施設(dlRepeat_ctlXX) × 部屋(dgTable_ctlYY) × 日付(bYYYYMMDD)

施設別空き状況は複数施設を一覧表示(dlRepeat_ctl00, ctl01..)するため、
スポーツ施設を選択上限まで選んで一括取得 → 日別に集約。施設名で照合。
"""
from __future__ import annotations

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
BASE = "https://www4.pf489.com/azumino/web"
EXTERNAL_SYSTEM = "azumino_fujitsu"
DEFAULT_OPEN = "09:00"
DEFAULT_CLOSE = "21:00"
SHOTS = SCRIPT_DIR / "outputs" / "azumino_screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)

STATUS_MAP = {
    "○": "空き", "◯": "空き", "△": "一部空き",
    "×": "満", "✕": "満", "－": "unavailable", "-": "unavailable", "ー": "unavailable",
}


def _ascii_safe(s: str | None) -> str:
    if s is None:
        return ""
    return str(s).replace("﻿", "").strip().encode("ascii", errors="ignore").decode("ascii")


SUPABASE_URL = _ascii_safe(os.getenv("SUPABASE_URL"))
SUPABASE_KEY = _ascii_safe(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


def _headers(extra: dict | None = None) -> dict:
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    if extra:
        h.update(extra)
    return h


def supa_get(path: str, params: dict | None = None) -> list[dict]:
    r = httpx.get(f"{SUPABASE_URL.rstrip('/')}/rest/v1/{path}", params=params,
                  headers=_headers(), timeout=30.0)
    r.raise_for_status()
    return r.json()


def supa_upsert(path: str, rows: list[dict], on_conflict: str) -> None:
    r = httpx.post(f"{SUPABASE_URL.rstrip('/')}/rest/v1/{path}", params={"on_conflict": on_conflict},
                   headers=_headers({"Content-Type": "application/json",
                                     "Prefer": "resolution=merge-duplicates,return=minimal"}),
                   json=rows, timeout=60.0)
    if r.status_code >= 400:
        raise RuntimeError(f"upsert {path}: {r.status_code} {r.text[:300]}")


def supa_insert(path: str, rows: list[dict]) -> None:
    r = httpx.post(f"{SUPABASE_URL.rstrip('/')}/rest/v1/{path}",
                   headers=_headers({"Content-Type": "application/json", "Prefer": "return=minimal"}),
                   json=rows, timeout=60.0)
    if r.status_code >= 400:
        raise RuntimeError(f"insert {path}: {r.status_code} {r.text[:300]}")


# --------------------------------------------------------------------
# パース: 施設別空き状況 (hidden input ..._bYYYYMMDD value=○△×)
# --------------------------------------------------------------------
def parse_availability(html: str) -> dict[str, dict[str, str]]:
    """
    return { 施設名: { date: status } }
    施設名は lnkShisetsu (h_dlRepeat_ctlXX_tpItem_lnkShisetsu) のラベルから、
    状態は dgTable_ctlYY_bYYYYMMDD の value から。施設(ctlXX)単位で日別集約(空き優先)。
    """
    soup = BeautifulSoup(html, "lxml")
    # 施設インデックス → 施設名
    idx_name: dict[str, str] = {}
    for a in soup.find_all("a"):
        aid = a.get("id", "") or ""
        m = re.search(r"dlRepeat_ctl(\d+)_tpItem_lnkShisetsu", aid)
        if m:
            idx_name[m.group(1)] = a.get_text(strip=True)
    # セル状態
    by_idx: dict[str, dict[str, str]] = {}
    for inp in soup.find_all("input"):
        name = inp.get("id", "") or inp.get("name", "")
        m = re.search(r"dlRepeat_ctl(\d+)_tpItem_dgTable_ctl(\d+)_b(\d{8})", name)
        if not m:
            continue
        fac_idx, _room, ymd = m.groups()
        raw = (inp.get("value") or "").replace("&nbsp;", "").replace("\xa0", "").replace("　", "").strip()
        st = STATUS_MAP.get(raw, "unknown")
        date = f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}"
        d = by_idx.setdefault(fac_idx, {})
        # 空き優先で日別集約 (複数部屋のうち1つでも空きなら空き)
        prev = d.get(date)
        if prev is None or _rank(st) > _rank(prev):
            d[date] = st
    # 施設名キーに変換
    result: dict[str, dict[str, str]] = {}
    for idx, cal in by_idx.items():
        nm = idx_name.get(idx, f"施設{idx}")
        # unavailable/unknownのみの日は除外しつつ、空き/一部/満は残す
        cal2 = {dt: s for dt, s in cal.items() if s in ("空き", "一部空き", "満")}
        if cal2:
            result[nm] = cal2
    return result


def _rank(status: str) -> int:
    return {"満": 1, "一部空き": 2, "空き": 3}.get(status, 0)


# --------------------------------------------------------------------
# Playwright フロー
# --------------------------------------------------------------------
def _postback(page, target: str) -> None:
    page.evaluate(f"() => {{ if(typeof __doPostBack==='function') __doPostBack('{target}',''); }}")
    page.wait_for_load_state("networkidle", timeout=25000)
    page.wait_for_timeout(1500)


def goto_shisetsu_list(page) -> None:
    """ModeSelect → スポーツ施設 → Wg_ShisetsuIchiran"""
    page.goto(f"{BASE}/Wg_ModeSelect.aspx", wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(1500)
    page.locator("text=スポーツ施設").first.click()
    page.wait_for_load_state("networkidle", timeout=25000)
    page.wait_for_timeout(1500)


def list_facility_names(page) -> list[str]:
    """施設選択画面の施設名一覧 (input[type=submit] value=施設名, onclick=CheckBox_OnClick)"""
    return page.evaluate("""
        () => Array.from(document.querySelectorAll("input[onclick*='CheckBox_OnClick']"))
            .map(i => (i.value || '').trim()).filter(Boolean)
    """)


def fetch_availability_html(page, facility_names: list[str]) -> str:
    """指定施設群を選択 → 日時 → 空き状況HTML。施設選択上限に注意(分割呼び出し前提)"""
    goto_shisetsu_list(page)
    # 施設を選択(input[type=submit] value=施設名)。CheckBox_OnClickはチェックのみ(submitしない)
    for nm in facility_names:
        try:
            page.locator(f"input[value='{nm}']").first.click(force=True, timeout=5000)
            page.wait_for_timeout(300)
        except Exception as e:
            console.print(f"    [dim]選択失敗 {nm}: {str(e)[:30]}[/dim]")
    # 次へ → 日時選択
    _postback(page, "ucPCFooter$btnForward")
    # 表示形式=カレンダー(月間)を選択してから次へ (rbCalendar)。無ければデフォルトのまま
    try:
        cal = page.locator("input[name='rbCalendar']").first
        if cal.count():
            cal.click()
            page.wait_for_timeout(600)
    except Exception:
        pass
    # 次へ → 施設別空き状況
    _postback(page, "ucPCFooter$btnForward")
    # content取得リトライ
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


def build_arg_parser():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--batch", type=int, default=5, help="一度に選択する施設数")
    return ap


def run_scrape(args) -> int:
    console.print(f"[bold green]安曇野市 スクレイプ ({EXTERNAL_SYSTEM})[/bold green]\n")
    if not SUPABASE_URL or not SUPABASE_KEY:
        console.print("[red]ERROR: SUPABASE 認証情報 未設定[/red]")
        return 1

    db_facs = supa_get("facilities", {
        "external_system": f"eq.{EXTERNAL_SYSTEM}",
        "select": "id,facility_code,facility_name,external_facility_id",
    })
    name_to_fac = {f["facility_name"]: f for f in db_facs}
    console.print(f"[cyan]DB登録施設: {len(db_facs)}件[/cyan]")

    now_iso = datetime.now(timezone.utc).isoformat()
    collected: dict[str, dict[str, str]] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(user_agent=USER_AGENT, locale="ja-JP",
                                   viewport={"width": 1280, "height": 900}).new_page()
        page.set_default_timeout(20000)

        # 1セッション完結 (ASP.NET VIEWSTATEのため goto再実行は不安定)
        goto_shisetsu_list(page)
        all_names = list_facility_names(page)
        console.print(f"[cyan]スポーツ施設: {len(all_names)}件[/cyan]")

        # 選択上限(h_SelectedMax)を取得
        smax = page.evaluate("() => { const e=document.querySelector(\"input[name='h_SelectedMax']\"); return e? e.value : ''; }")
        console.print(f"  [dim]選択上限 h_SelectedMax={smax}[/dim]")
        limit = int(smax) if str(smax).isdigit() and int(smax) > 0 else args.batch

        # 施設を選択 (上限内)
        selected = []
        for nm in all_names[:limit]:
            try:
                page.locator(f"input[value='{nm}']").first.click(force=True, timeout=4000)
                page.wait_for_timeout(150)
                selected.append(nm)
            except Exception as e:
                console.print(f"  [dim]選択不可 {nm}: {str(e)[:25]}[/dim]")
        console.print(f"  選択: {len(selected)}施設")

        try:
            _postback(page, "ucPCFooter$btnForward")  # → 日時選択
            console.print(f"  [dim]遷移1: {page.url.split('/')[-1]}[/dim]")
            # 横表示のまま 期間=1ヶ月・終日・全曜日 に設定して期間分を取得
            for rb in ["rbtnMonth", "rbtnAllday"]:
                try:
                    page.locator(f"input[name='{rb}']").first.click(force=True, timeout=2000)
                    page.wait_for_timeout(250)
                except Exception:
                    pass
            for chk in ["chkMon", "chkTue", "chkWed", "chkThu", "chkFri", "chkSat", "chkSun", "chkHol"]:
                try:
                    page.locator(f"input[name='{chk}']").first.check(timeout=1500)
                except Exception:
                    pass
            _postback(page, "ucPCFooter$btnForward")  # → 施設別空き状況
            console.print(f"  [dim]遷移2: {page.url.split('/')[-1]}[/dim]")
            html = ""
            for _ in range(3):
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=8000)
                    html = page.content()
                    if html:
                        break
                except Exception:
                    page.wait_for_timeout(1500)
            parsed = parse_availability(html)
            for nm, cal in parsed.items():
                collected[nm] = cal
            console.print(f"  取得: {len(parsed)}施設")
        except Exception as e:
            console.print(f"  [red]空き状況取得失敗: {str(e)[:60]}[/red]")

        browser.close()

    console.print(f"\n[cyan]取得施設: {len(collected)}件[/cyan]")
    matched, unmatched = 0, []
    pc, ps = [], []
    for nm, cal in collected.items():
        fac = name_to_fac.get(nm)
        if not fac:
            unmatched.append(nm)
            continue
        matched += 1
        for dt, st in cal.items():
            avail = 1 if st in ("空き", "一部空き") else 0
            common = {
                "facility_id": fac["id"], "court_name": "", "target_date": dt,
                "start_time": DEFAULT_OPEN, "end_time": DEFAULT_CLOSE,
                "availability_status": st, "available_court_count": avail,
                "total_court_count": 1, "source": "scrape",
            }
            pc.append({**common, "last_checked_at": now_iso})
            ps.append({**common, "snapshot_at": now_iso})

    console.print(f"  DB照合: {matched}施設 / 未照合: {len(unmatched)}")
    if unmatched:
        console.print(f"  [yellow]未照合: {unmatched[:8]}[/yellow]")
    if not args.dry_run and pc:
        supa_upsert("availability_current", pc,
                    on_conflict="facility_id,court_name,target_date,start_time,end_time")
        supa_insert("availability_snapshots", ps)
        console.print(f"  [green]→ DB投入: {len(pc)}行[/green]")
    elif args.dry_run:
        console.print("  [yellow][dry-run] スキップ[/yellow]")
    console.print(f"\n[bold]完了: {matched}施設 / {len(pc)}行[/bold]")
    return 0 if matched > 0 else 1


if __name__ == "__main__":
    sys.exit(run_scrape(build_arg_parser().parse_args()))

