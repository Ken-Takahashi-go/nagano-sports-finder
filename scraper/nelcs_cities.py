"""
NELCS系 各市の NelcsCityConfig 集約 (Phase 2 コンプリート)

自治体ID(URL): 伊那2020900 / 千曲2021800 / 中野2021100 / 箕輪2038300
競技は SPORT_ITEM 共通使用 (伊那で確認、市差は register 時に施設0なら要確認)
"""
from nelcs_core import NelcsCityConfig

# 体育館・テニス・サッカー・フットサルを網羅
SPORTS = ["basketball", "tennis_hard", "soccer", "futsal"]

CITIES: dict[str, NelcsCityConfig] = {
    "ina": NelcsCityConfig(name="伊那市", external_system="nelcs_ina",
                           municipality_id="2020900", sports=SPORTS),
    "chikuma": NelcsCityConfig(name="千曲市", external_system="nelcs_chikuma",
                               municipality_id="2021800", sports=SPORTS),
    "nakano": NelcsCityConfig(name="中野市", external_system="nelcs_nakano",
                              municipality_id="2021100", sports=SPORTS),
    "minowa": NelcsCityConfig(name="箕輪町", external_system="nelcs_minowa",
                              municipality_id="2038300", sports=SPORTS),
}
