"""
Server-side calculator endpoints — protects proprietary algorithm
constants (POLARIS driver weights, clamp logic) from being exposed in
client-side HTML/JS.

Inputs are user slider values. Outputs are formatted numbers ready
for direct display. The 5 demand-driver weights live ONLY here.
"""
from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field, conlist


# ============================================================
# POLARIS — Strategic Pricing Engine (hotel pricing calculator)
#   PROPRIETARY: the 5 driver weights are server-side constants.
#   They are never returned to the client.
# ============================================================

# Order: cross_border, holiday_compression, weekend_effect,
#        ota_booking_pace, competitive_saturation
_POLARIS_WEIGHTS: List[float] = [0.18, 0.16, 0.14, 0.12, 0.12]


class POLARISInput(BaseModel):
    base: float = Field(..., ge=0, le=20000, description="Floor / base rate")
    ceiling: float = Field(..., ge=0, le=50000)
    occupancy: float = Field(..., ge=0, le=100, description="0-100 (percent)")
    max_uplift: float = Field(..., ge=0, le=100, description="0-100 (percent)")
    intensities: conlist(float, min_length=5, max_length=5) = Field(
        ..., description="5 intensity values, each 0-100"
    )


class POLARISResult(BaseModel):
    rate: float                  # recommended rate (already clamped)
    revpar: float                # rate × occupancy
    hit_ceiling: bool
    # Chart trajectory: 11 points showing rate as overall demand goes 0→100.
    # The underlying weights are NOT included.
    trajectory: List[float]


def compute_polaris(payload: POLARISInput) -> POLARISResult:
    base = max(0.0, payload.base)
    ceil_ = max(base, payload.ceiling)
    occ = payload.occupancy / 100.0
    max_up = payload.max_uplift / 100.0

    # Weighted demand index (intensities are %; weights are server-side constants)
    w_sum = sum(_POLARIS_WEIGHTS)
    contrib = sum(
        w * (intensity / 100.0)
        for w, intensity in zip(_POLARIS_WEIGHTS, payload.intensities)
    )
    demand_index = (contrib / w_sum) if w_sum > 0 else 0.0

    raw = base * (1.0 + max_up * demand_index)
    rate = min(max(raw, base), ceil_)
    hit_ceiling = raw > ceil_ + 0.5

    # Trajectory: a curve showing recommended rate as a hypothetical
    # "overall demand" parameter ramps 0 → 1. Used only for the visualisation
    # — does not disclose the 5 weights.
    trajectory = [
        min(base * (1.0 + max_up * (i / 10.0)), ceil_) for i in range(11)
    ]

    return POLARISResult(
        rate=round(rate, 2),
        revpar=round(rate * occ, 2),
        hit_ceiling=hit_ceiling,
        trajectory=[round(t, 2) for t in trajectory],
    )


# ============================================================
# OTA True Cost Calculator
#   Pure cost layering, industry-standard math — but moving server-side
#   for visual consistency with POLARIS (same "no client formulas" stance).
# ============================================================

class OTAInput(BaseModel):
    adr: float = Field(..., ge=0, le=100000, description="Average daily rate")
    bookings: float = Field(..., ge=0, le=1_000_000, description="OTA bookings per month")
    commission: float = Field(..., ge=0, le=100, description="Base commission %")
    preferred: float = Field(..., ge=0, le=100, description="Preferred Partner fee %")
    genius: float = Field(..., ge=0, le=100, description="Genius / loyalty discount %")
    payment: float = Field(..., ge=0, le=100, description="Payment processing %")


class OTAResult(BaseModel):
    total_rate_pct: float        # all-in cost as % of ADR
    total_per_booking: float     # absolute cost per booking
    monthly_loss: float
    annual_loss: float
    annual_recoverable_60pct: float    # for the "shift 60% to direct" message
    monthly_savings_20pct: float       # for the "shift 20% to direct" message
    severity: str                # "high" | "medium" | "low"


def compute_ota(payload: OTAInput) -> OTAResult:
    c = payload.commission / 100.0
    p = payload.preferred / 100.0
    g = payload.genius / 100.0
    py_ = payload.payment / 100.0

    d_adr = payload.adr * (1.0 - g)           # ADR after Genius discount
    comm_amt = d_adr * c
    pref_amt = d_adr * p
    pay_amt = d_adr * py_
    total_per = comm_amt + pref_amt + pay_amt + (payload.adr - d_adr)

    total_rate = (total_per / payload.adr * 100.0) if payload.adr > 0 else 0.0
    monthly = total_per * payload.bookings
    annual = monthly * 12.0

    if total_rate >= 28:
        severity = "high"
    elif total_rate >= 22:
        severity = "medium"
    else:
        severity = "low"

    return OTAResult(
        total_rate_pct=round(total_rate, 1),
        total_per_booking=round(total_per, 2),
        monthly_loss=round(monthly, 2),
        annual_loss=round(annual, 2),
        annual_recoverable_60pct=round(annual * 0.6, 2),
        monthly_savings_20pct=round(monthly * 0.2, 2),
        severity=severity,
    )
