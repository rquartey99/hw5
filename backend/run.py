"""Run the Campus Customs team from the command line.

    python run.py --ticket 101                     # read-only: plan ticket 101, change nothing
    python run.py "Review every open ticket"       # read-only, custom request to the boss
    python run.py --ticket 102 --allow-writes --approver "Regi"   # may update tickets and record payments

Every step is appended to ../output/audit_trail.json.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from agents import Team, prompts_missing_rules


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("request", nargs="?", help="What to ask the boss.")
    parser.add_argument("--ticket", type=int, help="Shortcut for 'Handle ticket N.'")
    parser.add_argument("--allow-writes", action="store_true", help="Let agents change the working-copy database.")
    parser.add_argument("--approver", help="Human name recorded on any payment; payments are blocked without it.")
    args = parser.parse_args()

    request = args.request or (f"Handle ticket {args.ticket}." if args.ticket else "Review every open ticket.")
    if missing := prompts_missing_rules():
        print(f"Warning: shop rules not written yet in prompts for: {', '.join(missing)}", file=sys.stderr)

    run_id, report = asyncio.run(Team().run(request, allow_writes=args.allow_writes, approver=args.approver))
    print(f"run_id: {run_id}")
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
