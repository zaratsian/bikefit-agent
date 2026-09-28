"""Human-in-the-Loop (HITL) Safety and Approval System.

Requires explicit human confirmation and validation before authorizing irreversible
or high-consequence bicycle cockpit modifications (such as cutting carbon fork steerers,
slammed stem conversions, or extreme posture modifications).
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class HumanApprovalRequest(BaseModel):
    """Schema for a Human-in-the-Loop approval submission."""
    action_type: str = Field(..., description="Type of physical modification (e.g., 'STEERER_TUBE_CUT', 'SLAMMED_STEM', 'EXTREME_REACH')")
    component_details: str = Field(..., description="Exact parts or dimensions being modified")
    risk_level: str = Field(..., description="Assessed risk level: 'LOW', 'MODERATE', or 'HIGH'")
    rationale: str = Field(..., description="Technical rationale for the proposed change")
    user_confirmed: bool = Field(default=False, description="Whether the rider has explicitly approved this change")


class HumanApprovalResponse(BaseModel):
    """Result of Human-in-the-Loop review and authorization."""
    status: str = Field(..., description="'APPROVED', 'REJECTED', or 'AWAITING_CONFIRMATION'")
    requires_user_action: bool = Field(..., description="True if human confirmation is still pending")
    confirmation_prompt: str = Field(..., description="Message presented to human user for verification")
    safety_disclaimer: str = Field(..., description="Legal and physical safety disclaimer")
    authorized_action: Optional[str] = Field(default=None, description="Action allowed if confirmed")


def request_human_approval(
    action_type: str,
    component_details: str,
    risk_level: str,
    rationale: str,
    user_confirmed: bool = False
) -> HumanApprovalResponse:
    """Human-in-the-Loop tool to gate high-risk physical bike alterations behind explicit user confirmation.

    Args:
        action_type: The physical modification category (e.g. 'CUT_STEERER_TUBE', 'EXTREME_STEM_LENGTH').
        component_details: Specific measurements and components (e.g. 'Removing 25mm spacers and cutting steerer').
        risk_level: Risk level ('LOW', 'MODERATE', 'HIGH').
        rationale: Why this alteration is proposed.
        user_confirmed: True only if the user has explicitly verified and approved this action in the chat.

    Returns:
        HumanApprovalResponse: Pydantic model with approval status, prompt, and safety disclaimer.
    """
    disclaimer = (
        "WARNING: Physical modifications to bicycle fork steerer tubes or cockpits are permanent "
        "and can drastically alter bike handling or void manufacturer warranties. Always have critical cuts "
        "and torque specifications verified by a certified professional bike mechanic."
    )

    if user_confirmed:
        return HumanApprovalResponse(
            status="APPROVED",
            requires_user_action=False,
            confirmation_prompt=f"User has explicitly approved {action_type}. Modification authorized to proceed.",
            safety_disclaimer=disclaimer,
            authorized_action=f"Execute: {action_type} - {component_details}"
        )

    # Human confirmation pending
    prompt = (
        f"🚨 HUMAN APPROVAL REQUIRED FOR [{action_type}] (Risk: {risk_level})\n"
        f"Proposed Modification: {component_details}\n"
        f"Reasoning: {rationale}\n"
        f"To proceed, please reply: 'I confirm and approve {action_type}'."
    )

    return HumanApprovalResponse(
        status="AWAITING_CONFIRMATION",
        requires_user_action=True,
        confirmation_prompt=prompt,
        safety_disclaimer=disclaimer,
        authorized_action=None
    )
