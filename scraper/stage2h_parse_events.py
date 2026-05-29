"""
Stage 2-H: 取得した reservation_events.json をパースして
空き状況スロットに変換する

入力: outputs/stage2g_events.json (Stage 2-G の成果物)
出力:
  - コンソールに集計と日別空き状況テーブル表示
  - outputs/stage2h_parsed_slots.json (構造化済データ)
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

SCRIPT_DIR = Path(__file__).parent
INPUT_PATH = SCRIPT_DIR / "outputs" / "stage2g_events.json"
OUTPUT_PATH = SCRIPT_DIR / "outputs" / "stage2h_parsed_slots.json"

console = Console()


@dataclass
class Slot:
    """空き状況スロット (1つの時間枠)"""
    date: str          # YYYY-MM-DD
    start_time: str    # HH:MM
    end_time: str      # HH:MM
    status: str        # '空き' / '満' / '不明'
    fee_yen: int | None  # 円 (空きのみ)
    booking_method: str | None  # '先着' / '抽選' など (空きのみ)
    raw_title: str     # 元のtitle (デバッグ用)


def parse_event(event: dict) -> Slot:
    """
    1イベントを Slot に変換

    判定ルール:
      - color が None → 空き (titleに料金情報が入る)
      - color が "white" → 満 (titleが '×')
      - それ以外 → 不明
    """
    # 開始・終了時刻のパース
    start_dt = datetime.fromisoformat(event["start"])
    end_dt = datetime.fromisoformat(event["end"])
    date = start_dt.date().isoformat()
    start_time = start_dt.strftime("%H:%M")
    end_time = end_dt.strftime("%H:%M")

    title = event.get("title", "")
    color = event.get("color")

    # 料金パース (¥ U+00A5 / ￥ U+FFE5 の両方対応)
    fee_match = re.search(r"[¥￥]([\d,]+)", title)
    fee_yen = int(fee_match.group(1).replace(",", "")) if fee_match else None

    # 予約方式
    method = None
    if "先着" in title:
        method = "先着"
    elif "抽選" in title:
        method = "抽選"

    # ステータス判定 (color優先・最も確実)
    if color is None:
        status = "空き"
    elif color == "white":
        status = "満"
    else:
        status = "不明"

    return Slot(
        date=date,
        start_time=start_time,
        end_time=end_time,
        status=status,
        fee_yen=fee_yen,
        booking_method=method,
        raw_title=title,
    )


def main() -> int:
    console.print(f"[bold green]Stage 2-H: events.json をパースして空き状況を抽出[/bold green]\n")

    if not INPUT_PATH.exists():
        console.print(f"[red]ERROR: {INPUT_PATH} がありません。stage2gを先に実行してください[/red]")
        return 1

    events = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    console.print(f"入力イベント数: [bold]{len(events)}[/bold]\n")

    # パース
    slots: list[Slot] = [parse_event(e) for e in events]

    # 集計
    status_count = defaultdict(int)
    for s in slots:
        status_count[s.status] += 1
    console.print("[bold]ステータス別件数:[/bold]")
    for status, count in sorted(status_count.items()):
        console.print(f"  {status}: {count}件")
    console.print()

    # 日別集計
    by_date: dict[str, list[Slot]] = defaultdict(list)
    for s in slots:
        by_date[s.date].append(s)

    console.print(f"[bold]日別空き状況テーブル (先頭10日):[/bold]")
    table = Table(show_lines=False)
    table.add_column("日付", style="cyan", no_wrap=True)
    table.add_column("総枠", justify="right")
    table.add_column("空き", justify="right", style="green")
    table.add_column("満", justify="right", style="red")
    table.add_column("空き率", justify="right")
    table.add_column("料金帯(円)", style="yellow")

    sorted_dates = sorted(by_date.keys())
    for d in sorted_dates[:10]:
        day_slots = by_date[d]
        total = len(day_slots)
        available = sum(1 for s in day_slots if s.status == "空き")
        full = sum(1 for s in day_slots if s.status == "満")
        ratio = f"{available / total * 100:.0f}%" if total else "-"
        fees = sorted({s.fee_yen for s in day_slots if s.fee_yen})
        fee_str = "/".join(f"¥{f:,}" for f in fees) if fees else "-"
        table.add_row(d, str(total), str(available), str(full), ratio, fee_str)

    console.print(table)
    console.print()

    if len(sorted_dates) > 10:
        console.print(f"[dim]...他 {len(sorted_dates) - 10}日分のデータあり[/dim]\n")

    # 空きスロットのサンプル表示
    available_slots = [s for s in slots if s.status == "空き"]
    if available_slots:
        console.print(f"[bold]空きスロット サンプル(先頭5件):[/bold]")
        sample_table = Table(show_lines=False)
        sample_table.add_column("日付", style="cyan")
        sample_table.add_column("時間", style="white")
        sample_table.add_column("料金", style="yellow")
        sample_table.add_column("予約方式", style="green")
        for s in available_slots[:5]:
            sample_table.add_row(
                s.date,
                f"{s.start_time}-{s.end_time}",
                f"¥{s.fee_yen:,}" if s.fee_yen else "-",
                s.booking_method or "-",
            )
        console.print(sample_table)
        console.print()

    # JSON保存
    OUTPUT_PATH.write_text(
        json.dumps([asdict(s) for s in slots], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    console.print(f"[green]✓ 保存: {OUTPUT_PATH.relative_to(SCRIPT_DIR)}[/green]")
    console.print()
    console.print(f"[bold green]✓ パーサー完成。次は Stage 2-I (全16コート×30日 + Supabase投入)[/bold green]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
