"""
Stage 2-I: 1施設の全コートの空き状況を取得 → 集約 → Supabaseに保存

PoC として南長野運動公園テニスコート(NAG-TEN-019, machikagi=84, 16コート)で動作確認。
うまく動いたら stage2j で全施設に拡張する。

フロー:
  1. Supabaseから facility (machikagi_facility_id付き) を取得
  2. machikagi の /rooms?facility_id=X からコート一覧取得
  3. 各コートの /rooms/N/reservation_events.json を取得
  4. (date, time_slot) ごとに集約
  5. availability_current にUPSERT + availability_snapshots にINSERT
  6. scraping_jobs にログ記録

使い方:
  python stage2i_scrape_one_facility.py
  python stage2i_scrape_one_facility.py --facility-code NAG-TEN-018 --days 14
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

SCRIPT_DIR = Path(__file__).parent
load_dotenv(SCRIPT_DIR / ".env")

def _ascii_safe(s: str | None) -> str:
    """HTTPヘッダー用にASCII safe化 (httpx は ヘッダーをasciiで送るため)"""
    if s is None:
        return ""
    # BOM除去 + 前後空白除去 + 非ASCII除去
    cleaned = str(s).replace("﻿", "").strip()
    return cleaned.encode("ascii", errors="ignore").decode("ascii")


# 設定
BASE_URL = _ascii_safe(os.getenv("MACHIKAGI_BASE_URL", "https://city.nagano.nagano.machikagi-remote.jp"))
SUPABASE_URL = _ascii_safe(os.getenv("SUPABASE_URL"))
SUPABASE_KEY = _ascii_safe(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
SCRAPER_NAME = _ascii_safe(os.getenv("SCRAPER_NAME", "NaganoSportsFinder"))
SCRAPER_VERSION = _ascii_safe(os.getenv("SCRAPER_VERSION", "0.1.0"))
SCRAPER_CONTACT = _ascii_safe(os.getenv("SCRAPER_CONTACT", "contact@example.com"))
INTERVAL = int(os.getenv("REQUEST_INTERVAL_SECONDS", "15"))
SETTING_ID = "84"  # 基本利用

USER_AGENT = _ascii_safe(
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    f"AppleWebKit/537.36 (KHTML, like Gecko) "
    f"Chrome/120.0.0.0 Safari/537.36 "
    f"{SCRAPER_NAME}/{SCRAPER_VERSION} (+{SCRAPER_CONTACT})"
)

console = Console()


# ===== データ構造 =====
@dataclass
class Room:
    machikagi_room_id: int
    name: str


@dataclass
class Slot:
    date: str
    start_time: str
    end_time: str
    status: str       # 空き / 満 / 不明
    fee_yen: int | None
    booking_method: str | None


@dataclass
class AggregatedSlot:
    target_date: str
    start_time: str
    end_time: str
    availability_status: str   # 空き / 一部空き / 満
    available_court_count: int
    total_court_count: int
    fee_min_yen: int | None
    fee_max_yen: int | None


# ===== Supabase クライアント =====
def supa_get(path: str, params: dict | None = None) -> list[dict]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        console.print("[red]ERROR: .env に SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY を設定してください[/red]")
        sys.exit(1)
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{path}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    r = httpx.get(url, params=params, headers=headers, timeout=30.0)
    r.raise_for_status()
    return r.json()


def supa_upsert(path: str, rows: list[dict], on_conflict: str | None = None) -> None:
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{path}"
    params = {"on_conflict": on_conflict} if on_conflict else {}
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    r = httpx.post(url, params=params, headers=headers, json=rows, timeout=60.0)
    if r.status_code >= 400:
        console.print(f"[red]upsert error {r.status_code}: {r.text[:300]}[/red]")
        r.raise_for_status()


def supa_insert(path: str, rows: list[dict]) -> dict | None:
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    r = httpx.post(url, headers=headers, json=rows, timeout=60.0)
    if r.status_code >= 400:
        console.print(f"[red]insert error {r.status_code}: {r.text[:300]}[/red]")
        r.raise_for_status()
    data = r.json()
    return data[0] if isinstance(data, list) and data else None


def supa_patch(path: str, params: dict, payload: dict) -> None:
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    r = httpx.patch(url, params=params, headers=headers, json=payload, timeout=30.0)
    if r.status_code >= 400:
        console.print(f"[red]patch error {r.status_code}: {r.text[:300]}[/red]")
        r.raise_for_status()


# ===== machikagi 取得 =====
def fetch_room_list(client: httpx.Client, facility_id: int) -> list[Room]:
    url = f"{BASE_URL}/rooms"
    r = client.get(url, params={"facility_id": facility_id}, timeout=30.0)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    rooms: list[Room] = []
    seen: set[int] = set()
    for a in soup.find_all("a", href=True):
        m = re.match(r"^/rooms/(\d+)$", a["href"])
        if m:
            rid = int(m.group(1))
            if rid in seen:
                continue
            seen.add(rid)
            name = re.sub(r"\s+", " ", a.get_text(strip=True))
            rooms.append(Room(machikagi_room_id=rid, name=name))
    return rooms


def fetch_events(
    client: httpx.Client, room_id: int, start_date: str, end_date: str
) -> list[dict]:
    url = f"{BASE_URL}/rooms/{room_id}/reservation_events.json"
    params = {"start": start_date, "end": end_date, "requested_setting_id": SETTING_ID}
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": f"{BASE_URL}/rooms/{room_id}/reservation_calendar?requested_setting_id={SETTING_ID}",
    }
    r = client.get(url, params=params, headers=headers, timeout=30.0)
    r.raise_for_status()
    return r.json()


def parse_event_to_slot(event: dict) -> Slot:
    start_dt = datetime.fromisoformat(event["start"])
    end_dt = datetime.fromisoformat(event["end"])
    title = event.get("title", "")
    color = event.get("color")

    if color is None:
        status = "空き"
    elif color == "white":
        status = "満"
    else:
        status = "不明"

    fee_match = re.search(r"[¥￥]([\d,]+)", title)
    fee_yen = int(fee_match.group(1).replace(",", "")) if fee_match else None

    method = "先着" if "先着" in title else ("抽選" if "抽選" in title else None)

    return Slot(
        date=start_dt.date().isoformat(),
        start_time=start_dt.strftime("%H:%M"),
        end_time=end_dt.strftime("%H:%M"),
        status=status,
        fee_yen=fee_yen,
        booking_method=method,
    )


# ===== 集約 =====
def aggregate(slots_per_room: dict[int, list[Slot]]) -> list[AggregatedSlot]:
    """
    複数roomのslotsを (date, start_time, end_time) でグループ化
    """
    # 全room の slot を平坦化しながら、(time slot) -> [room_id ごとの状態]
    grouped: dict[tuple[str, str, str], list[Slot]] = defaultdict(list)
    for room_id, slots in slots_per_room.items():
        for s in slots:
            grouped[(s.date, s.start_time, s.end_time)].append(s)

    aggregated: list[AggregatedSlot] = []
    for (target_date, start_time, end_time), slots_here in grouped.items():
        total = len(slots_here)
        available = sum(1 for s in slots_here if s.status == "空き")
        if available == 0:
            status = "満"
        elif available == total:
            status = "空き"
        else:
            status = "一部空き"

        fees = [s.fee_yen for s in slots_here if s.fee_yen]
        fee_min = min(fees) if fees else None
        fee_max = max(fees) if fees else None

        aggregated.append(AggregatedSlot(
            target_date=target_date,
            start_time=start_time,
            end_time=end_time,
            availability_status=status,
            available_court_count=available,
            total_court_count=total,
            fee_min_yen=fee_min,
            fee_max_yen=fee_max,
        ))
    # 並び替え
    aggregated.sort(key=lambda a: (a.target_date, a.start_time))
    return aggregated


# ===== メイン =====
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--facility-code", default="NAG-TEN-019", help="DBの facility_code")
    ap.add_argument("--days", type=int, default=7, help="取得日数 (今日からN日先まで)")
    ap.add_argument("--dry-run", action="store_true", help="Supabaseへの書き込みをスキップ")
    args = ap.parse_args()

    console.print(f"[bold green]Stage 2-I: 1施設PoCスクレイパー[/bold green]")
    console.print(f"対象: facility_code={args.facility_code}, {args.days}日分")
    if args.dry_run:
        console.print(f"[yellow]DRY RUN: Supabase書き込みスキップ[/yellow]")
    console.print()

    # 1. DBから施設取得
    facilities = supa_get("facilities", {
        "facility_code": f"eq.{args.facility_code}",
        "select": "id,facility_code,facility_name,machikagi_facility_id"
    })
    if not facilities:
        console.print(f"[red]ERROR: facility_code='{args.facility_code}' がDBにない[/red]")
        return 1
    facility = facilities[0]
    mid = facility.get("machikagi_facility_id")
    if not mid:
        console.print(f"[red]ERROR: {args.facility_code} に machikagi_facility_id が未設定[/red]")
        return 1
    console.print(f"[bold]DB facility:[/bold] {facility['facility_name']} (id={facility['id']}, machikagi={mid})")
    console.print()

    # scraping_job 開始ログ
    job_started_at = datetime.now(timezone.utc).isoformat()
    job_row = supa_insert("scraping_jobs", [{
        "municipality": "長野市",
        "scraper_name": "machikagi_stage2i",
        "scraper_version": SCRAPER_VERSION,
        "started_at": job_started_at,
        "status": "running",
    }])
    job_id = job_row["id"] if job_row else None

    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Language": "ja-JP,ja;q=0.9",
        }
        with httpx.Client(headers=headers, follow_redirects=True) as client:
            # 2. machikagi rooms
            console.print(f"[cyan]GET /rooms?facility_id={mid}[/cyan]")
            rooms = fetch_room_list(client, mid)
            console.print(f"  → {len(rooms)}コート発見")
            time.sleep(INTERVAL)

            # 3. 各room の events
            start_date = date.today().isoformat()
            end_date = (date.today() + timedelta(days=args.days)).isoformat()
            slots_per_room: dict[int, list[Slot]] = {}

            for i, room in enumerate(rooms):
                console.print(f"[cyan]({i+1}/{len(rooms)}) GET events room_id={room.machikagi_room_id} ({room.name[:40]})[/cyan]")
                events = fetch_events(client, room.machikagi_room_id, start_date, end_date)
                slots = [parse_event_to_slot(e) for e in events]
                slots_per_room[room.machikagi_room_id] = slots
                console.print(f"  → {len(slots)} slots (空き: {sum(1 for s in slots if s.status == '空き')})")
                if i < len(rooms) - 1:
                    time.sleep(INTERVAL)

            # 4. 集約
            aggregated = aggregate(slots_per_room)
            console.print(f"\n[bold]集約後: {len(aggregated)}スロット[/bold]")
            # サンプル表示
            table = Table(title="集約結果サンプル(空き/一部空き 先頭8件)", show_lines=False)
            table.add_column("日付", style="cyan")
            table.add_column("時間", style="white")
            table.add_column("状態", style="white")
            table.add_column("空き/総", justify="right")
            table.add_column("料金", style="yellow")
            shown = 0
            for a in aggregated:
                if a.availability_status in ("空き", "一部空き") and shown < 8:
                    fee_str = (f"¥{a.fee_min_yen:,}" if a.fee_min_yen == a.fee_max_yen
                               else f"¥{a.fee_min_yen:,}-{a.fee_max_yen:,}")
                    table.add_row(a.target_date, f"{a.start_time}-{a.end_time}",
                                  a.availability_status, f"{a.available_court_count}/{a.total_court_count}",
                                  fee_str)
                    shown += 1
            console.print(table)

            # 5. Supabase upsert
            if not args.dry_run:
                now = datetime.now(timezone.utc).isoformat()
                facility_uuid = facility["id"]

                payloads_current = []
                payloads_snapshot = []
                for a in aggregated:
                    # 共通フィールド (両テーブル共通)
                    common = {
                        "facility_id": facility_uuid,
                        "target_date": a.target_date,
                        "start_time": a.start_time,
                        "end_time": a.end_time,
                        "availability_status": a.availability_status,
                        "available_court_count": a.available_court_count,
                        "total_court_count": a.total_court_count,
                        "fee_min_yen": a.fee_min_yen,
                        "fee_max_yen": a.fee_max_yen,
                        "source": "scrape",
                    }
                    # availability_current: last_checked_at
                    payloads_current.append({**common, "last_checked_at": now})
                    # availability_snapshots: snapshot_at
                    payloads_snapshot.append({**common, "snapshot_at": now})

                console.print(f"\n[cyan]Supabase に書き込み中 ({len(payloads_current)}行)...[/cyan]")
                supa_upsert(
                    "availability_current", payloads_current,
                    on_conflict="facility_id,target_date,start_time,end_time",
                )
                supa_insert("availability_snapshots", payloads_snapshot)
                console.print(f"[green]✓ 書き込み完了[/green]")

            # job 完了ログ
            if job_id:
                supa_patch("scraping_jobs", {"id": f"eq.{job_id}"}, {
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "status": "success",
                    "records_fetched": len(aggregated),
                })

            console.print(f"\n[bold green]✓ Stage 2-I 完了[/bold green]")
            return 0

    except Exception as e:
        console.print(f"[red]エラー: {e}[/red]")
        if job_id:
            supa_patch("scraping_jobs", {"id": f"eq.{job_id}"}, {
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error_message": str(e)[:500],
            })
        raise


if __name__ == "__main__":
    sys.exit(main())
