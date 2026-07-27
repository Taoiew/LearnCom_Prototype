from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RubricScaleLevel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    score: float = Field(ge=0)
    description: str = Field(min_length=1)


class RubricCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    weight: float = Field(gt=0, le=1)
    levels: list[RubricScaleLevel] = Field(min_length=1)


class RubricCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    course_id: str = Field(min_length=1)
    class_session_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    criteria: list[RubricCriterion] = Field(min_length=1)


class RubricDefinition(RubricCreateRequest):
    rubric_id: str
    source_filename: Optional[str] = None
    created_at: datetime


class RubricEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(min_length=1)
    submission_text: str = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list)


class CriterionEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    score: float = Field(ge=0)
    max_score: float = Field(gt=0)
    feedback: str = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list)


class RubricEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluation_id: str
    rubric_id: str
    student_id: str
    total_score: float = Field(ge=0)
    max_score: float = Field(gt=0)
    percentage: float = Field(ge=0, le=100)
    criterion_results: list[CriterionEvaluation]
    overall_feedback: str = Field(min_length=1)
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    created_at: datetime


class SessionReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str
    course_id: str
    class_session_id: str
    generated_at: datetime
    total_interactions: int = Field(ge=0)
    unique_students: int = Field(ge=0)
    average_confidence: float = Field(ge=0, le=1)
    average_readiness: float = Field(ge=0, le=100)
    on_track_count: int = Field(ge=0)
    needs_review_count: int = Field(ge=0)
    at_risk_count: int = Field(ge=0)
    common_issues: list[str] = Field(default_factory=list)
    suggested_focus: str = ""
    rubric_summary: dict[str, float] = Field(default_factory=dict)
