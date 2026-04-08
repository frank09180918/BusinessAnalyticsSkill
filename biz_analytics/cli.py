"""
CLI entry point — run as: python -m biz_analytics.cli "your question here"

Usage examples:
  python -m biz_analytics.cli "Why did our conversion rate drop 15% last month?"
  python -m biz_analytics.cli "Predict churn for next quarter" --format html --out report.html
  python -m biz_analytics.cli "Compare marketing ROI" --poster --poster-out poster.jpeg
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .models import OutputFormat, ImageRatio
from .validator import assert_valid_analysis, assert_valid_poster
from .analyzer import run_analysis
from .reporter import render_report, save_report
from .poster import generate_poster_from_report


def _get_api_key() -> str:
    key = os.environ.get("DAMIAPI_KEY", "")
    if not key:
        print(
            "ERROR: API key not found.\n"
            "Set the DAMIAPI_KEY environment variable:\n"
            "  export DAMIAPI_KEY=sk-...",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="biz-analytics",
        description="Harvard Business Analytics Framework CLI",
    )
    p.add_argument("question", help="Business question or problem to analyze")
    p.add_argument("--context", default=None, help="Background context (optional)")
    p.add_argument("--data", default=None, metavar="DATA_SUMMARY",
                   help="Brief description of available data (optional)")
    p.add_argument("--audience", default=None, help="Target audience for the report")
    p.add_argument(
        "--format", dest="output_format", default="markdown",
        choices=["markdown", "html", "json"],
        help="Report output format (default: markdown)",
    )
    p.add_argument("--out", default=None, metavar="FILE",
                   help="Save report to file instead of printing to stdout")
    p.add_argument(
        "--base-url", default="https://damiapi.cn",
        help="API base URL (default: https://damiapi.cn)",
    )
    p.add_argument(
        "--model", default="claude-sonnet-4-6",
        help="LLM model for analysis (default: claude-sonnet-4-6)",
    )
    p.add_argument(
        "--poster", action="store_true",
        help="Generate a visual poster from the analysis results",
    )
    p.add_argument("--poster-out", default="poster.jpeg", metavar="FILE",
                   help="Poster output path (default: poster.jpeg)")
    p.add_argument(
        "--poster-ratio", default="16:9", choices=["16:9", "4:3", "1:1"],
        help="Poster aspect ratio (default: 16:9)",
    )
    p.add_argument(
        "--excel", default=None, metavar="FILE",
        help="Path to Excel file (.xlsx/.xls). All sheets are read and injected into analysis.",
    )
    p.add_argument(
        "--sheets", nargs="+", default=None, metavar="SHEET",
        help="Specific sheet names to read (default: all sheets). "
             "Example: --sheets Sales Q1 Q2",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    api_key = _get_api_key()

    # ── Step 1: Validate input ──
    print("Validating input...", file=sys.stderr)
    try:
        inp = assert_valid_analysis({
            "question":      args.question,
            "context":       args.context,
            "data_summary":  args.data,
            "audience":      args.audience,
            "output_format": args.output_format,
            "excel_path":    args.excel,
            "excel_sheets":  args.sheets,
        })
    except ValueError as exc:
        print(f"Input validation failed:\n{exc}", file=sys.stderr)
        return 1

    # ── Step 2: Run analysis ──
    print("Running analysis...", file=sys.stderr)
    try:
        report = run_analysis(inp, api_key=api_key, base_url=args.base_url, model=args.model)
    except Exception as exc:
        print(f"Analysis failed: {exc}", file=sys.stderr)
        return 1

    fmt = OutputFormat(args.output_format)

    # ── Step 3: Generate poster (optional) ──
    if args.poster:
        print("Generating poster via NanoBanana2...", file=sys.stderr)
        try:
            poster_inp = assert_valid_poster({
                "topic":    args.question,
                "api_key":  api_key,
                "base_url": args.base_url,
                "ratio":    args.poster_ratio,
            })
            poster_path = generate_poster_from_report(report, poster_inp, args.poster_out)
            report.poster_url = str(poster_path)
            print(f"Poster saved: {poster_path}", file=sys.stderr)
        except Exception as exc:
            print(f"Poster generation failed (continuing): {exc}", file=sys.stderr)

    # ── Step 4: Render and output report ──
    rendered = render_report(report, fmt)
    if args.out:
        saved = save_report(report, args.out, fmt)
        print(f"Report saved: {saved}", file=sys.stderr)
    else:
        print(rendered)

    return 0


if __name__ == "__main__":
    sys.exit(main())
