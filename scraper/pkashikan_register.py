"""
P-Kashikan 施設登録 (施設名ベース)

各市で登録用競技を検索 → カレンダーの施設名(h3)を収集 → スポーツ施設のみ
フィルタ・分類して DB登録。P-Kashikan は施設名で照合するため
external_facility_id にも施設名を入れる。

使い方:
  python pkashikan_register.py suzaka
  python pkashikan_register.py suzaka ueda komagane tomi omachi
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from pkashikan_core import (  # noqa: E402
    SUPABASE_URL, SUPABASE_KEY, USER_AGENT, console,
    SPORT_SEARCH, fetch_sport_day, parse_calendar, _headers,
)
from datetime import datetime  # noqa: E402

# key → (市名, prefix, external_system, base_url, 公式URL)
CITY_META = {
    "suzaka": ("須坂市", "SUZ", "pkashikan_suzaka", "https://k3.p-kashikan.jp/suzaka-city", "https://www.city.suzaka.nagano.jp/"),
    "ueda": ("上田市", "UED", "pkashikan_ueda", "https://k6.p-kashikan.jp/ueda-city", "https://www.city.ueda.nagano.jp/"),
    "komagane": ("駒ヶ根市", "KMG", "pkashikan_komagane", "https://k3.p-kashikan.jp/komagane-city", "https://www.city.komagane.nagano.jp/"),
    "tomi": ("東御市", "TOM", "pkashikan_tomi", "https://k2.p-kashikan.jp/tomi-city", "https://www.city.tomi.nagano.jp/"),
    "omachi": ("大町市", "OMC", "pkashikan_omachi", "https://k5.p-kashikan.jp/omachi-city", "https://www.city.omachi.nagano.jp/"),
}

# 施設登録のために検索する競技 (体育館/テニス/サッカー/フットサルを網羅)
REGISTER_SPORTS = ["basketball", "tennis_hard", "tennis_soft", "soccer", "futsal"]

# スポーツ施設でないものを除外 (多目的室・文化施設)
EXCLUDE_KW = ["公民館", "公会堂", "プラザ", "ホール", "会議", "学習", "図書",
              "美術", "文化", "資料館", "交流", "ふれあい", "コミュニティ", "集会"]


def is_sport_facility(name: str) -> bool:
    return name and not any(k in name for k in EXCLUDE_KW)


def classify(name: str) -> tuple[str, list[str]]:
    if "テニス" in name or "庭球" in name:
        return ("TEN", ["tennis"])
    if "サッカー" in name:
        return ("SOC", ["soccer", "futsal", "multi"])
    if any(k in name for k in ["グラウンド", "運動場", "運動公園", "球技", "球場", "スポーツ広場"]):
        return ("GND", ["soccer", "multi"])
    if any(k in name for k in ["体育館", "アリーナ", "体育センター", "体育施設", "総合体育"]):
        return ("GYM", ["basketball", "volleyball", "multi"])
    return ("GYM", ["multi"])  # その他スポーツ施設(学校体育館等含む)


def collect_facilities(page, base_url: str) -> dict[str, set]:
    """登録用競技を順に検索し、施設名→出現競技 を集める"""
    today = datetime.now().strftime("%Y%m%d")
    fac_sports: dict[str, set] = defaultdict(set)
    for sport in REGISTER_SPORTS:
        if sport not in SPORT_SEARCH:
            continue
        tv, mk = SPORT_SEARCH[sport]
        try:
            html = fetch_sport_day(page, base_url, tv, mk, today)
            parsed = parse_calendar(html)
            for fac_name in parsed:
                fac_sports[fac_name].add(sport)
            console.print(f"    {sport}: {len(parsed)}施設")
        except Exception as e:
            console.print(f"    [yellow]{sport} 失敗: {str(e)[:50]}[/yellow]")
    return fac_sports


def register_city(page, key: str) -> int:
    name, prefix, ext_sys, base_url, official = CITY_META[key]
    console.print(f"\n[bold cyan]===== {name} =====[/bold cyan]")
    fac_sports = collect_facilities(page, base_url)
    console.print(f"  収集施設(全競技): {len(fac_sports)}")

    fac_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/facilities"
    sport_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/facility_sports"

    counters: dict[str, int] = defaultdict(int)
    ok = 0
    excluded = []
    for fac_name in sorted(fac_sports):
        if not is_sport_facility(fac_name):
            excluded.append(fac_name)
            continue
        sub, base_sports = classify(fac_name)
        # 出現競技からも sport を補強
        sports = set(base_sports)
        for sp in fac_sports[fac_name]:
            if sp.startswith("tennis"):
                sports.add("tennis")
            elif sp == "soccer":
                sports.update(["soccer", "multi"])
            elif sp == "futsal":
                sports.add("futsal")
            elif sp == "basketball":
                sports.update(["basketball", "volleyball"])
        counters[sub] += 1
        code = f"{prefix}-{sub}-{counters[sub]:03d}"
        row = {
            "facility_code": code, "facility_name": fac_name,
            "municipality": name, "indoor_outdoor": "要確認",
            "surface_type": "要確認", "booking_method": "Web",
            "external_system": ext_sys, "external_facility_id": fac_name,
            "data_confidence": "C", "official_url": official,
            "reservation_url": f"{base_url}/",
            "notes": f"{name}公共施設予約システム(P-Kashikan)より取得。施設名で空き状況を照合。詳細要確認(簡易登録)。",
        }
        r = httpx.post(fac_url, params={"on_conflict": "facility_code"},
                       headers=_headers({"Content-Type": "application/json",
                                         "Prefer": "resolution=merge-duplicates,return=representation"}),
                       json=[row], timeout=30.0)
        if r.status_code >= 400:
            console.print(f"  [red][NG] {code} ({fac_name}): {r.status_code} {r.text[:100]}[/red]")
            continue
        fac_id = r.json()[0]["id"]
        srows = [{"facility_id": fac_id, "sport": s} for s in sorted(sports)]
        httpx.post(sport_url, headers=_headers({"Content-Type": "application/json",
                                                "Prefer": "resolution=ignore-duplicates,return=minimal"}),
                   json=srows, timeout=30.0)
        console.print(f"  [green][OK] {code} {fac_name} [{','.join(sorted(sports))}][/green]")
        ok += 1

    console.print(f"  [bold]登録 {ok} / 除外(非スポーツ) {len(excluded)}[/bold]")
    if excluded:
        console.print(f"  [dim]除外例: {excluded[:6]}[/dim]")
    return ok


def main() -> int:
    if not SUPABASE_URL or not SUPABASE_KEY:
        console.print("[red]ERROR: SUPABASE 認証情報 未設定[/red]")
        return 1
    keys = sys.argv[1:] or ["suzaka"]
    console.print(f"[bold green]P-Kashikan 施設登録: {keys}[/bold green]")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(user_agent=USER_AGENT, locale="ja-JP",
                                   viewport={"width": 1280, "height": 900}).new_page()
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
