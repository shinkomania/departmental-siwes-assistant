"""
DSA SIWES Eligibility Service
==============================

Central source of truth for determining whether a student's
programme is currently configured for SIWES.

Important:
- Programme SIWES status is separate from employer/placement intake.
- Pending or missing configuration is never treated as confirmed SIWES.
- Institution-specific rules remain data-driven.
"""

from dataclasses import dataclass

from models.academic import SIWESConfiguration


@dataclass(frozen=True)
class SIWESEligibilityResult:
    """Normalized SIWES eligibility decision."""

    eligible: bool
    status: str
    configuration: object | None
    reason: str


def get_siwes_eligibility(programme):
    """
    Determine SIWES eligibility for a programme.

    Returns a normalized SIWESEligibilityResult so callers do not
    need to duplicate SIWES status interpretation.
    """

    if programme is None:
        return SIWESEligibilityResult(
            eligible=False,
            status="Pending Verification",
            configuration=None,
            reason="No programme has been selected.",
        )

    configuration = getattr(
        programme,
        "siwes_configuration",
        None,
    )

    if configuration is None:
        return SIWESEligibilityResult(
            eligible=False,
            status="Pending Verification",
            configuration=None,
            reason=(
                "SIWES configuration for this programme has not "
                "been established."
            ),
        )

    status = configuration.siwes_status

    if status == "Required":
        return SIWESEligibilityResult(
            eligible=True,
            status=status,
            configuration=configuration,
            reason="SIWES is required for this programme.",
        )

    if status == "Optional":
        return SIWESEligibilityResult(
            eligible=True,
            status=status,
            configuration=configuration,
            reason="SIWES is available for this programme.",
        )

    if status == "No SIWES":
        return SIWESEligibilityResult(
            eligible=False,
            status=status,
            configuration=configuration,
            reason="SIWES is not configured for this programme.",
        )

    return SIWESEligibilityResult(
        eligible=False,
        status=status or "Pending Verification",
        configuration=configuration,
        reason=(
            "SIWES eligibility for this programme has not yet "
            "been verified."
        ),
    )
