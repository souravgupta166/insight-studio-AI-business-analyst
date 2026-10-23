
"""
Typed contracts for the AI Business Analyst.

These models define consistent structures for:
- Incoming business questions
- Evidence supporting analytical findings
- Tool execution results
- Final investigation reports

Schema validation checks structure and consistency, not the truth
of the underlying data.
"""

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


Intent = Literal[
    "kpi_lookup",
    "monthly_trend",
    "anomaly_investigation",
]

ExecutionStatus = Literal[
    "success",
    "partial",
    "rejected",
    "error",
]

EvidenceType = Literal[
    "observed_metric",
    "trend",
    "anomaly",
    "decomposition",
    "category_comparison",
    "data_quality",
]


class BusinessQuestion(BaseModel):
    """Validated request received from a user."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    question: str = Field(min_length=1, max_length=1000)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question cannot be blank.")
        return value


class EvidenceItem(BaseModel):
    """One finding with its source and interpretation boundaries."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    evidence_type: EvidenceType
    claim: str = Field(min_length=1)
    source_tool: str = Field(min_length=1)
    metric_name: str | None = None
    value: float | int | str | None = None
    unit: str | None = None
    period: str | None = None
    limitations: list[str] = Field(default_factory=list)
    supports_causal_claim: bool = False


class ToolResult(BaseModel):
    """Standardized result from an approved analytical tool."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(min_length=1)
    status: Literal["success", "partial", "error"]
    data: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    error_message: str | None = None
    database_access: Literal["read-only"] = "read-only"

    @model_validator(mode="after")
    def validate_error_consistency(self):
        """Keep the result status consistent with its error message."""

        if self.status == "error" and not self.error_message:
            raise ValueError(
                "An error result must include an error message."
            )

        if self.status != "error" and self.error_message:
            raise ValueError(
                "Only an error result may include an error message."
            )

        return self


class InvestigationReport(BaseModel):
    """Validated report returned to the user."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    intent: Intent
    status: ExecutionStatus
    summary: str = Field(min_length=1)
    findings: list[EvidenceItem] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    database_access: Literal["read-only"] = "read-only"
    causal_conclusion_established: bool = False
    generated_at_utc: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @field_validator("generated_at_utc")
    @classmethod
    def timestamp_must_be_timezone_aware(
        cls,
        value: datetime,
    ) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "generated_at_utc must include timezone information."
            )

        return value
