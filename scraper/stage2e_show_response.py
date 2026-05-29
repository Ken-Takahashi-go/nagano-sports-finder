"""
Stage 2-E 補助: stage2e_*.txt の中身を表示して何が返ってきたか確認する
"""
from pathlib import Path
from bs4 import BeautifulSoup
from rich.console import Console

SCRIPT_DIR = Path(__file__).parent
OUTPUTS = SCRIPT_DIR / "outputs"
console = Console()

# stage2e で生成された .txt ファイルを全部見る
txts = sorted(OUTPUTS.glob("stage2e_*.txt"))

if not txts:
    console.print("[red]ERROR: stage2e_*.txt が無い。先にstage2eを実行してください[/red]")
    raise SystemExit(1)

for path in txts:
    console.print(f"\n[bold cyan]=== {path.name} ({path.stat().st_size:,} bytes) ===[/bold cyan]")
    content = path.read_text(encoding="utf-8")

    # HTMLっぽければパースして要点抽出
    try:
        soup = BeautifulSoup(content, "lxml")
        title = soup.title.get_text(strip=True) if soup.title else "(no title)"
        console.print(f"  [yellow]title[/yellow]: {title}")

        # body の主要テキスト
        body_text = soup.get_text(separator=" ", strip=True)
        body_text = " ".join(body_text.split())  # 連続空白圧縮
        console.print(f"  [yellow]text[/yellow]: {body_text[:300]}")

        # リダイレクト先 / canonical
        for tag_name in ["meta", "link"]:
            for tag in soup.find_all(tag_name):
                http_equiv = tag.get("http-equiv", "").lower()
                rel = tag.get("rel", [])
                if http_equiv == "refresh" or "canonical" in rel:
                    console.print(f"  [yellow]redirect/canonical[/yellow]: {tag}")
    except Exception:
        # 生で先頭表示
        console.print(content[:500])
