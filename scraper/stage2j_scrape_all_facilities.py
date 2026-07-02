"""
Stage 2-J: machikagi_facility_id が紐付いた全施設の空き状況を取得・保存

Stage 2-I のロジックを再利用しつつ、27施設をループ処理。
1施設エラーでも継続 (fault-tolerant)。最後にサマリー表示。

使い方:
  python stage2j_scrape_all_facilities.py
  python stage2j_scrape_all_facilities.py --days 14
  python stage2j_scrape_all_facilities.py --dry-run    # DB書き込みなし

所要時間目安:
  27施設 × 平均6コート × 15秒 = 約40分
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

SCRIPT_DIR = Path(__file__).parent
load_dotenv(SCRIPT_DIR / ".env")

# stage2i のロジックを再利用するためインポート
from stage2i_scrape_one_facility import (
    BASE_URL, SETTING_ID, INTERVAL, USER_AGENT, SCRAPER_VERSION,
    SUPABASE_URL, SUPABASE_KEY,
    AggregatedSlot, Room, Slot,
    aggregate, fetch_events, fetch_room_list, parse_event_to_slot,
    supa_get, supa_insert, supa_patch, supa_upsert,
)

console = Console()


def process_facility(
    client: httpx.Client,
    facility: dict,
    start_date: str,
    end_date: str,
    dry_run: bool,
) -> tuple[int, int]:
    """
    1施設の処理。
    戻り値: (取得room数, upsertした集約スロット数)
    """
    fid = facility["id"]
    code = facility["facility_code"]
    name = facility["facility_name"]
    mid = facility["machikagi_facility_id"]

    # rooms 取得
    rooms = fetch_room_list(client, mid)
    if not rooms:
        console.print(f"  [yellow]rooms が取れなかった (machikagi={mid})。スキップ[/yellow]")
        return 0, 0
    console.print(f"  rooms: {len(rooms)}件")
    time.sleep(INTERVAL)

    # 各 room の events
    slots_per_room: dict[int, list[Slot]] = {}
    for j, room in enumerate(rooms):
        try:
            events = fetch_events(client, room.machikagi_room_id, start_date, end_date)
            slots = [parse_event_to_slot(e) for e in events]
            slots_per_room[room.machikagi_room_id] = slots
            console.print(
                f"    ({j+1}/{len(rooms)}) room {room.machikagi_room_id}: "
                f"{len(slots)} slots, 空き {sum(1 for s in slots if s.status == '空き')}"
            )
        except Exception as e:
            console.print(f"    [red]room {room.machikagi_room_id} fetch失敗: {e}[/red]")
        if j < len(rooms) - 1:
            time.sleep(INTERVAL)

    if not slots_per_room:
        console.print(f"  [yellow]全room取得失敗。スキップ[/yellow]")
        return len(rooms), 0

    # 集約
    aggregated = aggregate(slots_per_room)

    # 集計表示
    avail = sum(1 for a in aggregated if a.availability_status == "空き")
    partial = sum(1 for a in aggregated if a.availability_status == "一部空き")
    full = sum(1 for a in aggregated if a.availability_status == "満")
    console.print(
        f"  集約後: {len(aggregated)}スロット "
        f"(空き {avail} / 一部 {partial} / 満 {full})"
    )

    # upsert
    if not dry_run:
        now = datetime.now(timezone.utc).isoformat()
        payloads_current = []
        payloads_snapshot = []
        for a in aggregated:
            common = {
                "facility_id": fid,
                "court_name": "",
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
            payloads_current.append({**common, "last_checked_at": now})
            payloads_snapshot.append({**common, "snapshot_at": now})

        supa_upsert(
            "availability_current", payloads_current,
            on_conflict="facility_id,court_name,target_date,start_time,end_time",
        )
        supa_insert("availability_snapshots", payloads_snapshot)
        console.print(f"  [green]✓ Supabaseに{len(aggregated)}行投入[/green]")

    return len(rooms), len(aggregated)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7, help="取得日数")
    ap.add_argument("--dry-run", action="store_true", help="DB書き込みスキップ")
    args = ap.parse_args()

    console.print(f"[bold green]Stage 2-J: 全施設スクレイパー[/bold green]")
    if args.dry_run:
        console.print(f"[yellow]DRY RUN モード[/yellow]")
    console.print()

    # 環境変数サニティチェック (GitHub Actionsでの早期発見用)
    console.print(f"[dim]USER_AGENT     = {repr(USER_AGENT)[:120]}[/dim]")
    console.print(f"[dim]BASE_URL       = {BASE_URL!r}[/dim]")
    console.print(f"[dim]SUPABASE_URL   = {'(set)' if (SUPABASE_URL or '').startswith('https://') else '(MISSING!)'}[/dim]")
    console.print(f"[dim]SUPABASE_KEY   = {'(set)' if SUPABASE_KEY else '(MISSING!)'}[/dim]")
    console.print()

    # 対象施設取得 (machikagi_facility_id が紐付いた全施設)
    facilities = supa_get("facilities", {
        "machikagi_facility_id": "not.is.null",
        "order": "facility_code",
        "select": "id,facility_code,facility_name,machikagi_facility_id",
    })
    console.print(f"対象: [bold]{len(facilities)}施設[/bold]")
    console.print(f"取得日数: {args.days}日\n")

    # ジョブログ開始
    job_started_at = datetime.now(timezone.utc).isoformat()
    job_row = supa_insert("scraping_jobs", [{
        "municipality": "長野市",
        "scraper_name": "machikagi_stage2j",
        "scraper_version": SCRAPER_VERSION,
        "started_at": job_started_at,
        "status": "running",
    }])
    job_id = job_row["id"] if job_row else None

    start_date = date.today().isoformat()
    end_date = (date.today() + timedelta(days=args.days)).isoformat()

    success: list[str] = []
    failed: list[tuple[str, str]] = []
    total_rooms = 0
    total_slots = 0

    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ja-JP,ja;q=0.9",
    }

    overall_start = time.time()

    try:
        with httpx.Client(headers=headers, follow_redirects=True) as client:
            for i, facility in enumerate(facilities):
                code = facility["facility_code"]
                name = facility["facility_name"]
                mid = facility["machikagi_facility_id"]

                elapsed = int(time.time() - overall_start)
                console.print(
                    f"\n[bold cyan][{i+1}/{len(facilities)}] {code} {name[:30]} (machikagi={mid})[/bold cyan]"
                    f"  [dim](経過 {elapsed//60}m{elapsed%60}s)[/dim]"
                )

                try:
                    rooms, slots = process_facility(client, facility, start_date, end_date, args.dry_run)
                    total_rooms += rooms
                    total_slots += slots
                    success.append(code)
                except Exception as e:
                    msg = str(e)[:200]
                    console.print(f"  [red]ERROR: {msg}[/red]")
                    failed.append((code, msg))

                # 次の施設へ
                if i < len(facilities) - 1:
                    time.sleep(INTERVAL)

    except KeyboardInterrupt:
        console.print(f"\n[yellow]中断されました[/yellow]")
    finally:
        # サマリー表示
        elapsed = int(time.time() - overall_start)
        console.print(f"\n[bold]=== サマリー ===[/bold]")
        console.print(f"  所要時間: {elapsed//60}分{elapsed%60}秒")
        console.print(f"  成功: [green]{len(success)}施設[/green]")
        console.print(f"  失敗: [red]{len(failed)}施設[/red]")
        console.print(f"  取得rooms合計: {total_rooms}")
        console.print(f"  upsertスロット合計: {total_slots}")

        if failed:
            console.print(f"\n[bold red]失敗施設:[/bold red]")
            for code, msg in failed:
                console.print(f"  {code}: {msg[:80]}")

        # ジョブ完了ログ
        if job_id:
            supa_patch("scraping_jobs", {"id": f"eq.{job_id}"}, {
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "status": "success" if not failed else "partial",
                "records_fetched": total_slots,
                "error_message": (
                    "; ".join(f"{c}: {m[:50]}" for c, m in failed[:5])
                    if failed else None
                ),
            })

    return 0


if __name__ == "__main__":
    sys.exit(main())
