"""
Full end-to-end example: validate → analyze → generate report → generate poster.

Run with:
    export DAMIAPI_KEY=sk-...
    python examples/example_analysis.py
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from biz_analytics import (
    validate_analysis_input,
    validate_poster_input,
    run_analysis,
    render_report,
    save_report,
    generate_poster_from_report,
    OutputFormat,
)

API_KEY  = os.environ.get("DAMIAPI_KEY", "")
BASE_URL = "https://damiapi.cn"


def main():
    # ── 1. Validate analysis input ──────────────────────────────────────────
    raw_input = {
        "question": (
            "Our e-commerce conversion rate dropped 15% last month. "
            "What caused it and how do we fix it?"
        ),
        "context":      "We run a B2C fashion e-commerce store, 50k monthly visitors.",
        "data_summary": "Google Analytics funnel data, session recordings, cart abandonment rate (72%).",
        "audience":     "Marketing director and CTO",
        "output_format": "html",
    }

    validation = validate_analysis_input(raw_input)
    if not validation.is_valid:
        print("Validation errors:")
        for err in validation.errors:
            print(f"  - {err}")
        sys.exit(1)

    print("Input valid. Running analysis...")
    inp = validation.model

    # ── 2. Run analysis ─────────────────────────────────────────────────────
    report = run_analysis(inp, api_key=API_KEY, base_url=BASE_URL)
    print(f"Analysis type: {report.analytics_type.value}")
    print(f"Insights: {len(report.insights)}, Actions: {len(report.action_items)}")

    # ── 3. Save Markdown report ─────────────────────────────────────────────
    md_path = save_report(report, "output/report.md", OutputFormat.MARKDOWN)
    print(f"Markdown report saved: {md_path}")

    # ── 4. Save HTML report ─────────────────────────────────────────────────
    html_path = save_report(report, "output/report.html", OutputFormat.HTML)
    print(f"HTML report saved: {html_path}")

    # ── 5. Generate poster (NanoBanana2 / Gemini) ───────────────────────────
    poster_validation = validate_poster_input({
        "topic":    raw_input["question"],
        "api_key":  API_KEY,
        "base_url": BASE_URL,
        "ratio":    "16:9",
    })
    if not poster_validation.is_valid:
        print("Poster input errors:", poster_validation.errors)
    else:
        print("Generating poster...")
        poster_path = generate_poster_from_report(
            report,
            poster_validation.model,
            output_path="output/poster.jpeg",
        )
        print(f"Poster saved: {poster_path}")

    # ── 6. Print markdown to stdout ─────────────────────────────────────────
    print("\n" + "=" * 60)
    print(render_report(report, OutputFormat.MARKDOWN))


if __name__ == "__main__":
    main()
