"""
Stage M4: 空き状況カレンダーの解析 PoC (オフライン)

入力: outputs/matsumoto_M3_screenshots/04_after_click.html
       (Stage M3 で取得済の 1施設×13日のカレンダー)

出力:
  - outputs/matsumoto_M4_parsed.json
    {
      "facility_external_id": "202001",
      "facility_name": "総合体育館",
      "rooms": [
        {
          "room_id": "001",
          "room_name": "メインアリーナ（全面）",
          "slots": [
            {"date": "2026-05-31", "time_slot_id": "01",
             "status": "partial", "raw": "△",
             "value": "2026053100101   0"},
            ...
          ]
        },
        ...
      ]
    }

value エンコーディング (実検証で判明):
  YYYYMMDD + TTT + RR + "   " + F
  例: 2026053100101   0
       └─日付─┘└時間┘└部屋┘ 空白3 + フラグ
  - TTT: 全部屋共通 (= 1日1コマ扱い / カレンダーモード)
  - RR:  部屋枝番 (01=メインアリーナ全面, 02=A面, ..., 11=和室)
  - 時間別詳細は別モード (radioDisplayHorizontal) で取得必要

ステータスマップ:
  ○  -> available  (空き)
  △  -> partial    (一部空き)
  ×  -> full       (空きなし)
  －  -> unavailable (予約不可・休業時間)
  休館日 -> closed
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table

# Windows cp932 で絵文字/特殊記号が落ちるのを回避
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.parent
INPUT_HTML = SCRIPT_DIR / "outputs" / "matsumoto_M3_screenshots" / "04_after_click.html"
OUTPUT_JSON = SCRIPT_DIR / "outputs" / "matsumoto_M4_parsed.json"

console = Console()

# value pattern: YYYYMMDD + RRR + TT + spaces + flag
VALUE_PATTERN = re.compile(r"^(\d{8})(\d{3})(\d{2})\s*(\d*)$")

STATUS_MAP = {
    "○": "available",
    "△": "partial",
    "×": "full",
    "－": "unavailable",
    "ー": "unavailable",   # 長音バリエーション
    "－": "unavailable",
    "休館日": "closed",
}


def parse_value(value: str) -> dict | None:
    """value 文字列を分解 (修正: 中3桁=time_band, 末2桁=room_part)"""
    m = VALUE_PATTERN.match(value.strip())
    if not m:
        return None
    ymd, time_band, room_part, flag = m.groups()
    return {
        "date": f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}",
        "time_band_id": time_band,  # カレンダーモードでは "001" 固定
        "room_part_id": room_part,  # 部屋枝番 (01=全面, 02=A面, ...)
        "flag": flag,
    }


def normalize_status(text: str) -> str:
    t = (text or "").strip()
    return STATUS_MAP.get(t, "unknown")


def main() -> int:
    console.print("[bold green]Stage M4: カレンダー解析 PoC[/bold green]\n")

    if not INPUT_HTML.exists():
        console.print(f"[red]Input not found: {INPUT_HTML}[/red]")
        return 1

    html = INPUT_HTML.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    # ====================================================================
    # Step 1: 施設情報を抽出 (画面のヘッダーや title から)
    # ====================================================================
    title_h = soup.find(["h1", "h2", "h3"])
    page_title = soup.title.get_text(strip=True) if soup.title else ""
    console.print(f"[cyan]page title: {page_title}[/cyan]")

    # 年月情報を抽出 (例: "2026年 5月")
    year_month_text = soup.get_text()
    ym_match = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月", year_month_text)
    base_year = int(ym_match.group(1)) if ym_match else 2026

    # ====================================================================
    # Step 2: テーブル走査
    # ====================================================================
    tables = soup.find_all("table")
    console.print(f"[cyan]tables: {len(tables)}[/cyan]")

    # 一番大きい table（行数最多）を採用
    main_table = max(tables, key=lambda t: len(t.find_all("tr")), default=None)
    if not main_table:
        console.print("[red]No table found[/red]")
        return 1

    rows = main_table.find_all("tr")
    console.print(f"[cyan]main table rows: {len(rows)}[/cyan]\n")

    # ====================================================================
    # Step 3: 各 tr (=部屋) を解析
    # ====================================================================
    parsed_rooms: list[dict] = []
    seen_room_ids: dict[str, str] = {}  # room_id -> room_name

    for tr_idx, tr in enumerate(rows):
        room_name_cell = tr.find("td", class_="shisetsu")
        if not room_name_cell:
            continue  # ヘッダー行 or 無関係行
        room_name = room_name_cell.get_text(strip=True)

        slots: list[dict] = []
        for td in tr.find_all("td"):
            # 休館日セル
            if "closed" in (td.get("class") or []):
                # 休館日は日付不明（位置から推測必要）
                continue

            # チェックボックスを含むセル
            cb = td.find("input", attrs={"name": "checkdate"})
            if not cb:
                continue
            value = cb.get("value", "")
            parsed = parse_value(value)
            if not parsed:
                continue

            label = td.find("label")
            raw_status = label.get_text(strip=True) if label else ""
            status = normalize_status(raw_status)

            slots.append({
                "date": parsed["date"],
                "time_band_id": parsed["time_band_id"],
                "room_part_id": parsed["room_part_id"],
                "status": status,
                "raw": raw_status,
                "value": value,
            })

        if not slots:
            continue

        # この行の room_part_id は slots 全部で同一のはず
        room_part_id = slots[0]["room_part_id"]
        seen_room_ids[room_part_id] = room_name

        parsed_rooms.append({
            "room_part_id": room_part_id,
            "room_name": room_name,
            "slot_count": len(slots),
            "slots": slots,
        })

    # ====================================================================
    # Step 4: 結果サマリ
    # ====================================================================
    console.print(f"[bold green][OK] 部屋数: {len(parsed_rooms)}[/bold green]")
    console.print(f"[bold green][OK] 検出 room_id: {sorted(seen_room_ids.keys())}[/bold green]\n")

    # サマリテーブル
    summary = Table(title="部屋別 スロット集計")
    summary.add_column("part_id")
    summary.add_column("部屋名")
    summary.add_column("スロット数", justify="right")
    summary.add_column("○", justify="right", style="green")
    summary.add_column("△", justify="right", style="yellow")
    summary.add_column("×", justify="right", style="red")
    summary.add_column("－", justify="right", style="dim")

    for r in parsed_rooms:
        c = {"available": 0, "partial": 0, "full": 0, "unavailable": 0}
        for s in r["slots"]:
            if s["status"] in c:
                c[s["status"]] += 1
        summary.add_row(
            r["room_part_id"], r["room_name"], str(r["slot_count"]),
            str(c["available"]), str(c["partial"]), str(c["full"]), str(c["unavailable"]),
        )
    console.print(summary)

    # time_band の分布
    all_time_bands = set()
    for r in parsed_rooms:
        for s in r["slots"]:
            all_time_bands.add(s["time_band_id"])
    console.print(f"\n[bold]検出した time_band_id: {sorted(all_time_bands)}[/bold]")
    if len(all_time_bands) == 1:
        console.print(
            "[yellow][!] time_band は 1種類のみ (= カレンダーモード = 1日1コマ集約)[/yellow]"
        )
        console.print(
            "[yellow]   時間別詳細は radioDisplayHorizontal モードで取得 (次フェーズ)[/yellow]"
        )

    # ====================================================================
    # Step 5: JSON 保存
    # ====================================================================
    result = {
        "source_file": INPUT_HTML.name,
        "page_title": page_title,
        "facility_external_id": "202001",  # Stage M3 で選択した 総合体育館
        "facility_name_guess": "総合体育館",
        "base_year_month": ym_match.group(0) if ym_match else None,
        "room_count": len(parsed_rooms),
        "rooms": parsed_rooms,
    }
    OUTPUT_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    console.print(f"\n[bold green]-> 保存: {OUTPUT_JSON}[/bold green]")
    console.print(f"   ({OUTPUT_JSON.stat().st_size:,} bytes)\n")

    # ====================================================================
    # Step 6: サンプル出力
    # ====================================================================
    if parsed_rooms:
        first = parsed_rooms[0]
        console.print(f"[bold]サンプル: {first['room_name']} の最初5スロット[/bold]")
        for s in first["slots"][:5]:
            console.print(
                f"  {s['date']} band={s['time_band_id']} part={s['room_part_id']}: "
                f"{s['raw']:>2} ({s['status']}) value={s['value']!r}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
