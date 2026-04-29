"""
Pydantic models for classification output and validation.
"""

from pydantic import BaseModel, Field
from typing import Literal, List


class ClassificationResult(BaseModel):
    """
    Classification result returned by the LLM.
    
    Attributes:
        is_malicious: Whether the prompt is classified as malicious.
        attack_type: Category of attack, or "none" if benign.
        risk: Risk level (low, medium, or high).
        explanation: Human-readable explanation of the classification.
    """
    
    is_malicious: bool = Field(
        description="Whether the prompt is classified as a malicious injection attempt"
    )
    attack_type: Literal[
        "direct_injection",
        "persona_jailbreak",
        "payload_splitting",
        "indirect_injection",
        "instruction_override",
        "system_prompt_exfiltration",
        "none",
    ] = Field(
        description="Category of attack detected, or 'none' for benign input"
    )
    risk: Literal["low", "medium", "high"] = Field(
        description="Risk level associated with the prompt"
    )
    explanation: str = Field(
        description="Brief explanation of the classification decision"
    )

    class Config:
        """Pydantic config for validation."""
        use_enum_values = True


class PreFilterResult(BaseModel):
    """
    Result of the lightweight pre-filtering stage.
    
    Attributes:
        is_suspicious: Whether any suspicious patterns were detected.
        matched_patterns: List of pattern categories that matched.
    """
    
    is_suspicious: bool = Field(
        description="Whether any suspicious patterns were found"
    )
    matched_patterns: List[str] = Field(
        default_factory=list,
        description="List of matched pattern categories"
    )
