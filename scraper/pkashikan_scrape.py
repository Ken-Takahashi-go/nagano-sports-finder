"""
P-Kashikan 汎用スクレイプ CLI

使い方:
  python pkashikan_scrape.py --city suzaka
  python pkashikan_scrape.py --city ueda --days 7
  python pkashikan_scrape.py --city komagane --dry-run
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pkashikan_cities import CITIES  # noqa: E402
from pkashikan_core import build_arg_parser, run_scrape  # noqa: E402

if __name__ == "__main__":
    ap = build_arg_parser()
    ap.add_argument("--city", required=True, choices=list(CITIES),
                    help="対象市 (suzaka/ueda/komagane/tomi/omachi)")
    args = ap.parse_args()
    sys.exit(run_scrape(CITIES[args.city], args))
