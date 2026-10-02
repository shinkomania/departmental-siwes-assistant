"""
Academic Hierarchy Identity Resolution
--------------------------------------

E4 read-only resolver for authoritative academic hierarchy records.

This module performs identity resolution only.

It does NOT:
- create database records;
- modify existing records;
- create SIWESConfiguration;
- infer SIWES eligibility;
- publish source data.

Resolution is scoped to the canonical hierarchy:

Institution
    -> AcademicUnit
        -> Department
            -> Programme
"""

from dataclasses import dataclass, field
from typing import List, Optional

from models import AcademicUnit, Department, Institution, Programme
from services.academic_hierarchy_source import (
    AcademicHierarchySourceRecord,
    NormalizedAcademicHierarchySourceRecord,
    normalize_hierarchy_source_record,
)


HIERARCHY_RESULTS = (
    "INVALID",
    "REVIEW_REQUIRED",
    "EXACT_HIERARCHY_MATCH",
    "EXISTING_INSTITUTION",
    "EXISTING_ACADEMIC_UNIT",
    "EXISTING_DEPARTMENT",
    "NEW_ACADEMIC_HIERARCHY",
)


@dataclass(frozen=True)
class AcademicHierarchyResolutionResult:
    """
    Non-mutating hierarchy resolution result.
    """

    result: str

    source_name: str
    external_identifier: Optional[str]
    institution_name: str

    academic_unit_name: Optional[str] = None
    department_name: Optional[str] = None
    programme_name: Optional[str] = None
    programme_award: Optional[str] = None

    matched_institution_id: Optional[int] = None
    matched_institution_name: Optional[str] = None

    matched_academic_unit_id: Optional[int] = None
    matched_academic_unit_name: Optional[str] = None

    matched_department_id: Optional[int] = None
    matched_department_name: Optional[str] = None

    matched_programme_id: Optional[int] = None
    matched_programme_name: Optional[str] = None

    reason: Optional[str] = None
    errors: List[str] = field(default_factory=list)


