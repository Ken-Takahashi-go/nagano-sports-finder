"""
Stage 1.5: machikagi_facility_list.json と Supabase の facilities テーブルを突合し、
machikagi_facility_id を紐付けるSQL UPDATE文を生成する。

入力:
  - outputs/machikagi_facility_list.json (Stage 1 の成果物)
  - Supabase API (.env の SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

出力:
  - outputs/matching_result.csv  人間確認用 (マッチ・候補・未マッチ)
  - outputs/update_machikagi_ids.sql  Supabaseに当てるSQL

マッチング戦略:
  1. 完全一致 (公式名 or 表示名)
  2. 部分一致 (machikagi名がDB名の部分文字列、または逆)
  3. キーワードベース (テニスコート/球技場/Uスタジアム等のキー名で照合)

使い方:
  python stage1_5_match_facilities.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

SCRIPT_DIR = Path(__file__).parent
load_dotenv(SCRIPT_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OUTPUTS_DIR = SCRIPT_DIR / "outputs"

console = Console()


@dataclass
class DbFacility:
    facility_code: str
    facility_name: str
    booking_method: str | None


@dataclass
class MachikagiFacility:
    machikagi_id: str
    facility_name: str


@dataclass
class Match:
    db: DbFacility
    machikagi: MachikagiFacility | None
    strategy: str  # 'exact' | 'partial' | 'keyword' | 'none'


# ----- ユーティリティ ------------------------------------------------
def normalize(name: str) -> str:
    """施設名を正規化: 全角・半角統一、記号除去、市営・長野市営の前置詞除去"""
    n = name
    # 全角英数→半角(ざっくり)
    n = n.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    # 「長野市営」「市営」を除去 (まちかぎ側に無いことが多い)
    n = re.sub(r"^(長野市営|市営)", "", n)
    # 「総合運動場」 / 「総合スポーツ」 を共通化
    n = n.replace("総合運動場", "運動公園").replace("総合運動場", "")
    # 空白・記号除去
    n = re.sub(r"[\s・()（）\-－―ー]", "", n)
    return n


def fetch_db_facilities() -> list[DbFacility]:
    """Supabase REST API から facilities を取得"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        console.print("[red]ERROR: .env に SUPABASE_URL と SUPABASE_SERVICE_ROLE_KEY を設定してください[/red]")
        sys.exit(1)

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/facilities"
    response = httpx.get(
        url,
        params={"select": "facility_code,facility_name,booking_method", "order": "facility_code"},
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return [DbFacility(**row) for row in response.json()]


def load_machikagi() -> list[MachikagiFacility]:
    path = OUTPUTS_DIR / "machikagi_facility_list.json"
    if not path.exists():
        console.print(f"[red]ERROR: {path} がありません。先に stage1 を実行してください。[/red]")
        sys.exit(1)
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        MachikagiFacility(machikagi_id=row["machikagi_id"], facility_name=row["facility_name"])
        for row in data
    ]


def match_facility(db: DbFacility, machikagi_list: list[MachikagiFacility]) -> Match:
    """1つのDB施設に対して machikagi側からマッチする施設を探す"""
    db_norm = normalize(db.facility_name)

    # Strategy 1: 完全一致 (正規化後)
    for m in machikagi_list:
        if normalize(m.facility_name) == db_norm:
            return Match(db, m, "exact")

    # Strategy 2: 部分一致 (どちらかが他方を含む)
    for m in machikagi_list:
        m_norm = normalize(m.facility_name)
        if m_norm and (m_norm in db_norm or db_norm in m_norm):
            return Match(db, m, "partial")

    # Strategy 3: キーワードベース (主要な特徴語で当たり)
    # 例: "南長野運動公園球技場" の キー単語は ["南長野", "球技場"] や ["Uスタジアム"]
    keywords_in_db = extract_keywords(db.facility_name)
    if keywords_in_db:
        best_match = None
        best_score = 0
        for m in machikagi_list:
            score = sum(1 for kw in keywords_in_db if kw in m.facility_name)
            if score > best_score:
                best_score = score
                best_match = m
        if best_match and best_score >= 2:
            return Match(db, best_match, "keyword")

    return Match(db, None, "none")


