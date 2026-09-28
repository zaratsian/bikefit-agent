"""Session State and Memory Schema for BikeFit Agent.

Defines structured state schemas for tracking rider anthropometrics, current bike specs,
shortlisted candidate frames, and fit solutions across conversation turns.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class BikeFitState(BaseModel):
    """Persistent state memory maintained across user interaction turns."""

    # Rider Anthropometrics & Profile
    rider_height_cm: Optional[float] = Field(default=None, description="Rider standing height in cm")
    rider_inseam_cm: Optional[float] = Field(default=None, description="Rider cycling inseam in cm")
    rider_flexibility: str = Field(default="moderate", description="Rider flexibility: 'low', 'moderate', or 'high'")
    rider_goals: Optional[str] = Field(default=None, description="Primary focus: aero race, endurance comfort, or gravel")

    # Current Baseline Bike Configuration
    current_bike_brand: Optional[str] = Field(default=None, description="Current bike brand")
    current_bike_model: Optional[str] = Field(default=None, description="Current bike model")
    current_bike_size: Optional[str] = Field(default=None, description="Current frame size")
    current_spacer_mm: float = Field(default=20.0, description="Current headset spacer stack in mm")
    current_stem_len_mm: float = Field(default=100.0, description="Current stem length in mm")
    current_stem_angle_deg: float = Field(default=-6.0, description="Current stem angle in degrees")
    current_handlebar_coords: Optional[Dict[str, float]] = Field(default=None, description="Computed (X_bar, Y_bar) in mm")

    # Candidate Target Bikes
    shortlisted_bikes: List[Dict[str, Any]] = Field(default_factory=list, description="Candidate bikes being evaluated")
    
    # Active Comparison & Solution History
    last_solution: Optional[Dict[str, Any]] = Field(default=None, description="Most recently computed cockpit match solution")
    comparison_notes: List[str] = Field(default_factory=list, description="Historical notes on evaluated comparisons")
