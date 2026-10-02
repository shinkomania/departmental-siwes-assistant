"""
Academic Hierarchy Source Contract
-----------------------------------

E4 foundation for controlled ingestion of authoritative academic
hierarchy information.

This contract represents:

    Institution -> Academic Unit -> Department -> Programme

It does NOT represent SIWES eligibility.

SIWES configuration remains an independent E3 concern.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from domain.academic_identity import normalize_directory_identity


@dataclass(frozen=True)
class AcademicHierarchySourceRecord:
    """
    Standardized academic hierarchy record produced by a source adapter.

    A record may describe the full hierarchy or only the portion available
    from the authoritative source.
    """

    source_name: str
    source_type: str
    external_identifier: Optional[str]

    institution_name: str

    academic_unit_name: Optional[str] = None
    academic_unit_type: Optional[str] = None

    department_name: Optional[str] = None

    programme_name: Optional[str] = None
    programme_award: Optional[str] = None
    programme_duration_years: Optional[int] = None

    reference_url: Optional[str] = None

    source_snapshot: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedAcademicHierarchySourceRecord:
    """
    Validated and normalized hierarchy source record.

    Original source-facing values are retained while deterministic
    normalized identities are stored separately for matching.
    """

    source_name: str
    source_type: str
    external_identifier: Optional[str]

    institution_name: str
    normalized_institution_name: str

    academic_unit_name: Optional[str] = None
    normalized_academic_unit_name: Optional[str] = None
    academic_unit_type: Optional[str] = None

    department_name: Optional[str] = None
    normalized_department_name: Optional[str] = None

    programme_name: Optional[str] = None
    normalized_programme_name: Optional[str] = None

    programme_award: Optional[str] = None
    normalized_programme_award: str = ""

    programme_duration_years: Optional[int] = None

    reference_url: Optional[str] = None

    source_snapshot: Dict[str, Any] = field(default_factory=dict)


def _optional_clean(value: Optional[str]) -> Optional[str]:
    """Strip optional text values while preserving None."""
    if value is None:
        return None

    cleaned = value.strip()

    return cleaned or None


def normalize_hierarchy_source_record(
    record: AcademicHierarchySourceRecord,
) -> NormalizedAcademicHierarchySourceRecord:
    """
    Validate and normalize an academic hierarchy source record.

    This function performs no database reads or writes.
    """

    errors: List[str] = []

    source_name = (record.source_name or "").strip()
    source_type = (record.source_type or "").strip()
    institution_name = (record.institution_name or "").strip()

    academic_unit_name = _optional_clean(record.academic_unit_name)
    academic_unit_type = _optional_clean(record.academic_unit_type)
    department_name = _optional_clean(record.department_name)
    programme_name = _optional_clean(record.programme_name)
    programme_award = _optional_clean(record.programme_award)
    external_identifier = _optional_clean(record.external_identifier)
    reference_url = _optional_clean(record.reference_url)

    if not source_name:
        errors.append("source_name is required.")

    if not source_type:
        errors.append("source_type is required.")

    if not institution_name:
        errors.append("institution_name is required.")

    if academic_unit_name and not academic_unit_type:
        errors.append(
            "academic_unit_type is required when academic_unit_name is provided."
        )

    if department_name and not academic_unit_name:
        errors.append(
            "academic_unit_name is required when department_name is provided."
        )

    if programme_name and not department_name:
        errors.append(
            "department_name is required when programme_name is provided."
        )

    if record.programme_duration_years is not None:
        if not isinstance(record.programme_duration_years, int):
            errors.append("programme_duration_years must be an integer.")
        elif record.programme_duration_years <= 0:
            errors.append(
                "programme_duration_years must be greater than zero."
            )

    if errors:
        raise ValueError("; ".join(errors))

    normalized_institution_name = normalize_directory_identity(
        institution_name
    )

    normalized_academic_unit_name = (
        normalize_directory_identity(academic_unit_name)
        if academic_unit_name
        else None
    )

    normalized_department_name = (
        normalize_directory_identity(department_name)
        if department_name
        else None
    )

    normalized_programme_name = (
        normalize_directory_identity(programme_name)
        if programme_name
        else None
    )

    normalized_programme_award = (
        normalize_directory_identity(programme_award)
        if programme_award
        else ""
    )

    return NormalizedAcademicHierarchySourceRecord(
        source_name=source_name,
        source_type=source_type,
        external_identifier=external_identifier,
        institution_name=institution_name,
        normalized_institution_name=normalized_institution_name,
        academic_unit_name=academic_unit_name,
        normalized_academic_unit_name=normalized_academic_unit_name,
        academic_unit_type=academic_unit_type,
        department_name=department_name,
        normalized_department_name=normalized_department_name,
        programme_name=programme_name,
        normalized_programme_name=normalized_programme_name,
        programme_award=programme_award,
        normalized_programme_award=normalized_programme_award,
        programme_duration_years=record.programme_duration_years,
        reference_url=reference_url,
        source_snapshot=dict(record.source_snapshot),
    )
