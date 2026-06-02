"""
塩尻市の施設を DB 新規登録 + webR ID 紐付け (REST)

入力: outputs/shiojiri_S1_facilities.json (probe で取得した 7施設)
  アリーナ(体育館)3 / テニスコート2 / サッカー場2

facility_code 採番:
  SIO-GYM-00x (アリーナ) / SIO-TEN-00x / SIO-SOC-00x
external_system = 'shiojiri_webR' (松本 matsumoto_webR と区別)

データ確度:
  webR の施設名・IDのみ確定 → data_confidence='C'
  設備/路面/料金は後で公式サイトから補強 (松本の seed 相当は次段階)
"""
from __future__ import annotations

import io
import json
import os
import sys
from collections import defaultdict
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
EXTERNAL_SYSTEM = "shiojiri_webR"
OFFICIAL_URL = "https://www.city.shiojiri.lg.jp/"
RESERVATION_URL = "https://www.pf489.com/shiojiri/WebR/"
INPUT_JSON = SCRIPT_DIR / "outputs" / "shiojiri_S1_facilities.json"

# 施設種別 → (facility_code prefix, sports, indoor/outdoor)
TYPE_MAP = {
    "アリーナ": ("SIO-GYM", ["basketball", "volleyball", "multi"], "屋内"),
    "テニスコート": ("SIO-TEN", ["tennis"], "屋外"),
    "サッカー場": ("SIO-SOC", ["soccer", "futsal", "multi"], "屋外"),
}
NOTES = "塩尻市公共施設予約システム(webR)より取得。設備・料金・路面等の詳細は要確認(簡易登録)。"


def _headers(extra: dict | None = None) -> dict:
    h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    if extra:
        h.update(extra)
    return h


def main() -> int:
    if not SUPABASE_URL or not SUPABASE_KEY:
        console.print("[red]ERROR: SUPABASE 認証情報 未設定[/red]")
        return 1
    if not INPUT_JSON.exists():
        console.print(f"[red]入力なし: {INPUT_JSON} (先に stageS1_probe.py を実行)[/red]")
        return 1

    facs = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    console.print(f"[bold green]塩尻市 施設登録 ({len(facs)}件)[/bold green]\n")

    fac_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/facilities"
    sport_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/facility_sports"

    # 種別ごとに連番採番
    counters: dict[str, int] = defaultdict(int)
    ok, fail = 0, 0
    for f in facs:
        stype = f["shisetsu_type"]
        ext_id = f["value"]
        name = f["name"].rstrip("（(").strip()  # 末尾の開き括弧切れを除去
        if stype not in TYPE_MAP:
            console.print(f"  [yellow]skip: 未対応種別 {stype} ({name})[/yellow]")
            continue
        prefix, sports, io_type = TYPE_MAP[stype]
        counters[prefix] += 1
        code = f"{prefix}-{counters[prefix]:03d}"

        row = {
            "facility_code": code,
            "facility_name": name,
            "municipality": "塩尻市",
            "indoor_outdoor": io_type,
            "surface_type": "要確認",
            "booking_method": "Web",
            "external_system": EXTERNAL_SYSTEM,
            "external_facility_id": ext_id,
            "data_confidence": "C",
            "official_url": OFFICIAL_URL,
            "reservation_url": RESERVATION_URL,
            "notes": NOTES,
        }
        r = httpx.post(fac_url, params={"on_conflict": "facility_code"},
                       headers=_headers({"Content-Type": "application/json",
                                         "Prefer": "resolution=merge-duplicates,return=representation"}),
                       json=[row], timeout=30.0)
        if r.status_code >= 400:
            console.print(f"  [red][NG] {code} ({name}): {r.status_code} {r.text[:150]}[/red]")
            fail += 1
            continue
        fac_id = r.json()[0]["id"]
        sport_rows = [{"facility_id": fac_id, "sport": s} for s in sports]
        httpx.post(sport_url,
                   headers=_headers({"Content-Type": "application/json",
                                     "Prefer": "resolution=ignore-duplicates,return=minimal"}),
                   json=sport_rows, timeout=30.0)
        console.print(f"  [green][OK] {code} ({name}) <- webR {ext_id} / {','.join(sports)}[/green]")
        ok += 1

    console.print(f"\n[bold]結果: 登録 {ok} / 失敗 {fail}[/bold]")

    # 確認
    chk = httpx.get(fac_url, params={
        "municipality": "eq.塩尻市", "select": "facility_code,external_facility_id",
    }, headers=_headers(), timeout=30.0).json()
    console.print(f"[cyan]塩尻市 登録済: {len(chk)}件 (全て webR ID 紐付け済)[/cyan]")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
