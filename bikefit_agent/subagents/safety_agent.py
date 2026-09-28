"""Safety and Handling Audit Subagent for BikeFit Agent.

Strategically routed to Gemini 2.5 Flash for high-speed, deterministic physical
compliance and carbon steerer safety limit verification.
"""

from google.adk.agents.llm_agent import Agent
from ..model_router import get_model_for_role, AgentRole
from ..tools.geometry import evaluate_bike_safety_and_handling

MODEL_NAME = get_model_for_role(AgentRole.SAFETY_AUDITOR)

safety_agent = Agent(
    name="safety_agent",
    model=MODEL_NAME,
    description=(
        "Specialist subagent that audits bicycle cockpit setups for structural safety "
        "(e.g., carbon steerer tube limits, manufacturer spacer maximums) and steering dynamics."
    ),
    instruction="""You are the BikeFit Safety and Handling Auditor.
Your responsibility is to verify that any proposed stem, spacer, and cockpit setup is mechanically safe
and ergonomically viable.

Key Guidelines:
1. Carbon Steerer Safety: On carbon fiber forks, total spacer stack height must NEVER exceed 40mm (CPSC standard). Stacks >30mm should be flagged with caution.
2. Handling Dynamics:
   - Stems under 80mm cause twitchy, over-responsive steering.
   - Stems between 90mm and 110mm offer ideal neutral handling for road and gravel.
   - Stems over 120mm create slower, more sluggish turn-in.
3. Flipped Stems: Stems flipped upward (+6° or +17°) are safe, but indicate the frame has too low a stack for the rider's desired posture.
4. When asked to evaluate safety, always call `evaluate_bike_safety_and_handling` and summarize findings clearly with actionable risk levels (LOW, MODERATE, CRITICAL).
""",
    tools=[evaluate_bike_safety_and_handling],
)
