"""
Poster generation via NanoBanana2 (Google Gemini 3.1 Flash Image).

Key discovery: NanoBanana2 is the community alias for gemini-3.1-flash-image-preview.
On damiapi.cn, call it via /v1/chat/completions with modalities=["text","image"].
The response embeds the image as base64 in markdown: ![image](data:image/jpeg;base64,...)
"""

from __future__ import annotations

import base64
import os
import re
from pathlib import Path

import httpx

from .models import PosterInput, AnalysisReport

_MODEL = "gemini-3.1-flash-image-preview"

_PROMPT_TEMPLATE = """\
Generate a {quality} {ratio} landscape poster image about:

{topic}

Visual requirements:
- Style: {style}
- Language: English only, all labels and text in English
- Layout: clean professional infographic, generous whitespace
- Typography: bold headline, clear hierarchy
- Do NOT add any watermarks or signatures
"""


def _build_prompt(inp: PosterInput, topic_override: str | None = None) -> str:
    topic = topic_override or inp.topic
    return _PROMPT_TEMPLATE.format(
        quality=inp.quality,
        ratio=inp.ratio.value,
        topic=topic,
        style=inp.style,
    )


def _extract_image(content: str) -> tuple[str, bytes]:
    """
    Parse base64 image from markdown returned by Gemini.
    Returns (format, raw_bytes).
    """
    match = re.search(r"data:image/(\w+);base64,([A-Za-z0-9+/=\s]+)", content)
    if not match:
        raise ValueError(
            "No image data found in API response. "
            "The model may have returned text only. "
            f"Response preview: {content[:200]}"
        )
    fmt = match.group(1)
    b64 = match.group(2).replace("\n", "").replace(" ", "")
    return fmt, base64.b64decode(b64)


def generate_poster(
    inp: PosterInput,
    output_path: str | Path | None = None,
    topic_override: str | None = None,
    timeout: int = 120,
) -> Path:
    """
    Generate a poster image using NanoBanana2 (Gemini 3.1 Flash Image).

    Args:
        inp:           Validated PosterInput (from validator.assert_valid_poster).
        output_path:   Where to save the image. Defaults to ./poster.<ext>.
        topic_override: Override the topic text (e.g. pass report summary).
        timeout:       HTTP request timeout in seconds.

    Returns:
        Path to the saved image file.

    Raises:
        ValueError: on API error or missing image in response.
        httpx.HTTPError: on network failures.
    """
    url = f"{inp.base_url}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {inp.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _MODEL,
        "messages": [{"role": "user", "content": _build_prompt(inp, topic_override)}],
        "modalities": ["text", "image"],
    }

    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, headers=headers, json=payload)

    if resp.status_code != 200:
        raise ValueError(f"API error {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    if "error" in data:
        raise ValueError(f"Poster API error: {data['error'].get('message', data['error'])}")

    raw_content = data["choices"][0]["message"]["content"]
    fmt, img_bytes = _extract_image(raw_content)

    if output_path is None:
        output_path = Path(f"poster.{fmt}")
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(img_bytes)
    return output_path


def generate_poster_from_report(
    report: AnalysisReport,
    inp: PosterInput,
    output_path: str | Path | None = None,
) -> Path:
    """
    Convenience wrapper: build a poster topic string from an AnalysisReport,
    then call generate_poster.

    Args:
        report:      A completed AnalysisReport from run_analysis().
        inp:         PosterInput (topic field is ignored; built from report).
        output_path: Where to save the image.

    Returns:
        Path to the saved image file.
    """
    top_insights = "\n".join(
        f"- {i.finding}" for i in sorted(report.insights, key=lambda x: x.priority)[:3]
    )
    top_actions = "\n".join(
        f"- {a.action}" for a in sorted(report.action_items, key=lambda x: x.priority)[:2]
    )

    topic = (
        f"Business Analytics Report: {report.question}\n\n"
        f"Analysis Type: {report.analytics_type.value.title()}\n\n"
        f"Key Insights:\n{top_insights}\n\n"
        f"Recommended Actions:\n{top_actions}\n\n"
        f"Business Impact: {report.business_impact or 'See full report'}"
    )
    return generate_poster(inp, output_path=output_path, topic_override=topic)