def extract_keywords(name: str) -> list[str]:
    """施設名から特徴的なキーワードを抽出"""
    keywords = []
    # 地名(漢字2-4字+「町」「公園」「広場」「テニス」「Uスタ」等)
    # 簡易実装: 「長野市営」を除いた残りを2字ずつ取る
    cleaned = re.sub(r"^(長野市営|市営)", "", name)
    cleaned = re.sub(r"[()（）]", "", cleaned)
    # 既知のキーワード
    for kw in ["テニスコート", "球技場", "運動公園", "運動場", "体育館",
               "Uスタジアム", "リバーフロント", "スポーツガーデン",
               "南長野", "北部スポーツ", "千曲川", "飯綱高原",
               "犀川", "西寺尾", "篠ノ井", "若穂"]:
        if kw in cleaned:
            keywords.append(kw)
    return keywords


def main() -> int:
    console.print("[bold green]Stage 1.5: DB施設とまちかぎリモートの突合[/bold green]\n")

    db_facilities = fetch_db_facilities()
    console.print(f"DB施設数: [bold]{len(db_facilities)}[/bold]")

    machikagi_list = load_machikagi()
    console.print(f"まちかぎ施設数: [bold]{len(machikagi_list)}[/bold]\n")

    # マッチング実行
    matches: list[Match] = [match_facility(db, machikagi_list) for db in db_facilities]

    # ストラテジー別集計
    stats: dict[str, int] = {"exact": 0, "partial": 0, "keyword": 0, "none": 0}
    for m in matches:
        stats[m.strategy] += 1

    # 結果テーブル表示
    table = Table(title="マッチング結果", show_lines=False)
    table.add_column("DB code", style="cyan", no_wrap=True)
    table.add_column("DB 施設名", style="white")
    table.add_column("→", justify="center")
    table.add_column("machikagi ID", style="green", no_wrap=True)
    table.add_column("machikagi 名", style="white")
    table.add_column("方法", style="yellow")

    for m in matches:
        if m.machikagi:
            table.add_row(
                m.db.facility_code,
                m.db.facility_name[:30],
                "→",
                m.machikagi.machikagi_id,
                m.machikagi.facility_name[:30],
                m.strategy,
            )
        else:
            table.add_row(
                m.db.facility_code,
                m.db.facility_name[:30],
                "✗",
                "-",
                "[red]未マッチ[/red]",
                "-",
            )
    console.print(table)
    console.print()

    # サマリ
    console.print(f"[bold]サマリー:[/bold]")
    console.print(f"  完全一致(exact)   : {stats['exact']}件")
    console.print(f"  部分一致(partial) : {stats['partial']}件")
    console.print(f"  キーワード(keyword): {stats['keyword']}件")
    console.print(f"  [red]未マッチ(none)    : {stats['none']}件[/red]")
    console.print()

    # CSV出力
    csv_path = OUTPUTS_DIR / "matching_result.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        f.write("facility_code,db_name,booking_method,strategy,machikagi_id,machikagi_name\n")
        for m in matches:
            mid = m.machikagi.machikagi_id if m.machikagi else ""
            mname = m.machikagi.facility_name if m.machikagi else ""
            # CSVエスケープ簡易版
            row = [
                m.db.facility_code,
                m.db.facility_name.replace(",", "、"),
                (m.db.booking_method or "").replace(",", "、"),
                m.strategy,
                mid,
                mname.replace(",", "、"),
            ]
            f.write(",".join(row) + "\n")
    console.print(f"[green]保存: {csv_path.relative_to(SCRIPT_DIR)}[/green]")

    # SQL UPDATE 文生成
    sql_path = OUTPUTS_DIR / "update_machikagi_ids.sql"
    with sql_path.open("w", encoding="utf-8") as f:
        f.write("-- machikagi_facility_id を紐付ける UPDATE 文\n")
        f.write("-- Stage 1.5 で生成。CSVで人間確認してから適用推奨\n")
        f.write("-- 前提: migration 004 が適用済\n\n")
        f.write("begin;\n\n")
        for m in matches:
            if m.machikagi:
                f.write(
                    f"update facilities set machikagi_facility_id = {m.machikagi.machikagi_id} "
                    f"where facility_code = '{m.db.facility_code}'; "
                    f"-- {m.strategy}: {m.machikagi.facility_name}\n"
                )
        f.write("\ncommit;\n")
    console.print(f"[green]保存: {sql_path.relative_to(SCRIPT_DIR)}[/green]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
