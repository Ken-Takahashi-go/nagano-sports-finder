"""
webR 汎用 register: webr_probe.py の出力を読んで施設を DB 登録 + ID紐付け

各市の施設を facility_code 採番してDB登録し、
scrape 用の type_map (facility_code prefix → 施設種類番号) を算出・表示する。

使い方:
  python webr_register.py chino suwa okaya   # 指定市を登録
  python webr_register.py                      # 全 probe 出力を登録

市コード/external_system は CITY_META で管理。
"""
from __future__ import annotations

import io
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import httpx
from dotenv import load_dotenv
from rich.console import Console

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
load_dotenv(SCRIPT_DIR / ".env")
console = Console()


def _ascii_safe(s: str | None) -> str:
    if s is None:
        return ""
    return str(s).replace("﻿", "").strip().encode("ascii", errors="ignore").decode("ascii")


SUPABASE_URL = _ascii_safe(os.getenv("SUPABASE_URL"))
SUPABASE_KEY = _ascii_safe(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

# key → (市名, facility_code prefix, external_system, 公式URL, 予約URL)
CITY_META = {
    "chino": ("茅野市", "CHN", "chino_webR", "https://www.city.chino.lg.jp/", "https://www.pf489.com/chino/webr/"),
    "suwa": ("諏訪市", "SUW", "suwa_webR", "https://www.city.suwa.lg.jp/", "https://www.pf489.com/suwa/webr/"),
    "okaya": ("岡谷市", "OKA", "okaya_webR", "https://www.city.okaya.lg.jp/", "https://www.pf489.com/okaya/webr/"),
}

# sport_class → (code種別, sportタグ, 屋内/屋外)
SPORT_CLASS_MAP = {
    "体育館": ("GYM", ["basketball", "volleyball", "multi"], "屋内"),
    "テニス": ("TEN", ["tennis"], "屋外"),
    "サッカー": ("SOC", ["soccer", "futsal", "multi"], "屋外"),
    "フットサル": ("FUT", ["futsal", "multi"], "要確認"),
    "グラウンド": ("GND", ["soccer", "multi"], "屋外"),
}


def _headers(extra: dict | None = None) -> dict:
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    if extra:
        h.update(extra)
    return h


def register_city(key: str) -> dict:
    if key not in CITY_META:
        console.print(f"[red]未知のkey: {key}[/red]")
        return {}
    name, citycode, ext_sys, official, reserve = CITY_META[key]
    probe_path = SCRIPT_DIR / "outputs" / f"webr_probe_{key}.json"
    if not probe_path.exists():
        console.print(f"[red]{name}: probe出力なし ({probe_path.name})[/red]")
        return {}

    data = json.loads(probe_path.read_text(encoding="utf-8"))
    facs = data["facilities"]
    console.print(f"\n[bold cyan]===== {name} ({len(facs)}施設) =====[/bold cyan]")

    fac_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/facilities"
    sport_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/facility_sports"

    counters: dict[str, int] = defaultdict(int)
    type_map: dict[str, str] = {}
    ok, fail = 0, 0
    for f in facs:
        sc = f["sport_class"]
        if sc not in SPORT_CLASS_MAP:
            continue
        sub, sports, io_type = SPORT_CLASS_MAP[sc]
        counters[sub] += 1
        code = f"{citycode}-{sub}-{counters[sub]:03d}"
        # prefix → 施設種類番号 (同種別は同番号)
        type_map[f"{citycode}-{sub}"] = f["type_value"]

        name_clean = (f["name"] or "").rstrip("（(").strip()
        row = {
            "facility_code": code,
            "facility_name": name_clean,
            "municipality": name,
            "indoor_outdoor": io_type,
            "surface_type": "要確認",
            "booking_method": "Web",
            "external_system": ext_sys,
            "external_facility_id": f["value"],
            "data_confidence": "C",
            "official_url": official,
            "reservation_url": reserve,
            "notes": f"{name}公共施設予約システム(webR)より取得。設備・料金・路面等は要確認(簡易登録)。",
        }
        r = httpx.post(fac_url, params={"on_conflict": "facility_code"},
                       headers=_headers({"Content-Type": "application/json",
                                         "Prefer": "resolution=merge-duplicates,return=representation"}),
                       json=[row], timeout=30.0)
        if r.status_code >= 400:
            console.print(f"  [red][NG] {code} ({name_clean}): {r.status_code} {r.text[:120]}[/red]")
            fail += 1
            continue
        fac_id = r.json()[0]["id"]
        sport_rows = [{"facility_id": fac_id, "sport": s} for s in sports]
        httpx.post(sport_url,
                   headers=_headers({"Content-Type": "application/json",
                                     "Prefer": "resolution=ignore-duplicates,return=minimal"}),
                   json=sport_rows, timeout=30.0)
        console.print(f"  [green][OK] {code} ({name_clean}) <- webR {f['value']} [{sc}][/green]")
        ok += 1

    console.print(f"  [bold]登録 {ok} / 失敗 {fail}[/bold]")
    console.print(f"  [yellow]type_map (CityConfig用): {json.dumps(type_map, ensure_ascii=False)}[/yellow]")
    return type_map


def main() -> int:
    if not SUPABASE_URL or not SUPABASE_KEY:
        console.print("[red]ERROR: SUPABASE 認証情報 未設定[/red]")
        return 1
    keys = sys.argv[1:] or list(CITY_META.keys())
    console.print(f"[bold green]webR施設登録: {keys}[/bold green]")
    all_type_maps = {}
    for key in keys:
        tm = register_city(key)
        if tm:
            all_type_maps[key] = tm

    console.print("\n[bold]===== 全 type_map (webr_cities.py 用) =====[/bold]")
    for key, tm in all_type_maps.items():
        console.print(f"  {key}: {json.dumps(tm, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