class AcademicHierarchyIdentityResolver:
    """
    Read-only resolver for the canonical academic hierarchy.
    """

    def __init__(self, session):
        self.session = session

    def resolve(
        self,
        record: AcademicHierarchySourceRecord,
    ) -> AcademicHierarchyResolutionResult:
        """
        Resolve one source hierarchy record without database mutation.
        """

        try:
            normalized = normalize_hierarchy_source_record(record)
        except ValueError as exc:
            return AcademicHierarchyResolutionResult(
                result="INVALID",
                source_name=(record.source_name or "").strip(),
                external_identifier=record.external_identifier,
                institution_name=(record.institution_name or "").strip(),
                reason="Source record validation failed.",
                errors=[str(exc)],
            )

        institution = (
            self.session.query(Institution)
            .filter(
                Institution.normalized_name
                == normalized.normalized_institution_name
            )
            .one_or_none()
        )

        if institution is None:
            return AcademicHierarchyResolutionResult(
                result="NEW_ACADEMIC_HIERARCHY",
                source_name=normalized.source_name,
                external_identifier=normalized.external_identifier,
                institution_name=normalized.institution_name,
                academic_unit_name=normalized.academic_unit_name,
                department_name=normalized.department_name,
                programme_name=normalized.programme_name,
                programme_award=normalized.programme_award,
                reason="No canonical institution matched the source record.",
            )

        if not normalized.academic_unit_name:
            return AcademicHierarchyResolutionResult(
                result="EXISTING_INSTITUTION",
                source_name=normalized.source_name,
                external_identifier=normalized.external_identifier,
                institution_name=normalized.institution_name,
                matched_institution_id=institution.id,
                matched_institution_name=institution.name,
                reason="Canonical institution matched; no academic unit supplied.",
            )

        academic_unit = (
            self.session.query(AcademicUnit)
            .filter(
                AcademicUnit.institution_id == institution.id,
                AcademicUnit.normalized_name
                == normalized.normalized_academic_unit_name,
            )
            .one_or_none()
        )

        if academic_unit is None:
            return AcademicHierarchyResolutionResult(
                result="EXISTING_INSTITUTION",
                source_name=normalized.source_name,
                external_identifier=normalized.external_identifier,
                institution_name=normalized.institution_name,
                academic_unit_name=normalized.academic_unit_name,
                department_name=normalized.department_name,
                programme_name=normalized.programme_name,
                programme_award=normalized.programme_award,
                matched_institution_id=institution.id,
                matched_institution_name=institution.name,
                reason="Institution matched, but academic unit did not.",
            )

        if not normalized.department_name:
            return AcademicHierarchyResolutionResult(
                result="EXISTING_ACADEMIC_UNIT",
                source_name=normalized.source_name,
                external_identifier=normalized.external_identifier,
                institution_name=normalized.institution_name,
                academic_unit_name=normalized.academic_unit_name,
                matched_institution_id=institution.id,
                matched_institution_name=institution.name,
                matched_academic_unit_id=academic_unit.id,
                matched_academic_unit_name=academic_unit.name,
                reason="Academic unit matched; no department supplied.",
            )

        department = (
            self.session.query(Department)
            .filter(
                Department.academic_unit_id == academic_unit.id,
                Department.normalized_name
                == normalized.normalized_department_name,
            )
            .one_or_none()
        )

        if department is None:
            return AcademicHierarchyResolutionResult(
                result="EXISTING_ACADEMIC_UNIT",
                source_name=normalized.source_name,
                external_identifier=normalized.external_identifier,
                institution_name=normalized.institution_name,
                academic_unit_name=normalized.academic_unit_name,
                department_name=normalized.department_name,
                programme_name=normalized.programme_name,
                programme_award=normalized.programme_award,
                matched_institution_id=institution.id,
                matched_institution_name=institution.name,
                matched_academic_unit_id=academic_unit.id,
                matched_academic_unit_name=academic_unit.name,
                reason="Academic unit matched, but department did not.",
            )

        if not normalized.programme_name:
            return AcademicHierarchyResolutionResult(
                result="EXISTING_DEPARTMENT",
                source_name=normalized.source_name,
                external_identifier=normalized.external_identifier,
                institution_name=normalized.institution_name,
                academic_unit_name=normalized.academic_unit_name,
                department_name=normalized.department_name,
                matched_institution_id=institution.id,
                matched_institution_name=institution.name,
                matched_academic_unit_id=academic_unit.id,
                matched_academic_unit_name=academic_unit.name,
                matched_department_id=department.id,
                matched_department_name=department.name,
                reason="Department matched; no programme supplied.",
            )

        programme = (
            self.session.query(Programme)
            .filter(
                Programme.department_id == department.id,
                Programme.normalized_name
                == normalized.normalized_programme_name,
                Programme.normalized_award
                == normalized.normalized_programme_award,
            )
            .one_or_none()
        )

        if programme is None:
            return AcademicHierarchyResolutionResult(
                result="EXISTING_DEPARTMENT",
                source_name=normalized.source_name,
                external_identifier=normalized.external_identifier,
                institution_name=normalized.institution_name,
                academic_unit_name=normalized.academic_unit_name,
                department_name=normalized.department_name,
                programme_name=normalized.programme_name,
                programme_award=normalized.programme_award,
                matched_institution_id=institution.id,
                matched_institution_name=institution.name,
                matched_academic_unit_id=academic_unit.id,
                matched_academic_unit_name=academic_unit.name,
                matched_department_id=department.id,
                matched_department_name=department.name,
                reason="Department matched, but programme did not.",
            )

        return AcademicHierarchyResolutionResult(
            result="EXACT_HIERARCHY_MATCH",
            source_name=normalized.source_name,
            external_identifier=normalized.external_identifier,
            institution_name=normalized.institution_name,
            academic_unit_name=normalized.academic_unit_name,
            department_name=normalized.department_name,
            programme_name=normalized.programme_name,
            programme_award=normalized.programme_award,
            matched_institution_id=institution.id,
            matched_institution_name=institution.name,
            matched_academic_unit_id=academic_unit.id,
            matched_academic_unit_name=academic_unit.name,
            matched_department_id=department.id,
            matched_department_name=department.name,
            matched_programme_id=programme.id,
            matched_programme_name=programme.name,
            reason="Complete canonical hierarchy matched.",
        )

    def dry_run(self, records):
        """
        Resolve multiple records without mutation.
        """
        return [self.resolve(record) for record in records]
