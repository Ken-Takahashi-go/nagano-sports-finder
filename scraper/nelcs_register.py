"""
NELCS 施設登録 (施設コードベース)

各市で登録用競技を巡回し、calendar_submit の施設コードをキーに DB登録。
external_facility_id = 施設コード(例 20209-00101), facility_name = clean_name(施設名)。

使い方:
  python nelcs_register.py ina
  python nelcs_register.py ina chikuma nakano minowa
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from nelcs_core import (  # noqa: E402
    SUPABASE_URL, SUPABASE_KEY, USER_AGENT, console, SPORT_ITEM,
    NelcsCityConfig, reach_facility_list, get_facilities, clean_name, _headers,
)

CITY_META = {
    "ina": ("伊那市", "INA", "nelcs_ina", "2020900", "https://www.inacity.jp/"),
    "chikuma": ("千曲市", "CHK", "nelcs_chikuma", "2021800", "https://www.city.chikuma.lg.jp/"),
    "nakano": ("中野市", "NKN", "nelcs_nakano", "2021100", "https://www.city.nakano.nagano.jp/"),
    "minowa": ("箕輪町", "MNW", "nelcs_minowa", "2038300", "https://www.town.minowa.lg.jp/"),
}

REGISTER_SPORTS = ["basketball", "tennis_hard", "soccer", "futsal"]


def classify(name: str, sports: set) -> tuple[str, list[str]]:
    if "テニス" in name or "庭球" in name:
        return ("TEN", ["tennis"])
    if "サッカー" in name:
        return ("SOC", ["soccer", "multi"])
    if any(k in name for k in ["グラウンド", "運動場", "運動公園", "球場", "広場"]):
        return ("GND", ["soccer", "multi"])
    if any(k in name for k in ["体育館", "アリーナ", "体育センター", "総合運動"]):
        return ("GYM", ["basketball", "volleyball", "multi"])
    # 名前で判らなければ出現競技から
    s = []
    if "basketball" in sports:
        s += ["basketball", "volleyball", "multi"]
    if any(t.startswith("tennis") for t in sports):
        s += ["tennis"]
    if "soccer" in sports:
        s += ["soccer", "multi"]
    if "futsal" in sports:
        s += ["futsal"]
    return ("GYM", list(dict.fromkeys(s)) or ["multi"])


def register_city(page, key: str) -> int:
    name, prefix, ext_sys, muni_id, official = CITY_META[key]
    cfg = NelcsCityConfig(name=name, external_system=ext_sys, municipality_id=muni_id)
    console.print(f"\n[bold cyan]===== {name} =====[/bold cyan]")

    code_info: dict[str, dict] = {}  # code -> {name, sports:set}
    for sport in REGISTER_SPORTS:
        if sport not in SPORT_ITEM:
            continue
        cat, item = SPORT_ITEM[sport]
        try:
            reach_facility_list(page, cfg, cat, item)
            facs = get_facilities(page)
            console.print(f"  [{sport}] {len(facs)}件")
            for f in facs:
                c = f["code"]
                if c not in code_info:
                    code_info[c] = {"name": clean_name(f["name"]), "sports": set()}
                code_info[c]["sports"].add(sport)
        except Exception as e:
            console.print(f"  [yellow]{sport} 失敗: {str(e)[:45]}[/yellow]")

    console.print(f"  収集: {len(code_info)}施設(コード)")
    fac_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/facilities"
    sport_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/facility_sports"
    counters: dict[str, int] = defaultdict(int)
    ok = 0
    for code, info in sorted(code_info.items()):
        sub, sports = classify(info["name"], info["sports"])
        counters[sub] += 1
        fcode = f"{prefix}-{sub}-{counters[sub]:03d}"
        row = {
            "facility_code": fcode, "facility_name": info["name"] or code,
            "municipality": name, "indoor_outdoor": "要確認",
            "surface_type": "要確認", "booking_method": "Web",
            "external_system": ext_sys, "external_facility_id": code,
            "data_confidence": "C", "official_url": official,
            "reservation_url": f"{cfg.base}/RsvIndex.php5",
            "notes": f"{name}公共施設予約システム(NELCS)より取得。施設コードで空き状況を照合。詳細要確認(簡易登録)。",
        }
        r = httpx.post(fac_url, params={"on_conflict": "facility_code"},
                       headers=_headers({"Content-Type": "application/json",
                                         "Prefer": "resolution=merge-duplicates,return=representation"}),
                       json=[row], timeout=30.0)
        if r.status_code >= 400:
            console.print(f"  [red][NG] {fcode} ({info['name']}): {r.status_code} {r.text[:90]}[/red]")
            continue
        fac_id = r.json()[0]["id"]
        srows = [{"facility_id": fac_id, "sport": s} for s in sports]
        httpx.post(sport_url, headers=_headers({"Content-Type": "application/json",
                                                "Prefer": "resolution=ignore-duplicates,return=minimal"}),
                   json=srows, timeout=30.0)
        console.print(f"  [green][OK] {fcode} {info['name'][:22]} [{','.join(sports)}][/green]")
        ok += 1
    console.print(f"  [bold]登録 {ok}施設[/bold]")
    return ok


def main() -> int:
    if not SUPABASE_URL or not SUPABASE_KEY:
        console.print("[red]ERROR: SUPABASE 認証情報 未設定[/red]")
        return 1
    keys = sys.argv[1:] or ["ina"]
    console.print(f"[bold green]NELCS 施設登録: {keys}[/bold green]")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(user_agent=USER_AGENT, locale="ja-JP",
                                   viewport={"width": 400, "height": 800}).new_page()
        page.set_default_timeout(20000)
        total = 0
        for key in keys:
            if key not in CITY_META:
                console.print(f"[red]未知のkey: {key}[/red]")
                continue
            total += register_city(page, key)
        browser.close()
    console.print(f"\n[bold]全登録: {total}施設[/bold]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
