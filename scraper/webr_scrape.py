"""
webR 汎用スクレイプ CLI

使い方:
  python webr_scrape.py --city chino
  python webr_scrape.py --city suwa --dry-run
  python webr_scrape.py --city okaya --code OKA-GYM-001

webr_cities.CITIES に登録された市を webr_core.run_scrape で処理する。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from webr_cities import CITIES  # noqa: E402
from webr_core import build_arg_parser, run_scrape  # noqa: E402

if __name__ == "__main__":
    ap = build_arg_parser()
    ap.add_argument("--city", required=True, choices=list(CITIES),
                    help="対象市 (chino/suwa/okaya)")
    args = ap.parse_args()
    sys.exit(run_scrape(CITIES[args.city], args))
