"""
塩尻市 webR スクレイプ (webr_core の薄いラッパ)

塩尻の差分:
  base_url        : https://www.pf489.com/shiojiri
  external_system : shiojiri_webR
  施設種類番号     : 00=アリーナ(体育館) / 13=テニスコート / 10=サッカー場

使い方:
  python shiojiri/scrape.py --dry-run
  python shiojiri/scrape.py
  python shiojiri/scrape.py --code SIO-GYM-001
"""
from __future__ import annotations

import sys
from pathlib import Path

# scraper/ をパスに追加して webr_core を import
sys.path.insert(0, str(Path(__file__).parent.parent))

from webr_core import CityConfig, build_arg_parser, run_scrape  # noqa: E402

SHIOJIRI = CityConfig(
    name="塩尻市",
    external_system="shiojiri_webR",
    base_url="https://www.pf489.com/shiojiri",
    type_map={
        "SIO-GYM": "00",  # アリーナ(体育館)
        "SIO-TEN": "13",  # テニスコート
        "SIO-SOC": "10",  # サッカー場
    },
)

if __name__ == "__main__":
    sys.exit(run_scrape(SHIOJIRI, build_arg_parser().parse_args()))
