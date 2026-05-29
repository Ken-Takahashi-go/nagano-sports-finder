"""
machikagi_facility_list.json から関連施設をフィルタして表示する確認用スクリプト
使い方: python inspect_machikagi.py
"""
import json
from pathlib import Path

JSON_PATH = Path(__file__).parent / "outputs" / "machikagi_facility_list.json"

KEYWORDS = [
    "Uスタ", "スタジアム", "球技",
    "犀川", "緑", "若穂", "西和田",
    "西寺尾", "城山", "青垣", "三輪",
    "小松原", "七二会", "テニス",
]

data = json.loads(JSON_PATH.read_text(encoding="utf-8"))

print(f"=== 全{len(data)}件のうち、キーワード一致 ===\n")

for f in data:
    if any(kw in f["facility_name"] for kw in KEYWORDS):
        print(f"{f['machikagi_id']:>4}  {f['facility_name']}")
