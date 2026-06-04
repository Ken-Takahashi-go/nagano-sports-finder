"""
安曇野市 施設登録 (施設名ベース)

スポーツ施設カテゴリの施設名を取得し、スポーツ施設のみ分類してDB登録。
external_facility_id = facility_name (空き状況は施設名で照合)。
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from azumino_core import (  # noqa: E402
    EXTERNAL_SYSTEM, USER_AGENT, console, SUPABASE_URL, SUPABASE_KEY,
    _headers, goto_shisetsu_list, list_facility_names,
)

OFFICIAL = "https://www.city.azumino.nagano.jp/"
RESERVE = "https://www4.pf489.com/azumino/web/"
PREFIX = "AZM"

EXCLUDE = ["公民館", "集会", "研修", "会議", "文化", "資料館", "交流", "ホール", "学習", "センター施設"]


def is_sport(n: str) -> bool:
    return bool(n) and not any(k in n for k in EXCLUDE)


def classify(n: str) -> tuple[str, list[str]]:
    if "テニス" in n or "庭球" in n:
        return ("TEN", ["tennis"])
    if "サッカー" in n:
        return ("SOC", ["soccer", "multi"])
    if any(k in n for k in ["運動広場", "運動公園", "グラウンド", "運動場", "スポーツ広場"]):
        return ("GND", ["soccer", "multi"])
    if any(k in n for k in ["体育館", "アリーナ", "武道", "弓道", "総合公園", "スポーツ施設"]):
        return ("GYM", ["basketball", "volleyball", "multi"])
    if any(k in n for k in ["小学校", "中学校", "高校", "学校"]):
        return ("GYM", ["basketball", "volleyball", "multi"])  # 学校開放
    return ("GYM", ["multi"])


def main() -> int:
    if not SUPABASE_URL or not SUPABASE_KEY:
        console.print("[red]ERROR: SUPABASE 認証情報 未設定[/red]")
        return 1
    console.print("[bold green]安曇野市 施設登録[/bold green]")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(user_agent=USER_AGENT, locale="ja-JP",
                                   viewport={"width": 1280, "height": 900}).new_page()
        page.set_default_timeout(20000)
        goto_shisetsu_list(page)
        names = list_facility_names(page)
        browser.close()

    console.print(f"  取得施設(全): {len(names)}件")
    fac_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/facilities"
    sport_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/facility_sports"
    counters: dict[str, int] = defaultdict(int)
    ok, excluded = 0, []
    for nm in names:
        if not is_sport(nm):
            excluded.append(nm)
            continue
        sub, sports = classify(nm)
        counters[sub] += 1
        code = f"{PREFIX}-{sub}-{counters[sub]:03d}"
        row = {
            "facility_code": code, "facility_name": nm, "municipality": "安曇野市",
            "indoor_outdoor": "要確認", "surface_type": "要確認", "booking_method": "Web",
            "external_system": EXTERNAL_SYSTEM, "external_facility_id": nm,
            "data_confidence": "C", "official_url": OFFICIAL, "reservation_url": RESERVE,
            "notes": "安曇野市公共施設予約システム(富士通Wg_系)より取得。施設名で空き状況を照合。詳細要確認(簡易登録)。",
        }
        r = httpx.post(fac_url, params={"on_conflict": "facility_code"},
                       headers=_headers({"Content-Type": "application/json",
                                         "Prefer": "resolution=merge-duplicates,return=representation"}),
                       json=[row], timeout=30.0)
        if r.status_code >= 400:
            console.print(f"  [red][NG] {code} ({nm}): {r.status_code} {r.text[:90]}[/red]")
            continue
        fac_id = r.json()[0]["id"]
        srows = [{"facility_id": fac_id, "sport": s} for s in sports]
        httpx.post(sport_url, headers=_headers({"Content-Type": "application/json",
                                                "Prefer": "resolution=ignore-duplicates,return=minimal"}),
                   json=srows, timeout=30.0)
        console.print(f"  [green][OK] {code} {nm[:24]} [{','.join(sports)}][/green]")
        ok += 1

    console.print(f"\n[bold]登録 {ok}施設 / 除外(非スポーツ) {len(excluded)}[/bold]")
    if excluded:
        console.print(f"  [dim]除外例: {excluded[:6]}[/dim]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
