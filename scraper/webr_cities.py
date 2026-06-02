"""
webR系 各市の CityConfig 集約 (Phase 2 横展開)

施設種類番号は webr_probe.py で判明したもの (自治体ごとにカスタム)。
新市追加時: probe → register → ここに CityConfig を1つ足すだけ。

※松本・塩尻は既存スクリプト(matsumoto/stageM6, shiojiri/scrape)で運用中のため
  ここには茅野・諏訪・岡谷のみ登録 (将来統合可)。
"""
from webr_core import CityConfig

CITIES: dict[str, CityConfig] = {
    "chino": CityConfig(
        name="茅野市", external_system="chino_webR",
        base_url="https://www.pf489.com/chino",
        type_map={"CHN-GYM": "01", "CHN-TEN": "06"},
    ),
    "suwa": CityConfig(
        name="諏訪市", external_system="suwa_webR",
        base_url="https://www.pf489.com/suwa",
        type_map={"SUW-GYM": "01", "SUW-TEN": "03", "SUW-GND": "05"},
    ),
    "okaya": CityConfig(
        name="岡谷市", external_system="okaya_webR",
        base_url="https://www.pf489.com/okaya",
        type_map={"OKA-GYM": "01", "OKA-TEN": "03", "OKA-GND": "05"},
    ),
}
