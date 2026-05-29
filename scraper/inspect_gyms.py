"""
machikagi_facility_list.json から体育館・アリーナ等を抽出する
フットサル可能候補の判定用
"""
import json
from pathlib import Path

JSON_PATH = Path(__file__).parent / "outputs" / "machikagi_facility_list.json"

# 体育館・アリーナ系
GYM_KEYWORDS = ["体育館", "アリーナ", "屋内運動場", "B&G", "総合運動場"]

# 既に登録済の運動場(再登録不要)
ALREADY_REGISTERED = ["テニス", "公民館", "プール", "Uスタジアム", "犀川", "西寺尾", "七二会",
                      "若穂中央公園", "青垣公園", "小松原", "三輪", "豊野", "鬼無里",
                      "緑ヶ丘", "緑ケ丘", "古里", "篠ノ井", "御厨", "茶臼山", "真島",
                      "城山", "西和田", "大豆島", "昭和の森", "川柳", "飯綱高原",
                      "リバーフロント"]

data = json.loads(JSON_PATH.read_text(encoding="utf-8"))

print(f"=== machikagi 全{len(data)}件 ===\n")

# 体育館・アリーナ抽出
print("[bold]体育館・アリーナ・屋内系施設:[/bold]")
gym_facilities = []
for f in data:
    name = f["facility_name"]
    if any(kw in name for kw in GYM_KEYWORDS):
        gym_facilities.append(f)
        print(f"  {f['machikagi_id']:>4}  {name}")

print(f"\n→ 計 {len(gym_facilities)} 件")

# テニス・運動場系(既登録)
print("\n[bold]既登録の運動場・テニスコート系 (参考):[/bold]")
already_count = 0
for f in data:
    name = f["facility_name"]
    if any(kw in name for kw in GYM_KEYWORDS):
        continue
    if any(kw in name for kw in ALREADY_REGISTERED):
        already_count += 1

print(f"  約 {already_count} 件 (既にfacilitiesテーブルに紐付け済)")

# その他 (公民館や未分類)
print("\n[bold]その他 (公民館等の非スポーツ施設含む):[/bold]")
other_count = len(data) - len(gym_facilities) - already_count
print(f"  約 {other_count} 件")
