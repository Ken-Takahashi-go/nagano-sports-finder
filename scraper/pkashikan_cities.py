"""
P-Kashikan系 各市の PKCityConfig 集約 (Phase 2)

施設名ベースで照合。新市追加時: register → ここに1つ足すだけ。
競技コードは須坂で確認した SPORT_SEARCH を共通使用 (市差があれば要検証)。
"""
from pkashikan_core import PKCityConfig

# 体育館・テニス・サッカー/フットサルを網羅する検索競技
SPORTS = ["basketball", "tennis_hard", "tennis_soft", "soccer", "futsal"]

CITIES: dict[str, PKCityConfig] = {
    "suzaka": PKCityConfig(
        name="須坂市", external_system="pkashikan_suzaka",
        base_url="https://k3.p-kashikan.jp/suzaka-city", sports=SPORTS),
    "ueda": PKCityConfig(
        name="上田市", external_system="pkashikan_ueda",
        base_url="https://k6.p-kashikan.jp/ueda-city", sports=SPORTS),
    "komagane": PKCityConfig(
        name="駒ヶ根市", external_system="pkashikan_komagane",
        base_url="https://k3.p-kashikan.jp/komagane-city", sports=SPORTS),
    "tomi": PKCityConfig(
        name="東御市", external_system="pkashikan_tomi",
        base_url="https://k2.p-kashikan.jp/tomi-city", sports=SPORTS),
    "omachi": PKCityConfig(
        name="大町市", external_system="pkashikan_omachi",
        base_url="https://k5.p-kashikan.jp/omachi-city", sports=SPORTS),
}
