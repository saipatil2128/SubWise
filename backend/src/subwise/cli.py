"""Command line helpers (Windows-friendly).

python -m subwise.cli init-db           # create/upgrade data/app.db
python -m subwise.cli refresh [ids...]  # fetch official pricing pages now, print results
python -m subwise.cli prices            # show stored prices with their verification labels
"""

from __future__ import annotations

import argparse
import sys

from subwise.config import get_settings
from subwise.container import build_container, run_migrations
from subwise.core.money import format_inr
from subwise.logging_config import configure_logging
from subwise.research.registry import PROVIDERS


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # print ₹ on Windows consoles
    parser = argparse.ArgumentParser(prog="subwise")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db", help="create or upgrade the database")
    ref = sub.add_parser("refresh", help="retrieve live prices from official pages")
    ref.add_argument("providers", nargs="*", help=f"ids: {', '.join(p.id for p in PROVIDERS)}")
    sub.add_parser("prices", help="list stored prices and their labels")
    args = parser.parse_args(argv)
    settings = get_settings()
    configure_logging(settings.logs_dir)

    if args.cmd == "init-db":
        run_migrations(settings)
        print(f"Database ready: {settings.app_db_path}")
        return 0
    c = build_container(settings)
    try:
        if args.cmd == "refresh":
            results = c.prices.refresh(args.providers or None)
            for r in results:
                print(
                    f"{r.provider_id:16} {r.outcome:10} found={r.prices_found:2} "
                    f"verified={r.verified:2}  {r.error or ''}"
                )
                for w in r.warnings[:3]:
                    print(f"{'':16} warning: {w}")
            return 0 if any(r.outcome == "success" for r in results) else 2
        for p in sorted(c.prices.plan_prices(), key=lambda x: (x.provider_id, x.plan_name)):
            print(
                f"{p.plan_name:45} {format_inr(p.price_paise):>12} /{p.billing_cycle_months}mo "
                f"{p.label:16} {p.observed_at:%Y-%m-%d %H:%M} {p.source_url or ''}"
            )
        return 0
    finally:
        c.close()


if __name__ == "__main__":
    raise SystemExit(main())
