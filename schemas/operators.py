"""Operator copilot schemas for Gemini Q&A."""

from enum import Enum
from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    """The three supported operator questions."""

    WHY_ACTION = "WHY_ACTION"  # "Why did robot X stop/slow/reroute?"
    ZONE_STATUS = "ZONE_STATUS"  # "What's happening in Zone C?"
    PATTERN_CHECK = "PATTERN_CHECK"  # "Is this isolated or part of a pattern?"


class Confidence(str, Enum):
    """Confidence level for Gemini answers."""

    HIGH = "HIGH"  # Strong telemetry evidence
    MEDIUM = "MEDIUM"  # Some evidence, some inference
    LOW = "LOW"  # Limited data, educated guess
    INSUFFICIENT = "INSUFFICIENT"  # Cannot answer responsibly


class OperatorQuestion(BaseModel):
    """An operator question to be answered by Gemini."""

    question_type: QuestionType = Field(..., description="Type of question")
    raw_text: str = Field(..., description="Original question text from operator")

    # Context for the question
    robot_id: str | None = Field(None, description="Robot ID if question is about a specific robot")
    zone_id: str | None = Field(None, description="Zone ID if question is about a specific zone")
    decision_id: str | None = Field(None, description="Decision ID if asking about a specific event")

    class Config:
        json_schema_extra = {
            "example": {
                "question_type": "WHY_ACTION",
                "raw_text": "Why did robot-1 stop?",
                "robot_id": "robot-1",
                "zone_id": "zone-c",
                "decision_id": "dec-1703001234567-robot-1",
            }
        }


class EvidenceItem(BaseModel):
    """A piece of evidence supporting the answer."""

    signal: str = Field(..., description="What signal or data point")
    value: str = Field(..., description="The observed value")
    relevance: str = Field(..., description="Why this matters")


class OperatorAnswer(BaseModel):
    """Structured answer from Gemini."""

    question_type: QuestionType = Field(..., description="Type of question answered")
    confidence: Confidence = Field(..., description="Confidence in this answer")

    # The answer
    summary: str = Field(
        ..., description="Natural language answer (2-3 sentences)"
    )
    evidence: list[EvidenceItem] = Field(
        ..., description="Bullet-point evidence supporting the answer"
    )

    # For pattern questions
    is_pattern: bool | None = Field(
        None, description="True if this appears to be part of a pattern"
    )
    pattern_description: str | None = Field(
        None, description="Description of the pattern if detected"
    )

    # Recommended action (optional)
    recommended_action: str | None = Field(
        None, description="Suggested operator action if any"
    )

    # Refusal case
    refusal_reason: str | None = Field(
        None, description="Why we cannot answer (if confidence=INSUFFICIENT)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "question_type": "WHY_ACTION",
                "confidence": "HIGH",
                "summary": "Robot-1 stopped because a human entered its path at close range while the robot was moving at 1.2 m/s. The ultrasonic sensor detected an obstacle at 1.8m and BLE confirmed human presence.",
                "evidence": [
                    {
                        "signal": "Ultrasonic distance",
                        "value": "1.8m (threshold: 2.0m)",
                        "relevance": "Below safe stopping distance at current speed",
                    },
                    {
                        "signal": "BLE RSSI",
                        "value": "-55 dBm",
                        "relevance": "Indicates human within ~2m",
                    },
                    {
                        "signal": "Relative velocity",
                        "value": "+1.5 m/s (closing)",
                        "relevance": "Human and robot approaching each other",
                    },
                ],
                "is_pattern": None,
                "pattern_description": None,
                "recommended_action": "No action needed; robot responded correctly",
                "refusal_reason": None,
            }
        }
