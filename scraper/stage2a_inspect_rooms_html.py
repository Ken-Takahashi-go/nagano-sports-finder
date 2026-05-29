"""
Stage 2-A 補助: stage2_rooms.html の構造を詳細解析
目的: 空きカレンダーがHTMLのどこに、どんな形式で入っているかを特定
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table

SCRIPT_DIR = Path(__file__).parent
HTML_PATH = SCRIPT_DIR / "outputs" / "stage2_rooms.html"

console = Console()


def main() -> int:
    if not HTML_PATH.exists():
        console.print(f"[red]ERROR: {HTML_PATH} がありません。先にstage2aを実行してください[/red]")
        return 1

    html = HTML_PATH.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    console.print(f"[bold green]Stage 2-A 補助: rooms HTML構造解析[/bold green]")
    console.print(f"ファイル: {HTML_PATH.relative_to(SCRIPT_DIR)}")
    console.print(f"サイズ: {len(html):,} bytes")
    console.print()

    # 1. HTML全体の要素別カウント
    tag_counts = Counter(t.name for t in soup.find_all())
    console.print("[bold]主要タグ件数:[/bold]")
    for tag in ["form", "table", "tr", "td", "div", "a", "button", "input", "select", "option", "span", "ul", "li"]:
        n = tag_counts.get(tag, 0)
        if n > 0:
            console.print(f"  {tag:8s}: {n}")
    console.print()

    # 2. クラス名出現頻度 (top 20)
    classes = Counter()
    for el in soup.find_all(class_=True):
        for c in el.get("class", []):
            classes[c] += 1
    console.print("[bold]頻出CSSクラス (top 15):[/bold]")
    for cls, count in classes.most_common(15):
        console.print(f"  [cyan]{cls}[/cyan]: {count}")
    console.print()

    # 3. フォーム解析
    forms = soup.find_all("form")
    console.print(f"[bold]フォーム解析 (全{len(forms)}個):[/bold]")
    for i, form in enumerate(forms[:5], 1):
        action = form.get("action", "")
        method = form.get("method", "get")
        inputs = form.find_all(["input", "select"])
        input_summary = ", ".join(
            f"{inp.get('name', '?')}={inp.get('value', '?')[:20]}"
            for inp in inputs[:5] if inp.get("type") != "submit"
        )
        console.print(f"  [{i}] {method.upper()} {action}")
        console.print(f"      inputs: {input_summary}")
    if len(forms) > 5:
        console.print(f"  ... 他 {len(forms) - 5} フォーム")
    console.print()

    # 4. 日付・時刻パターンの検出
    date_patterns = [
        (r"\d{4}[/-]\d{1,2}[/-]\d{1,2}", "YYYY-MM-DD形式"),
        (r"\d{1,2}月\d{1,2}日", "MM月DD日 形式"),
        (r"\d{1,2}:\d{2}", "HH:MM 形式"),
        (r"\d{1,2}時\d{0,2}分?", "HH時 形式"),
    ]
    console.print("[bold]日付/時刻パターン検出:[/bold]")
    for pattern, label in date_patterns:
        matches = re.findall(pattern, html)
        unique = list(set(matches))[:10]
        console.print(f"  {label}: {len(matches)}件 (ユニーク {len(set(matches))}件)")
        if unique:
            console.print(f"    例: {', '.join(unique[:8])}")
    console.print()

    # 5. 「空き」「満」「予約」キーワード周辺の抜粋
    console.print("[bold]空き/満キーワード周辺の文字列(各3件まで):[/bold]")
    for kw in ["空き", "空", "満", "△", "○", "×", "予約可", "予約", "受付"]:
        if kw in html:
            count = html.count(kw)
            # 最初の出現箇所の前後抜粋
            idx = html.find(kw)
            snippet = re.sub(r"\s+", " ", html[max(0, idx-30):idx+30])
            console.print(f"  '[yellow]{kw}[/yellow]' ({count}回): ...{snippet}...")
    console.print()

    # 6. h1〜h3 ヘッダー
    console.print("[bold]ヘッダー(h1-h3):[/bold]")
    for level in ["h1", "h2", "h3"]:
        for el in soup.find_all(level):
            text = el.get_text(strip=True)
            if text:
                console.print(f"  <{level}> {text[:80]}")
    console.print()

    # 7. リンク先(href) を分類
    links = [a.get("href", "") for a in soup.find_all("a")]
    link_patterns = Counter()
    for href in links:
        if not href:
            continue
        # 数字部分をマスク
        masked = re.sub(r"\d+", "N", href)
        link_patterns[masked] += 1
    console.print("[bold]リンクパターン (上位10):[/bold]")
    for pattern, count in link_patterns.most_common(10):
        console.print(f"  [{count:3d}回] {pattern}")
    console.print()

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
