"""
Data models and validation schemas for the Harvard Business Analytics Framework.
All inputs and outputs are validated with Pydantic before processing.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ── Enums ──────────────────────────────────────────────────────────────────

class AnalyticsType(str, Enum):
    DESCRIPTIVE  = "descriptive"   # What is happening?
    DIAGNOSTIC   = "diagnostic"    # Why did it happen?
    PREDICTIVE   = "predictive"    # What will happen?
    PRESCRIPTIVE = "prescriptive"  # What should we do?


class OutputFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML     = "html"
    JSON     = "json"


class ImageRatio(str, Enum):
    RATIO_16_9 = "16:9"
    RATIO_4_3  = "4:3"
    RATIO_1_1  = "1:1"


# ── Input Schemas ───────────────────────────────────────────────────────────

class AnalysisInput(BaseModel):
    """Validated input for a business analytics request."""

    question: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="The business question or problem to analyze",
    )
    context: Optional[str] = Field(
        None,
        max_length=5000,
        description="Additional background context (optional)",
    )
    data_summary: Optional[str] = Field(
        None,
        max_length=3000,
        description="Brief description or sample of available data (optional)",
    )
    audience: Optional[str] = Field(
        None,
        max_length=200,
        description="Who will receive this analysis (e.g. 'C-suite', 'marketing team')",
    )
    output_format: OutputFormat = Field(
        OutputFormat.MARKDOWN,
        description="Desired output format",
    )

    @field_validator("question")
    @classmethod
    def question_must_be_meaningful(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped.split()) < 3:
            raise ValueError("Question must contain at least 3 words to be meaningful.")
        return stripped

    @field_validator("context", "data_summary", "audience", mode="before")
    @classmethod
    def strip_optional_strings(cls, v):
        return v.strip() if isinstance(v, str) else v


class PosterInput(BaseModel):
    """Validated input for poster generation via NanoBanana2 (Gemini)."""

    topic: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Topic or analysis result to visualize in the poster",
    )
    style: str = Field(
        default="professional infographic, dark navy blue and gold, modern clean design",
        max_length=300,
    )
    ratio: ImageRatio = Field(ImageRatio.RATIO_16_9)
    quality: str = Field(
        default="4K ultra high definition",
        description="Image quality descriptor",
    )
    api_key: str = Field(..., min_length=10)
    base_url: str = Field(default="https://damiapi.cn")

    @field_validator("base_url")
    @classmethod
    def normalize_base_url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if not v.startswith("http"):
            v = "https://" + v
        return v


# ── Output Schemas ──────────────────────────────────────────────────────────

class Insight(BaseModel):
    """A single analytical finding."""
    finding: str = Field(..., description="The key insight")
    evidence: Optional[str] = Field(None, description="Data or reasoning that supports it")
    priority: int = Field(default=1, ge=1, le=5, description="Importance (1=highest)")


class ActionItem(BaseModel):
    """A concrete recommended action."""
    action: str
    expected_impact: Optional[str] = None
    priority: int = Field(default=1, ge=1, le=5)


class VisualizationSuggestion(BaseModel):
    """Chart recommendation."""
    chart_type: str = Field(..., description="e.g. 'line chart', 'heat map', 'scatter plot'")
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    rationale: Optional[str] = None


class AnalysisReport(BaseModel):
    """Full structured output of one analysis run."""

    question: str
    analytics_type: AnalyticsType
    analytics_type_rationale: str

    # 6-dimension analysis
    audience_note: Optional[str] = None
    unexplored_questions: list[str] = Field(default_factory=list)
    insights: list[Insight] = Field(default_factory=list)
    critical_limitations: list[str] = Field(default_factory=list)
    visualization_suggestions: list[VisualizationSuggestion] = Field(default_factory=list)
    business_impact: Optional[str] = None

    # Recommendations
    action_items: list[ActionItem] = Field(default_factory=list)

    # Meta
    tool_recommendation: Optional[str] = None
    poster_url: Optional[str] = None   # set if poster was generated

    @model_validator(mode="after")
    def must_have_at_least_one_insight(self) -> "AnalysisReport":
        if not self.insights:
            raise ValueError("An analysis report must contain at least one insight.")
        return self
