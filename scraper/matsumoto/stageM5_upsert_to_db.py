"""
Stage M5: 解析済みカレンダー JSON を Supabase に upsert

入力:
  - outputs/matsumoto_M4_parsed.json (Stage M4 の出力)

処理:
  1. .env から SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 読み込み
  2. facility を external_system='matsumoto_webR' + external_facility_id で検索
     (存在しなければ facility_code から逆引き)
  3. 部屋ごとの○△× を集計し、1日1スロット(09:00-21:00)として記録:
     - 全部屋○ → '空き'      / available_count = N
     - 一部空き(○△) → '一部空き' / available_count = (○+△)の部屋数
     - 全部× → '満'          / available_count = 0
     - 全部－/休館 → '休館'  / available_count = 0
  4. availability_current に UPSERT
  5. availability_snapshots に INSERT

使い方:
  python matsumoto/stageM5_upsert_to_db.py --dry-run
  python matsumoto/stageM5_upsert_to_db.py            # 実投入
  python matsumoto/stageM5_upsert_to_db.py --facility-code MAT-GYM-001
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.parent
load_dotenv(SCRIPT_DIR / ".env")

console = Console()


def _ascii_safe(s: str | None) -> str:
    if s is None:
        return ""
    cleaned = str(s).replace("﻿", "").strip()
    return cleaned.encode("ascii", errors="ignore").decode("ascii")


SUPABASE_URL = _ascii_safe(os.getenv("SUPABASE_URL"))
SUPABASE_KEY = _ascii_safe(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
EXTERNAL_SYSTEM = "matsumoto_webR"

INPUT_JSON = SCRIPT_DIR / "outputs" / "matsumoto_M4_parsed.json"

# 松本市体育施設の標準営業時間 (1日1コマ集約用)
# 個別差は notes 等でカバー、ここではざっくり統一値
DEFAULT_OPEN = "09:00"
DEFAULT_CLOSE = "21:00"


# --------------------------------------------------------------------
# Supabase REST helpers
# --------------------------------------------------------------------
def _headers(extra: dict | None = None) -> dict:
    h = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
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
    headers = _headers({
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    })
    r = httpx.post(url, params={"on_conflict": on_conflict},
                   headers=headers, json=rows, timeout=60.0)
    if r.status_code >= 400:
        console.print(f"[red]upsert {path} failed: {r.status_code}[/red]")
        console.print(f"[red]{r.text[:500]}[/red]")
        r.raise_for_status()


def supa_insert(path: str, rows: list[dict]) -> None:
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{path}"
    headers = _headers({
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    })
    r = httpx.post(url, headers=headers, json=rows, timeout=60.0)
    if r.status_code >= 400:
        console.print(f"[red]insert {path} failed: {r.status_code}[/red]")
        console.print(f"[red]{r.text[:500]}[/red]")
        r.raise_for_status()


# --------------------------------------------------------------------
# 集約ロジック
# --------------------------------------------------------------------
def aggregate_daily(rooms: list[dict]) -> list[dict]:
    """
    rooms: [{room_part_id, room_name, slots:[{date,status,...}]}]
    → 日付ごとの集約: [{target_date, status, available, total}]
    """
    by_date: dict[str, dict[str, int]] = {}
    for r in rooms:
        for s in r["slots"]:
            d = s["date"]
            st = s["status"]
            if d not in by_date:
                by_date[d] = {"available": 0, "partial": 0, "full": 0,
                              "unavailable": 0, "closed": 0, "total": 0}
            by_date[d]["total"] += 1
            if st in by_date[d]:
                by_date[d][st] += 1

    results = []
    for d in sorted(by_date.keys()):
        c = by_date[d]
        total = c["total"]
        open_count = c["available"] + c["partial"]  # 予約可な部屋数

        # ステータス判定
        if c["closed"] + c["unavailable"] == total:
            status = "休館"
            avail = 0
        elif c["full"] == total - c["closed"] - c["unavailable"]:
            status = "満"
            avail = 0
        elif c["available"] == total - c["closed"] - c["unavailable"]:
            status = "空き"
            avail = open_count
        elif open_count > 0:
            status = "一部空き"
            avail = open_count
        else:
            status = "不明"
            avail = open_count

        results.append({
            "target_date": d,
            "status": status,
            "available_count": avail,
            "total_count": total,
            "breakdown": c,
        })
    return results


# --------------------------------------------------------------------
# main
# --------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="DB書き込みせず内容確認のみ")
    ap.add_argument("--facility-code", default=None,
                    help="入力JSONの代わりにDB照合に使う facility_code (デフォルト: MAT-GYM-001)")
    args = ap.parse_args()

    console.print("[bold green]Stage M5: Matsumoto availability upsert[/bold green]\n")

    if not INPUT_JSON.exists():
        console.print(f"[red]Input not found: {INPUT_JSON}[/red]")
        return 1
    if not SUPABASE_URL or not SUPABASE_KEY:
        console.print("[red]ERROR: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 未設定[/red]")
        return 1

    data = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    external_id = data["facility_external_id"]
    facility_name_guess = data["facility_name_guess"]
    rooms = data["rooms"]

    console.print(f"[cyan]ソース: {INPUT_JSON.name}[/cyan]")
    console.print(f"  external_id: {external_id}")
    console.print(f"  facility名(推定): {facility_name_guess}")
    console.print(f"  部屋数: {len(rooms)}")
    total_slots = sum(len(r["slots"]) for r in rooms)
    console.print(f"  総スロット数: {total_slots}\n")

    # ----------------------------------------------------------------
    # Step 1: facility を検索
    # ----------------------------------------------------------------
    console.print("[cyan]Step 1: facilities テーブルから対象を検索[/cyan]")
    facility_code = args.facility_code or "MAT-GYM-001"

    # まず external_facility_id で検索
    facilities = supa_get("facilities", {
        "external_system": f"eq.{EXTERNAL_SYSTEM}",
        "external_facility_id": f"eq.{external_id}",
        "select": "id,facility_code,facility_name,external_facility_id",
    })

    if not facilities:
        # 見つからなければ facility_code で検索
        console.print(f"  [yellow]external_facility_id={external_id} で未発見、{facility_code} で検索[/yellow]")
        facilities = supa_get("facilities", {
            "facility_code": f"eq.{facility_code}",
            "select": "id,facility_code,facility_name,external_facility_id,external_system",
        })

    if not facilities:
        console.print(f"[red]facility が見つかりません (external={external_id}, code={facility_code})[/red]")
        return 1

    facility = facilities[0]
    console.print(f"  [green][OK] {facility['facility_name']} (code={facility['facility_code']}, id={facility['id'][:8]}...)[/green]")

    needs_link = facility.get("external_facility_id") != external_id
    if needs_link:
        console.print(f"  [yellow][!] external_facility_id 未紐付け or 異なる → 更新します[/yellow]")

    # ----------------------------------------------------------------
    # Step 2: 集約
    # ----------------------------------------------------------------
    console.print("\n[cyan]Step 2: 部屋別 → 日付別 集約[/cyan]")
    daily = aggregate_daily(rooms)
    console.print(f"  → {len(daily)} 日分")

    tbl = Table(title="日次集約サマリ")
    tbl.add_column("日付")
    tbl.add_column("状態")
    tbl.add_column("空き/総", justify="right")
    tbl.add_column("○", justify="right", style="green")
    tbl.add_column("△", justify="right", style="yellow")
    tbl.add_column("×", justify="right", style="red")
    tbl.add_column("－/休", justify="right", style="dim")
    for d in daily:
        b = d["breakdown"]
        tbl.add_row(
            d["target_date"], d["status"],
            f"{d['available_count']}/{d['total_count']}",
            str(b["available"]), str(b["partial"]),
            str(b["full"]), str(b["unavailable"] + b["closed"]),
        )
    console.print(tbl)

    # ----------------------------------------------------------------
    # Step 3: payload 構築
    # ----------------------------------------------------------------
    now = datetime.now(timezone.utc).isoformat()
    facility_uuid = facility["id"]

    payloads_current = []
    payloads_snapshot = []
    for d in daily:
        common = {
            "facility_id": facility_uuid,
            "target_date": d["target_date"],
            "start_time": DEFAULT_OPEN,
            "end_time": DEFAULT_CLOSE,
            "availability_status": d["status"],
            "available_court_count": d["available_count"],
            "total_court_count": d["total_count"],
            "source": "scrape",
        }
        payloads_current.append({**common, "last_checked_at": now})
        payloads_snapshot.append({**common, "snapshot_at": now})

    console.print(f"\n[cyan]payload: current={len(payloads_current)} / snapshot={len(payloads_snapshot)}[/cyan]")

    if args.dry_run:
        console.print("[yellow][!] dry-run: DB書き込みスキップ[/yellow]")
        console.print(f"\nサンプル payload:")
        console.print(json.dumps(payloads_current[0], ensure_ascii=False, indent=2))
        return 0

    # ----------------------------------------------------------------
    # Step 4: external_facility_id を紐付け (必要なら)
    # ----------------------------------------------------------------
    if needs_link:
        console.print(f"\n[cyan]Step 4-a: external_facility_id={external_id} で紐付け[/cyan]")
        url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/facilities"
        r = httpx.patch(
            url,
            params={"id": f"eq.{facility_uuid}"},
            headers=_headers({"Content-Type": "application/json", "Prefer": "return=minimal"}),
            json={"external_system": EXTERNAL_SYSTEM, "external_facility_id": external_id},
            timeout=30.0,
        )
        if r.status_code >= 400:
            console.print(f"  [red]link failed: {r.status_code} {r.text[:200]}[/red]")
        else:
            console.print(f"  [green][OK] facility に external_facility_id を設定[/green]")

    # ----------------------------------------------------------------
    # Step 5: upsert / insert
    # ----------------------------------------------------------------
    console.print(f"\n[cyan]Step 5: Supabase 書き込み[/cyan]")
    supa_upsert("availability_current", payloads_current,
                on_conflict="facility_id,court_name,target_date,start_time,end_time")
    console.print(f"  [green][OK] availability_current: {len(payloads_current)} rows upserted[/green]")

    supa_insert("availability_snapshots", payloads_snapshot)
    console.print(f"  [green][OK] availability_snapshots: {len(payloads_snapshot)} rows inserted[/green]")

    console.print(f"\n[bold green]Done.[/bold green]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
