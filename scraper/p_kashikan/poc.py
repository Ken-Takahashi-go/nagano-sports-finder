"""
P-Kashikan httpx PoC: 須坂の空き状況を Playwright無し(httpx)で取得できるか実証

フロー:
  1. GET トップ → セッションCookie
  2. POST index.php (op=srch_mkt) → 検索画面のformから hidden取得
  3. POST index.php (Type/MokutekiCode/disp_span/searchBtn) → カレンダーHTML
  4. カレンダーの ○△× / 施設名 を解析できるか確認

成功すれば webR(Playwright必須)と違い httpx軽量スクレイピング可能。
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from webr_core import USER_AGENT, console  # noqa: E402

BASE = "https://k3.p-kashikan.jp/suzaka-city/"
OUT = Path(__file__).parent.parent / "outputs" / "pkashikan_poc_result.html"


def parse_form(html: str, name: str = "forma") -> dict:
    soup = BeautifulSoup(html, "lxml")
    form = soup.find("form", attrs={"name": name}) or soup.find("form")
    params = {}
    if form:
        for inp in form.find_all(["input", "select"]):
            n = inp.get("name")
            if n and inp.get("type") not in ("button", "submit"):
                params[n] = inp.get("value", "")
    return params


def main() -> int:
    console.print("[bold green]P-Kashikan httpx PoC (須坂)[/bold green]\n")
    client = httpx.Client(follow_redirects=True,
                          headers={"User-Agent": USER_AGENT}, timeout=30.0)

    # 1. トップ → Cookie
    r0 = client.get(BASE)
    console.print(f"[cyan]1. トップ[/cyan]: {r0.status_code}, cookies={list(client.cookies.keys())}")

    # 2. 検索画面 op=srch_mkt
    r1 = client.post(f"{BASE}index.php", data={"op": "srch_mkt"})
    console.print(f"[cyan]2. op=srch_mkt[/cyan]: {r1.status_code}, {len(r1.text):,}B")
    base_params = parse_form(r1.text)
    console.print(f"   form hidden: {list(base_params.keys())}")

    # 3. 体育館(Type=6 屋内スポーツ + Mokuteki=022 バスケ) を 1ヶ月表示で検索
    params = dict(base_params)
    params.update({
        "op": "srch_mkt",
        "Type": "6",
        "MokutekiCode": "022",
        "disp_span": "2",   # 1ヶ月
        "searchBtn": "検索",
    })
    console.print(f"[cyan]3. 検索POST[/cyan] params(主要)= "
                  f"Type=6,Mokuteki=022,disp_span=2 + hidden{len(base_params)}個")
    r2 = client.post(f"{BASE}index.php", data=params)
    console.print(f"   結果: {r2.status_code}, {len(r2.text):,}B")
    OUT.write_text(r2.text, encoding="utf-8")

    # 4. カレンダー解析
    soup = BeautifulSoup(r2.text, "lxml")
    text = soup.get_text()
    console.print(f"\n[bold]カレンダー記号:[/bold]")
    for sym in ["○", "△", "×", "空き", "休", "－"]:
        c = text.count(sym)
        if c:
            console.print(f"  '{sym}': {c}回")
    # 施設名候補 (リンク or 状態テーブル)
    tables = soup.find_all("table")
    console.print(f"\n  table数: {len(tables)}")
    # 施設名リンク (op=rsv系 or onclick)
    links = soup.find_all("a", onclick=True)
    rsv_links = [a for a in links if "rsv" in (a.get("onclick") or "").lower()
                 or "shisetsu" in (a.get("onclick") or "").lower()]
    console.print(f"  予約/施設リンク: {len(rsv_links)}")
    for a in rsv_links[:8]:
        console.print(f"    '{a.get_text(strip=True)[:24]}' onclick={a.get('onclick')[:50]}")

    # 状態セル候補 (class に aki/full/status 等)
    status_cells = soup.find_all("td", class_=lambda c: c and any(
        k in c for k in ["aki", "full", "status", "yoyaku", "close", "maru", "batu"]))
    console.print(f"  状態セル候補(class): {len(status_cells)}")
    if status_cells:
        for td in status_cells[:5]:
            console.print(f"    class={td.get('class')} text='{td.get_text(strip=True)[:10]}'")

    console.print(f"\n[green]→ HTML保存: {OUT.name}[/green]")
    ok = ("○" in text or "×" in text or len(status_cells) > 0)
    console.print(f"[bold {'green' if ok else 'red'}]"
                  f"{'[OK] httpxでカレンダー取得成功' if ok else '[NG] 空き状況が取れていない(パラメータ要調整)'}[/]")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
