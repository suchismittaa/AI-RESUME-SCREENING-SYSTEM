#!/usr/bin/env python3
"""CLI entry point:  python main.py --input ./resumes --output ./output/results.json"""
from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from screener.config import load_settings  # noqa: E402
from screener.pipeline import run_pipeline  # noqa: E402
from screener.report import format_table, write_csv, write_json  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="AI resume screening & ranking")
    ap.add_argument("--input", "-i", type=Path, required=True, help="folder containing resumes (PDF; DOCX/TXT also supported)")
    ap.add_argument("--output", "-o", type=Path, default=Path("output/results.json"))
    ap.add_argument("--no-github", action="store_true", help="skip GitHub enrichment")
    ap.add_argument("--no-llm", action="store_true", help="force deterministic mode even if ANTHROPIC_API_KEY is set")
    ap.add_argument("--top", type=int, default=15, help="rows to print in the terminal table")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    settings = load_settings()
    if args.no_github:
        settings = replace(settings, github_enabled=False)
    if args.no_llm:
        settings = replace(settings, anthropic_api_key="")
    try:
        result = run_pipeline(args.input, settings)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    write_json(result, args.output)
    write_csv(result, args.output.with_suffix(".csv"))
    print(format_table(result, args.top))
    print(f"\nWrote {args.output} and {args.output.with_suffix('.csv')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
