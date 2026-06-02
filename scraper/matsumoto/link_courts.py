"""
テニス・サッカー施設の webR ID を MAT-TEN/MAT-SOC に紐付け (REST PATCH)

Stage M3-fix v3 (施設種類検索) で取得した庭球場・サッカー場の
external_facility_id を、名前照合で確定した対応に基づき紐付ける。

確定マッピング (DB名 ⇔ webR名):
  テニス 8件 + サッカー 2件 = 10件
未解決 (webR 庭球場リストに無し → 別途調査):
  MAT-TEN-002 開智公園運動場(庭球場) / MAT-TEN-003 新村庭球場
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

# (external_facility_id, facility_code, webR施設名)
MAPPING = [
    # --- テニス (庭球場) ---
    ("202029", "MAT-TEN-001", "沢村庭球場"),
    ("202026", "MAT-TEN-004", "浅間温泉庭球公園"),
    ("202035", "MAT-TEN-005", "臨空工業団地庭球場"),
    ("202032", "MAT-TEN-006", "奈川木曽路原庭球場"),
    ("202033", "MAT-TEN-007", "乗鞍テニスコート"),
    ("202030", "MAT-TEN-008", "波田扇子田庭球場"),
    ("202027", "MAT-TEN-009", "美須々屋内運動場"),
    ("202028", "MAT-TEN-010", "南部屋内運動場"),
    # --- サッカー ---
    ("202066", "MAT-SOC-001", "サッカー場"),
    ("202067", "MAT-SOC-002", "かりがねサッカー場"),
]


def _headers(extra: dict | None = None) -> dict:
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    if extra:
        h.update(extra)
    return h


def main() -> int:
    if not SUPABASE_URL or not SUPABASE_KEY:
        console.print("[red]ERROR: SUPABASE 認証情報 未設定[/red]")
        return 1

    console.print("[bold green]テニス・サッカー施設 webR ID 紐付け[/bold green]\n")
    base = f"{SUPABASE_URL.rstrip('/')}/rest/v1/facilities"

    ok, skip, fail = 0, 0, 0
    for ext_id, code, name in MAPPING:
        chk = httpx.get(base, params={
            "facility_code": f"eq.{code}",
            "select": "id,facility_name,external_facility_id",
        }, headers=_headers(), timeout=30.0)
        if chk.status_code >= 400 or not chk.json():
            console.print(f"  [red][NG] {code} ({name}): facility 未発見[/red]")
            fail += 1
            continue
        row = chk.json()[0]
        if row.get("external_facility_id") == ext_id:
            console.print(f"  [dim][--] {code}: 既に {ext_id} 紐付け済[/dim]")
            skip += 1
            continue
        r = httpx.patch(base, params={"facility_code": f"eq.{code}"},
                        headers=_headers({"Content-Type": "application/json",
                                          "Prefer": "return=minimal"}),
                        json={"external_system": EXTERNAL_SYSTEM,
                              "external_facility_id": ext_id},
                        timeout=30.0)
        if r.status_code >= 400:
            console.print(f"  [red][NG] {code}: {r.status_code} {r.text[:150]}[/red]")
            fail += 1
        else:
            console.print(f"  [green][OK] {code} ({row['facility_name'][:24]}) <- webR {ext_id} ({name})[/green]")
            ok += 1

    console.print(f"\n[bold]結果: 新規 {ok} / スキップ {skip} / 失敗 {fail}[/bold]")

    # 確認: 松本市の紐付け済み総数
    linked = httpx.get(base, params={
        "municipality": "eq.松本市",
        "external_facility_id": "not.is.null",
        "select": "facility_code",
    }, headers=_headers(), timeout=30.0).json()
    console.print(f"[cyan]松本市 紐付け済み合計: {len(linked)}件[/cyan]")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
