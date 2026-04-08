"""
Report generation — converts an AnalysisReport into Markdown or HTML.

Markdown: clean, readable, copy-paste friendly.
HTML: self-contained single file with inline CSS, ready to open in a browser.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .models import AnalysisReport, OutputFormat

_PRIORITY_LABEL = {1: "Critical", 2: "High", 3: "Medium", 4: "Low", 5: "Minor"}
_TYPE_EMOJI = {
    "descriptive":  "📊",
    "diagnostic":   "🔍",
    "predictive":   "🔮",
    "prescriptive": "🎯",
}


# ── Markdown ────────────────────────────────────────────────────────────────

def _md_section(title: str, content: str) -> str:
    return f"\n## {title}\n\n{content}\n"


def to_markdown(report: AnalysisReport) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    emoji = _TYPE_EMOJI.get(report.analytics_type.value, "📈")

    lines = [
        f"# Business Analytics Report",
        f"",
        f"> Generated: {ts}",
        f"",
        f"**Question:** {report.question}",
        f"",
    ]

    # Analysis type
    type_label = report.analytics_type.value.title()
    lines += [
        f"## {emoji} Analysis Type: {type_label}",
        f"",
        f"{report.analytics_type_rationale}",
        f"",
    ]

    # Audience
    if report.audience_note:
        lines += [
            f"## Audience & Communication",
            f"",
            f"{report.audience_note}",
            f"",
        ]

    # Key Insights
    lines += ["## Key Insights", ""]
    for i, insight in enumerate(sorted(report.insights, key=lambda x: x.priority), 1):
        priority = _PRIORITY_LABEL.get(insight.priority, str(insight.priority))
        lines.append(f"**{i}. {insight.finding}** `{priority}`")
        if insight.evidence:
            lines.append(f"   - *Evidence:* {insight.evidence}")
        lines.append("")

    # Unexplored questions
    if report.unexplored_questions:
        lines += ["## Questions Worth Exploring", ""]
        for q in report.unexplored_questions:
            lines.append(f"- {q}")
        lines.append("")

    # Visualization
    if report.visualization_suggestions:
        lines += ["## Visualization Recommendations", ""]
        for v in report.visualization_suggestions:
            axes = ""
            if v.x_axis or v.y_axis:
                axes = f" (X: {v.x_axis or '—'} / Y: {v.y_axis or '—'})"
            lines.append(f"- **{v.chart_type}**{axes}")
            if v.rationale:
                lines.append(f"  - {v.rationale}")
        lines.append("")

    # Action Items
    lines += ["## Action Recommendations", ""]
    for i, action in enumerate(sorted(report.action_items, key=lambda x: x.priority), 1):
        priority = _PRIORITY_LABEL.get(action.priority, str(action.priority))
        lines.append(f"**{i}. {action.action}** `{priority}`")
        if action.expected_impact:
            lines.append(f"   - Expected impact: {action.expected_impact}")
        lines.append("")

    # Business impact
    if report.business_impact:
        lines += ["## Business Impact", "", report.business_impact, ""]

    # Limitations
    if report.critical_limitations:
        lines += ["## Data Limitations & Assumptions", ""]
        for lim in report.critical_limitations:
            lines.append(f"- {lim}")
        lines.append("")

    # Tool recommendation
    if report.tool_recommendation:
        lines += [f"## Recommended Tools", "", f"`{report.tool_recommendation}`", ""]

    # Poster link
    if report.poster_url:
        lines += ["## Visual Poster", "", f"![Analytics Poster]({report.poster_url})", ""]

    return "\n".join(lines)


# ── HTML ─────────────────────────────────────────────────────────────────────

_HTML_CSS = """
  body { font-family: 'Segoe UI', Arial, sans-serif; max-width: 900px;
         margin: 40px auto; padding: 0 24px; color: #1a1a2e; background: #f8f9fa; }
  h1   { color: #0d1b2a; border-bottom: 3px solid #c9a84c; padding-bottom: 12px; }
  h2   { color: #1b3a5c; margin-top: 32px; }
  .meta { color: #666; font-size: 0.9em; margin-bottom: 24px; }
  .type-badge { display: inline-block; background: #1b3a5c; color: #c9a84c;
                padding: 4px 14px; border-radius: 20px; font-weight: bold; }
  .card { background: white; border-left: 4px solid #c9a84c; border-radius: 6px;
          padding: 16px 20px; margin: 12px 0; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
  .priority { font-size: 0.75em; background: #e8f4fd; color: #1b3a5c;
              border-radius: 10px; padding: 2px 8px; margin-left: 8px; font-weight: 600; }
  .priority.critical { background: #fde8e8; color: #b91c1c; }
  .priority.high     { background: #fef3cd; color: #92400e; }
  .evidence { color: #555; font-size: 0.9em; margin-top: 6px; font-style: italic; }
  .limitation { color: #666; margin: 6px 0; padding-left: 16px; }
  .action-card { background: white; border-left: 4px solid #1b3a5c; border-radius: 6px;
                 padding: 14px 18px; margin: 10px 0; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
  .impact { color: #2d6a4f; font-size: 0.9em; margin-top: 6px; }
  .tool-tag { background: #1b3a5c; color: white; padding: 4px 12px;
              border-radius: 4px; font-family: monospace; font-size: 0.95em; }
  .viz-item { padding: 8px 0; border-bottom: 1px solid #eee; }
  .poster-img { width: 100%; border-radius: 8px; margin-top: 12px;
                box-shadow: 0 4px 16px rgba(0,0,0,.15); }
  ul { padding-left: 20px; }
  li { margin: 6px 0; }
"""


def _priority_class(p: int) -> str:
    return {1: "critical", 2: "high"}.get(p, "")


def to_html(report: AnalysisReport) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    emoji = _TYPE_EMOJI.get(report.analytics_type.value, "📈")
    type_label = report.analytics_type.value.title()

    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    body_parts = [
        f'<h1>Business Analytics Report</h1>',
        f'<div class="meta">Generated: {ts}</div>',
        f'<p><strong>Question:</strong> {esc(report.question)}</p>',
        f'<h2>{emoji} Analysis Type</h2>',
        f'<p><span class="type-badge">{esc(type_label)}</span></p>',
        f'<p>{esc(report.analytics_type_rationale)}</p>',
    ]

    if report.audience_note:
        body_parts += [
            f'<h2>Audience & Communication</h2>',
            f'<p>{esc(report.audience_note)}</p>',
        ]

    body_parts.append('<h2>Key Insights</h2>')
    for insight in sorted(report.insights, key=lambda x: x.priority):
        plabel = _PRIORITY_LABEL.get(insight.priority, str(insight.priority))
        pcls = _priority_class(insight.priority)
        evidence_html = f'<div class="evidence">Evidence: {esc(insight.evidence)}</div>' if insight.evidence else ""
        body_parts.append(
            f'<div class="card">'
            f'<strong>{esc(insight.finding)}</strong>'
            f'<span class="priority {pcls}">{plabel}</span>'
            f'{evidence_html}'
            f'</div>'
        )

    if report.unexplored_questions:
        body_parts.append('<h2>Questions Worth Exploring</h2><ul>')
        for q in report.unexplored_questions:
            body_parts.append(f'<li>{esc(q)}</li>')
        body_parts.append('</ul>')

    if report.visualization_suggestions:
        body_parts.append('<h2>Visualization Recommendations</h2>')
        for v in report.visualization_suggestions:
            axes = f" &mdash; X: {esc(v.x_axis or '—')} / Y: {esc(v.y_axis or '—')}" if (v.x_axis or v.y_axis) else ""
            rationale_html = f'<br><small>{esc(v.rationale)}</small>' if v.rationale else ""
            body_parts.append(
                f'<div class="viz-item"><strong>{esc(v.chart_type)}</strong>{axes}{rationale_html}</div>'
            )

    body_parts.append('<h2>Action Recommendations</h2>')
    for action in sorted(report.action_items, key=lambda x: x.priority):
        plabel = _PRIORITY_LABEL.get(action.priority, str(action.priority))
        pcls = _priority_class(action.priority)
        impact_html = f'<div class="impact">Expected impact: {esc(action.expected_impact)}</div>' if action.expected_impact else ""
        body_parts.append(
            f'<div class="action-card">'
            f'<strong>{esc(action.action)}</strong>'
            f'<span class="priority {pcls}">{plabel}</span>'
            f'{impact_html}'
            f'</div>'
        )

    if report.business_impact:
        body_parts += [f'<h2>Business Impact</h2>', f'<p>{esc(report.business_impact)}</p>']

    if report.critical_limitations:
        body_parts.append('<h2>Data Limitations & Assumptions</h2><ul>')
        for lim in report.critical_limitations:
            body_parts.append(f'<li class="limitation">{esc(lim)}</li>')
        body_parts.append('</ul>')

    if report.tool_recommendation:
        body_parts += [
            f'<h2>Recommended Tools</h2>',
            f'<span class="tool-tag">{esc(report.tool_recommendation)}</span>',
        ]

    if report.poster_url:
        body_parts += [
            f'<h2>Visual Poster</h2>',
            f'<img class="poster-img" src="{esc(report.poster_url)}" alt="Analytics Poster">',
        ]

    return (
        f'<!DOCTYPE html><html lang="en"><head>'
        f'<meta charset="UTF-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f'<title>Business Analytics Report</title>'
        f'<style>{_HTML_CSS}</style>'
        f'</head><body>'
        + "\n".join(body_parts)
        + f'</body></html>'
    )


# ── JSON ─────────────────────────────────────────────────────────────────────

def to_json(report: AnalysisReport) -> str:
    return report.model_dump_json(indent=2)


# ── Public interface ─────────────────────────────────────────────────────────

def render_report(report: AnalysisReport, fmt: OutputFormat = OutputFormat.MARKDOWN) -> str:
    """
    Render an AnalysisReport to the requested format string.

    Args:
        report: Completed AnalysisReport.
        fmt:    OutputFormat.MARKDOWN | HTML | JSON

    Returns:
        Rendered string content.
    """
    if fmt == OutputFormat.HTML:
        return to_html(report)
    if fmt == OutputFormat.JSON:
        return to_json(report)
    return to_markdown(report)


def save_report(
    report: AnalysisReport,
    output_path: str | Path,
    fmt: OutputFormat = OutputFormat.MARKDOWN,
) -> Path:
    """
    Render and save the report to a file.

    Args:
        report:      Completed AnalysisReport.
        output_path: Destination file path.
        fmt:         Output format.

    Returns:
        Resolved Path of the saved file.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(report, fmt), encoding="utf-8")
    return path.resolve()
