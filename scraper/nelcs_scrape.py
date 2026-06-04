"""
NELCS 汎用スクレイプ CLI

使い方:
  python nelcs_scrape.py --city ina
  python nelcs_scrape.py --city chikuma --dry-run
  python nelcs_scrape.py --city nakano --sports basketball,soccer
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from nelcs_cities import CITIES  # noqa: E402
from nelcs_core import build_arg_parser, run_scrape  # noqa: E402

if __name__ == "__main__":
    ap = build_arg_parser()
    ap.add_argument("--city", required=True, choices=list(CITIES),
                    help="対象市 (ina/chikuma/nakano/minowa)")
    args = ap.parse_args()
    sys.exit(run_scrape(CITIES[args.city], args))
