"""
Stage 2-B: 「空室カレンダー」ボタンの遷移先URLを特定し、
           16コートのroom_idを抽出する

入力: outputs/stage2_facility_detail.html, stage2_rooms.html
出力: コンソール表示 + outputs/stage2_room_list.json
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table

SCRIPT_DIR = Path(__file__).parent
OUTPUTS = SCRIPT_DIR / "outputs"

console = Console()


def analyze(html_path: Path, label: str) -> None:
    console.print(f"\n[bold cyan]=== {label} ({html_path.name}) ===[/bold cyan]")
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    # 「空室カレンダー」を含むリンク・ボタン・フォームを全て探す
    console.print("\n[bold]「空室カレンダー」関連の要素:[/bold]")

    # リンク
    for a in soup.find_all("a"):
        text = (a.get_text() or "").strip()
        if "空室" in text or "カレンダー" in text or "予約" in text:
            href = a.get("href", "")
            console.print(f"  <a> [yellow]{text}[/yellow] → {href}")

    # フォーム
    for form in soup.find_all("form"):
        action = form.get("action", "")
        method = (form.get("method") or "GET").upper()
        # フォーム内のボタンとテキスト
        btns = form.find_all(["button", "input"])
        btn_texts = []
        for b in btns:
            if b.name == "button":
                btn_texts.append((b.get_text() or "").strip())
            elif b.get("type") == "submit":
                btn_texts.append(b.get("value", ""))
        for txt in btn_texts:
            if "カレンダー" in txt or "空室" in txt or "探す" in txt:
                console.print(f"  <form {method}> action={action}")
                console.print(f"    button: [yellow]{txt}[/yellow]")
                # フォーム内のhidden/select値も列挙
                for inp in form.find_all(["input", "select"]):
                    if inp.get("type") == "submit":
                        continue
                    name = inp.get("name", "?")
                    value = inp.get("value", "")
                    console.print(f"    field: {name}={value}")

    # コート(room)へのリンク
    console.print("\n[bold]/rooms/N リンク(個別コート):[/bold]")
    rooms = []
    seen_urls = set()
    for a in soup.find_all("a"):
        href = a.get("href", "")
        m = re.match(r"^/rooms/(\d+)$", href)
        if m and href not in seen_urls:
            seen_urls.add(href)
            room_id = m.group(1)
            text = (a.get_text() or "").strip()
            text = re.sub(r"\s+", " ", text)
            rooms.append({"room_id": room_id, "name": text, "url": href})

    if rooms:
        table = Table(show_lines=False)
        table.add_column("room_id", style="green", no_wrap=True)
        table.add_column("コート名", style="white")
        for r in rooms[:20]:
            table.add_row(r["room_id"], r["name"])
        console.print(table)
        if len(rooms) > 20:
            console.print(f"[dim]他 {len(rooms) - 20} 件[/dim]")
        console.print(f"\n→ [bold]計 {len(rooms)} コート見つかりました[/bold]")
    else:
        console.print("  [red]見つかりません[/red]")

    # その他のリンク URL パターン
    console.print("\n[bold]/rooms? 以外のリンクパターン上位:[/bold]")
    from collections import Counter
    patterns = Counter()
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if href and not href.startswith("#"):
            masked = re.sub(r"\d+", "N", href)
            patterns[masked] += 1
    for pattern, count in patterns.most_common(10):
        console.print(f"  [{count:3d}回] {pattern}")

    return rooms


def main() -> int:
    console.print(f"[bold green]Stage 2-B: 空室カレンダーURL特定 + コート一覧抽出[/bold green]")

    facility_html = OUTPUTS / "stage2_facility_detail.html"
    rooms_html = OUTPUTS / "stage2_rooms.html"

    if not facility_html.exists() or not rooms_html.exists():
        console.print(f"[red]ERROR: HTMLファイルがありません。先にstage2aを実行してください[/red]")
        return 1

    rooms_from_detail = analyze(facility_html, "施設詳細ページ")
    rooms_from_list = analyze(rooms_html, "rooms一覧ページ")

    # ユニーク化
    all_rooms_dict = {}
    for r in (rooms_from_detail or []) + (rooms_from_list or []):
        all_rooms_dict[r["room_id"]] = r
    all_rooms = sorted(all_rooms_dict.values(), key=lambda r: int(r["room_id"]))

    # JSON保存
    out_path = OUTPUTS / "stage2_room_list.json"
    out_path.write_text(
        json.dumps(all_rooms, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    console.print(f"\n[green]保存: {out_path.relative_to(SCRIPT_DIR)}[/green]")
    console.print(f"\n[bold]✓ ユニークなコート数: {len(all_rooms)}[/bold]")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
