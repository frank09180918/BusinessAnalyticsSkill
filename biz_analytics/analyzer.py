"""
Core analysis engine — applies the Harvard Business Analytics Framework.

Calls the LLM (via damiapi OpenAI-compatible endpoint) and parses the
structured JSON response back into an AnalysisReport model.
"""

from __future__ import annotations

import json
import re
import os
from typing import Optional

import httpx

from .models import (
    AnalysisInput,
    AnalysisReport,
    AnalyticsType,
    Insight,
    ActionItem,
    VisualizationSuggestion,
)

_SYSTEM_PROMPT = """\
You are a senior business analytics consultant trained in the Harvard Business Analytics framework.

When given a business question, you MUST respond with valid JSON only — no markdown fences, no prose.

The JSON schema is:
{
  "analytics_type": "descriptive|diagnostic|predictive|prescriptive",
  "analytics_type_rationale": "<one sentence explaining why>",
  "audience_note": "<how to tailor communication for the stated audience>",
  "unexplored_questions": ["<question>", ...],
  "insights": [
    {"finding": "...", "evidence": "...", "priority": 1}
  ],
  "critical_limitations": ["<limitation>", ...],
  "visualization_suggestions": [
    {"chart_type": "...", "x_axis": "...", "y_axis": "...", "rationale": "..."}
  ],
  "business_impact": "<how findings affect revenue, cost, or market position>",
  "action_items": [
    {"action": "...", "expected_impact": "...", "priority": 1}
  ],
  "tool_recommendation": "SQL | Python/R | Excel/SPSS | mixed"
}

Rules:
- insights must have at least 3 items
- action_items must have at least 2 items
- priorities are integers 1 (highest) to 5 (lowest)
- Do NOT include any text outside the JSON object
"""


def _build_user_message(inp: AnalysisInput) -> str:
    parts = [f"Business question: {inp.question}"]
    if inp.context:
        parts.append(f"Context: {inp.context}")

    # Excel data takes priority over manual data_summary
    if inp.excel_path:
        from .excel_reader import read_excel, summary_to_text
        excel_summary = read_excel(inp.excel_path, sheets=inp.excel_sheets)
        parts.append(f"Excel data provided:\n{summary_to_text(excel_summary)}")
    elif inp.data_summary:
        parts.append(f"Available data: {inp.data_summary}")

    if inp.audience:
        parts.append(f"Target audience: {inp.audience}")
    return "\n\n".join(parts)


def _parse_llm_response(raw: str) -> dict:
    """Extract and parse JSON from the LLM response, handling minor formatting issues."""
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    # Find the outermost JSON object
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in LLM response:\n{raw[:300]}")
    return json.loads(cleaned[start:end])


def _dict_to_report(question: str, data: dict) -> AnalysisReport:
    """Map raw LLM JSON dict to a validated AnalysisReport."""
    insights = [
        Insight(
            finding=i.get("finding", ""),
            evidence=i.get("evidence"),
            priority=i.get("priority", 1),
        )
        for i in data.get("insights", [])
    ]
    actions = [
        ActionItem(
            action=a.get("action", ""),
            expected_impact=a.get("expected_impact"),
            priority=a.get("priority", 1),
        )
        for a in data.get("action_items", [])
    ]
    viz = [
        VisualizationSuggestion(
            chart_type=v.get("chart_type", ""),
            x_axis=v.get("x_axis"),
            y_axis=v.get("y_axis"),
            rationale=v.get("rationale"),
        )
        for v in data.get("visualization_suggestions", [])
    ]

    return AnalysisReport(
        question=question,
        analytics_type=AnalyticsType(data["analytics_type"]),
        analytics_type_rationale=data.get("analytics_type_rationale", ""),
        audience_note=data.get("audience_note"),
        unexplored_questions=data.get("unexplored_questions", []),
        insights=insights,
        critical_limitations=data.get("critical_limitations", []),
        visualization_suggestions=viz,
        business_impact=data.get("business_impact"),
        action_items=actions,
        tool_recommendation=data.get("tool_recommendation"),
    )


def run_analysis(
    inp: AnalysisInput,
    api_key: Optional[str] = None,
    base_url: str = "https://damiapi.cn",
    model: str = "claude-sonnet-4-6",
    timeout: int = 60,
) -> AnalysisReport:
    """
    Send the validated input to the LLM and return a structured AnalysisReport.

    Args:
        inp:      Validated AnalysisInput (from validator.assert_valid_analysis).
        api_key:  API key. Falls back to DAMIAPI_KEY env var.
        base_url: Base URL of the OpenAI-compatible endpoint.
        model:    Model to use for analysis.
        timeout:  Request timeout in seconds.

    Returns:
        AnalysisReport — fully validated structured result.

    Raises:
        ValueError: if the API returns an error or unparseable JSON.
        httpx.HTTPError: on network failures.
    """
    key = api_key or os.environ.get("DAMIAPI_KEY", "")
    if not key:
        raise ValueError("API key required. Pass api_key= or set DAMIAPI_KEY env var.")

    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": _build_user_message(inp)},
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
    }

    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, headers=headers, json=payload)

    if resp.status_code != 200:
        raise ValueError(f"API error {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    if "error" in data:
        raise ValueError(f"LLM error: {data['error'].get('message', data['error'])}")

    raw_content = data["choices"][0]["message"]["content"]
    parsed = _parse_llm_response(raw_content)
    return _dict_to_report(inp.question, parsed)
