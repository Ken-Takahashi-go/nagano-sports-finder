"""
seed 015 相当を Supabase REST (PATCH) で適用

webR checkShisetsu value (=external_facility_id) を MAT-GYM facility に紐付け。
psql が無い環境なので REST 経由で直接 UPDATE する。

対応表 (Stage M3 / M3-fix v2 で確定):
  202001 総合体育館   → MAT-GYM-001
  202002 南部体育館   → MAT-GYM-005
  202003 岡田体育館   → MAT-GYM-012
  202004 芳川体育館   → MAT-GYM-017
  202005 島内体育館   → MAT-GYM-015
  202006 庄内体育館   → MAT-GYM-006
  202007 芝沢体育館   → MAT-GYM-008
  202008 神林体育館   → MAT-GYM-013
  202009 里山辺体育館 → MAT-GYM-014
  202010 鎌田体育館   → MAT-GYM-009
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
    ("202001", "MAT-GYM-001", "総合体育館"),
    ("202002", "MAT-GYM-005", "南部体育館"),
    ("202003", "MAT-GYM-012", "岡田体育館"),
    ("202004", "MAT-GYM-017", "芳川体育館"),
    ("202005", "MAT-GYM-015", "島内体育館"),
    ("202006", "MAT-GYM-006", "庄内体育館"),
    ("202007", "MAT-GYM-008", "芝沢体育館"),
    ("202008", "MAT-GYM-013", "神林体育館"),
    ("202009", "MAT-GYM-014", "里山辺体育館"),
    ("202010", "MAT-GYM-009", "鎌田体育館"),
]


def _headers(extra: dict | None = None) -> dict:
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    if extra:
        h.update(extra)
    return h


def main() -> int:
    if not SUPABASE_URL or not SUPABASE_KEY:
        console.print("[red]ERROR: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 未設定[/red]")
        return 1

    console.print("[bold green]seed 015: external_facility_id 一括紐付け (REST)[/bold green]\n")
    base = f"{SUPABASE_URL.rstrip('/')}/rest/v1/facilities"

    ok, skip, fail = 0, 0, 0
    for ext_id, code, name in MAPPING:
        # 対象確認
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
            console.print(f"  [dim][--] {code} ({row['facility_name']}): 既に {ext_id} 紐付け済[/dim]")
            skip += 1
            continue

        # PATCH
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
            console.print(f"  [green][OK] {code} ({row['facility_name']}) <- webR {ext_id} ({name})[/green]")
            ok += 1

    console.print(f"\n[bold]結果: 新規 {ok} / スキップ {skip} / 失敗 {fail}[/bold]")

    # 確認クエリ
    verify = httpx.get(base, params={
        "municipality": "eq.松本市",
        "external_facility_id": "not.is.null",
        "select": "facility_code,facility_name,external_facility_id",
        "order": "external_facility_id",
    }, headers=_headers(), timeout=30.0)
    linked = verify.json()
    console.print(f"\n[cyan]松本市 紐付け済: {len(linked)}件[/cyan]")
    for f in linked:
        console.print(f"  {f['external_facility_id']} = {f['facility_code']} {f['facility_name']}")

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
