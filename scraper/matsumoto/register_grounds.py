"""
運動広場10件を DB 新規登録 + webR ID 紐付け (REST)

経緯:
  体育館残り15件は webR 非対応と判明 (体育館カテゴリは10件のみ登録)。
  代替として、webR 施設種類「運動広場」(種別08) の10件を新規登録する。
  多目的グラウンドで サッカー等の利用が想定される (A3スコープ補完)。

データ確度:
  webR の施設名・IDのみ確定。設備/路面/用途の詳細は未確認 → data_confidence='C'
  サッカー利用前提で sport タグ soccer + multi を付与。野球等は別途確認。

冪等:
  facilities は facility_code で upsert、facility_sports は on conflict do nothing。
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from rich.console import Console

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.parent
load_dotenv(SCRIPT_DIR / ".env")
console = Console()


def _ascii_safe(s: str | None) -> str:
    if s is None:
        return ""
    return str(s).replace("﻿", "").strip().encode("ascii", errors="ignore").decode("ascii")


SUPABASE_URL = _ascii_safe(os.getenv("SUPABASE_URL"))
SUPABASE_KEY = _ascii_safe(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
EXTERNAL_SYSTEM = "matsumoto_webR"
OFFICIAL_URL = "https://www.city.matsumoto.nagano.jp/"

# (facility_code, external_facility_id, 施設名)  ← M3-fix v3 種別08 の結果
GROUNDS = [
    ("MAT-GND-001", "202037", "内田運動広場"),
    ("MAT-GND-002", "202038", "並柳運動広場"),
    ("MAT-GND-003", "202039", "横田運動広場"),
    ("MAT-GND-004", "202040", "入山辺運動広場"),
    ("MAT-GND-005", "202041", "芝沢運動広場"),
    ("MAT-GND-006", "202042", "寿運動広場"),
    ("MAT-GND-007", "202043", "両島浄化センター運動広場"),
    ("MAT-GND-008", "202044", "笹賀運動広場"),
    ("MAT-GND-009", "202045", "今井運動広場"),
    ("MAT-GND-010", "202046", "岡田運動広場"),
]

NOTES = "webR施設種類「運動広場」として登録。多目的グラウンド。サッカー等の利用想定だが設備・路面・対応競技は要確認(簡易登録)。"


def _headers(extra: dict | None = None) -> dict:
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    if extra:
        h.update(extra)
    return h


def main() -> int:
    if not SUPABASE_URL or not SUPABASE_KEY:
        console.print("[red]ERROR: SUPABASE 認証情報 未設定[/red]")
        return 1

    console.print("[bold green]運動広場10件 新規登録 + webR ID 紐付け[/bold green]\n")
    fac_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/facilities"
    sport_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/facility_sports"

    ok, fail = 0, 0
    for code, ext_id, name in GROUNDS:
        row = {
            "facility_code": code,
            "facility_name": name,
            "municipality": "松本市",
            "indoor_outdoor": "屋外",
            "surface_type": "要確認",
            "booking_method": "Web",
            "external_system": EXTERNAL_SYSTEM,
            "external_facility_id": ext_id,
            "data_confidence": "C",
            "official_url": OFFICIAL_URL,
            "notes": NOTES,
        }
        # facilities upsert (return id)
        r = httpx.post(fac_url, params={"on_conflict": "facility_code"},
                       headers=_headers({"Content-Type": "application/json",
                                         "Prefer": "resolution=merge-duplicates,return=representation"}),
                       json=[row], timeout=30.0)
        if r.status_code >= 400:
            console.print(f"  [red][NG] {code} ({name}): {r.status_code} {r.text[:150]}[/red]")
            fail += 1
            continue
        fac_id = r.json()[0]["id"]

        # facility_sports: soccer + multi
        sports = [{"facility_id": fac_id, "sport": s} for s in ("soccer", "multi")]
        rs = httpx.post(sport_url,
                        headers=_headers({"Content-Type": "application/json",
                                          "Prefer": "resolution=ignore-duplicates,return=minimal"}),
                        json=sports, timeout=30.0)
        sport_ok = rs.status_code < 400
        console.print(f"  [green][OK] {code} ({name}) <- webR {ext_id}[/green]"
                      f"{'' if sport_ok else ' [yellow](sportタグ失敗)[/yellow]'}")
        ok += 1

    console.print(f"\n[bold]結果: 登録 {ok} / 失敗 {fail}[/bold]")

    # 確認: 松本市総数 と 紐付け済み数
    facs = httpx.get(fac_url, params={
        "municipality": "eq.松本市", "select": "facility_code,external_facility_id",
    }, headers=_headers(), timeout=30.0).json()
    linked = sum(1 for f in facs if f["external_facility_id"])
    console.print(f"[cyan]松本市 総施設数: {len(facs)} / webR紐付け済: {linked}[/cyan]")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
