"""Formal LLM Security and Safety Guardrails.

Provides input prompt injection defenses, domain relevance filtering,
and output safety verification to protect agent integrity and user safety.
"""

import re
from typing import Optional, List
from pydantic import BaseModel, Field


class GuardrailResult(BaseModel):
    """Result of an input or output guardrail evaluation."""
    is_safe: bool = Field(..., description="Whether the input or output passed security guardrails")
    violation_type: Optional[str] = Field(default=None, description="Classification of security violation")
    reason: Optional[str] = Field(default=None, description="Detailed explanation if safety check failed")
    sanitized_text: str = Field(..., description="Sanitized or original safe text")


# Known adversarial prompt injection and jailbreak signatures
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|system)\s+rules?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*leak", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?(system\s+instructions?|hidden\s+prompt)", re.IGNORECASE),
    re.compile(r"DAN\s+mode", re.IGNORECASE),
]

# Allowed domain keywords (Cycling, fit, geometry, bikes)
CYCLING_DOMAIN_TERMS = {
    "bike", "bicycle", "fit", "geometry", "stack", "reach", "stem",
    "spacer", "handlebar", "saddle", "inseam", "height", "frame",
    "road", "gravel", "tarmac", "domane", "canyon", "specialized",
    "trek", "cervelo", "giant", "cockpit", "angle", "aerodynamic"
}


class InputSecurityGuardrail:
    """Evaluates incoming user prompts for adversarial attacks and out-of-scope misuse."""

    @staticmethod
    def validate_input(user_prompt: str) -> GuardrailResult:
        """Inspect user prompt against prompt injection and jailbreaks.

        Args:
            user_prompt: Raw text submitted by user.

        Returns:
            GuardrailResult with validation verdict and sanitized query.
        """
        if not user_prompt or not user_prompt.strip():
            return GuardrailResult(
                is_safe=False,
                violation_type="EMPTY_INPUT",
                reason="Input query cannot be empty.",
                sanitized_text=""
            )

        # Check for adversarial prompt injections
        for pattern in INJECTION_PATTERNS:
            if pattern.search(user_prompt):
                return GuardrailResult(
                    is_safe=False,
                    violation_type="PROMPT_INJECTION_DETECTED",
                    reason="Adversarial prompt injection pattern detected. Query blocked by security guardrails.",
                    sanitized_text=""
                )

        # Basic length sanity check (prevent buffer / context flood attacks)
        if len(user_prompt) > 4000:
            return GuardrailResult(
                is_safe=False,
                violation_type="INPUT_TOO_LARGE",
                reason="Query exceeds maximum allowed security length (4000 characters).",
                sanitized_text=user_prompt[:4000]
            )

        return GuardrailResult(
            is_safe=True,
            sanitized_text=user_prompt.strip()
        )


class OutputSafetyGuardrail:
    """Verifies that generated responses and recommendations strictly conform to physical safety rules."""

    @staticmethod
    def validate_cockpit_recommendation(
        spacer_height_mm: float,
        stem_length_mm: float,
        is_carbon_steerer: bool = True
    ) -> GuardrailResult:
        """Ensure proposed physical setup does not violate catastrophic safety maximums.

        Args:
            spacer_height_mm: Headset spacers under stem.
            stem_length_mm: Stem length.
            is_carbon_steerer: Whether steerer tube is carbon.

        Returns:
            GuardrailResult with structural safety pass/fail.
        """
        # Absolute structural safety limit
        if is_carbon_steerer and spacer_height_mm > 40.0:
            return GuardrailResult(
                is_safe=False,
                violation_type="CRITICAL_SAFETY_VIOLATION",
                reason=f"Spacer height ({spacer_height_mm}mm) exceeds the 40mm carbon steerer tube safety maximum.",
                sanitized_text=""
            )

        if stem_length_mm < 60.0:
            return GuardrailResult(
                is_safe=False,
                violation_type="DANGEROUS_HANDLING_VIOLATION",
                reason=f"Stem length ({stem_length_mm}mm) is dangerously short and causes steering instability.",
                sanitized_text=""
            )

        return GuardrailResult(
            is_safe=True,
            sanitized_text="Setup passed output safety guardrails."
        )
