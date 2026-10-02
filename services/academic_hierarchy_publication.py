"""
E4 Controlled Academic Hierarchy Publication Service.

Publishes authoritative academic structure:

    Institution -> AcademicUnit -> Department -> Programme

Important boundaries:
- One source record may produce identities for multiple hierarchy targets.
- The source external identifier is attached to the institution identity only.
- Lower hierarchy identities use their own scoped normalized names.
- Existing identities are recognized and do not cause false conflicts.
- Existing hierarchy records are never duplicated.
- SIWESConfiguration is never created or modified.
- Verification status is never automatically upgraded.
- The caller owns the transaction and must explicitly commit.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from domain.academic_identity import normalize_directory_identity
from models import (
    AcademicDirectorySourceIdentity,
    AcademicUnit,
    DataSource,
    Department,
    Institution,
    Programme,
    SourceEvidence,
)
from services.academic_hierarchy_source import (
    AcademicHierarchySourceRecord,
    normalize_hierarchy_source_record,
)


@dataclass(frozen=True)
class AcademicHierarchyPublicationResult:
    result: str

    institution_id: Optional[int] = None
    academic_unit_id: Optional[int] = None
    department_id: Optional[int] = None
    programme_id: Optional[int] = None

    institution_name: Optional[str] = None
    academic_unit_name: Optional[str] = None
    department_name: Optional[str] = None
    programme_name: Optional[str] = None

    created_institution: bool = False
    created_academic_unit: bool = False
    created_department: bool = False
    created_programme: bool = False

    created_source_identities: int = 0
    created_evidence: int = 0

    dry_run: bool = False
    reason: Optional[str] = None
    errors: List[str] = field(default_factory=list)


class AcademicHierarchyPublicationError(Exception):
    """Raised when authoritative hierarchy publication is ambiguous."""


class AcademicHierarchyPublicationService:

    TARGET_COLUMNS = {
        "Institution": "institution_id",
        "AcademicUnit": "academic_unit_id",
        "Department": "department_id",
        "Programme": "programme_id",
    }

    def __init__(self, session):
        self.session = session

    # ---------------------------------------------------------------
    # Canonical hierarchy lookup
    # ---------------------------------------------------------------

    def _find_institution(self, normalized_name):
        matches = (
            self.session.query(Institution)
            .filter(
                Institution.normalized_name == normalized_name,
            )
            .all()
        )

        if len(matches) > 1:
            raise AcademicHierarchyPublicationError(
                "Multiple institutions share the same normalized identity."
            )

        return matches[0] if matches else None

    def _find_academic_unit(self, institution_id, normalized_name):
        matches = (
            self.session.query(AcademicUnit)
            .filter(
                AcademicUnit.institution_id == institution_id,
                AcademicUnit.normalized_name == normalized_name,
            )
            .all()
        )

        if len(matches) > 1:
            raise AcademicHierarchyPublicationError(
                "Multiple academic units share the same scoped identity."
            )

        return matches[0] if matches else None

    def _find_department(self, academic_unit_id, normalized_name):
        matches = (
            self.session.query(Department)
            .filter(
                Department.academic_unit_id == academic_unit_id,
                Department.normalized_name == normalized_name,
            )
            .all()
        )

        if len(matches) > 1:
            raise AcademicHierarchyPublicationError(
                "Multiple departments share the same scoped identity."
            )

        return matches[0] if matches else None

    def _find_programme(
        self,
        department_id,
        normalized_name,
        normalized_award,
    ):
        matches = (
            self.session.query(Programme)
            .filter(
                Programme.department_id == department_id,
                Programme.normalized_name == normalized_name,
                Programme.normalized_award == normalized_award,
            )
            .all()
        )

        if len(matches) > 1:
            raise AcademicHierarchyPublicationError(
                "Multiple programmes share the same scoped identity."
            )

        return matches[0] if matches else None

    # ---------------------------------------------------------------
    # Source identity lookup
    # ---------------------------------------------------------------

    def _find_target_identity(
        self,
        data_source_id,
        target_column,
        target_id,
        external_name,
    ):
        normalized_name = normalize_directory_identity(
            external_name
        )

        matches = (
            self.session.query(AcademicDirectorySourceIdentity)
            .filter(
                AcademicDirectorySourceIdentity.data_source_id
                == data_source_id,
                getattr(
                    AcademicDirectorySourceIdentity,
                    target_column,
                )
                == target_id,
                AcademicDirectorySourceIdentity.normalized_external_name
                == normalized_name,
            )
            .all()
        )

        if len(matches) > 1:
            raise AcademicHierarchyPublicationError(
                "Multiple source identity mappings exist for the same target."
            )

        return matches[0] if matches else None

    def _find_identifier_identity(
        self,
        data_source_id,
        external_identifier,
    ):
        if not external_identifier:
            return None

        matches = (
            self.session.query(AcademicDirectorySourceIdentity)
            .filter(
                AcademicDirectorySourceIdentity.data_source_id
                == data_source_id,
                AcademicDirectorySourceIdentity.external_identifier
                == external_identifier,
            )
            .all()
        )

        if len(matches) > 1:
            raise AcademicHierarchyPublicationError(
                "Multiple source identity mappings share the same "
                "authoritative external identifier."
            )

        return matches[0] if matches else None

    # ---------------------------------------------------------------
    # Identity/evidence creation
    # ---------------------------------------------------------------

    def _ensure_identity(
        self,
        *,
        data_source_id,
        external_identifier,
        external_name,
        reference_url,
        target_column,
        target_id,
    ):
        existing = self._find_target_identity(
            data_source_id,
            target_column,
            target_id,
            external_name,
        )

        if existing is not None:
            return existing, False

        identity = AcademicDirectorySourceIdentity(
            data_source_id=data_source_id,
            external_identifier=external_identifier,
            external_name=external_name,
            normalized_external_name=normalize_directory_identity(
                external_name
            ),
            reference_url=reference_url,
            **{
                target_column: target_id,
            },
        )

        self.session.add(identity)
        self.session.flush()

        return identity, True

    def _ensure_evidence(
        self,
        *,
        data_source_id,
        target_column,
        target_id,
        reference_url,
        reference_text,
    ):
        """
        Create one Academic Structure evidence record for this target/source
        combination if one does not already exist.
        """

        existing = (
            self.session.query(SourceEvidence)
            .filter(
                SourceEvidence.data_source_id == data_source_id,
                SourceEvidence.claim_type == "Academic Structure",
                getattr(
                    SourceEvidence,
                    target_column,
                )
                == target_id,
                SourceEvidence.reference_url == reference_url,
                SourceEvidence.reference_text == reference_text,
            )
            .first()
        )

        if existing is not None:
            return existing, False

        evidence = SourceEvidence(
            data_source_id=data_source_id,
            claim_type="Academic Structure",
            reference_url=reference_url,
            reference_text=reference_text,
            **{
                target_column: target_id,
            },
        )

        self.session.add(evidence)
        self.session.flush()

        return evidence, True

    # ---------------------------------------------------------------
    # Publication
    # ---------------------------------------------------------------

    def publish(
        self,
        record: AcademicHierarchySourceRecord,
        *,
        data_source_id: int,
        dry_run: bool = False,
    ):
        try:
            normalized = normalize_hierarchy_source_record(record)
        except ValueError as exc:
            return AcademicHierarchyPublicationResult(
                result="INVALID",
                reason="Source validation failed.",
                errors=[str(exc)],
                dry_run=dry_run,
            )

        source = self.session.get(
            DataSource,
            data_source_id,
        )

        if source is None:
            return AcademicHierarchyPublicationResult(
                result="DATA_SOURCE_NOT_FOUND",
                reason="The supplied DataSource does not exist.",
                errors=[
                    f"Unknown DataSource id={data_source_id}."
                ],
                dry_run=dry_run,
            )

        if not source.is_active:
            return AcademicHierarchyPublicationResult(
                result="DATA_SOURCE_NOT_FOUND",
                reason="The supplied DataSource is inactive.",
                errors=[
                    f"DataSource id={data_source_id} is inactive."
                ],
                dry_run=dry_run,
            )

        # -----------------------------------------------------------
        # Existing authoritative identifier check
        #
        # The source identifier identifies the source record itself.
        # It is attached to the Institution identity only.
        #
        # If it already maps to the same institution, publication
        # continues normally through the lower hierarchy.
        # -----------------------------------------------------------

        existing_identifier_identity = (
            self._find_identifier_identity(
                data_source_id,
                normalized.external_identifier,
            )
        )

        institution = self._find_institution(
            normalized.normalized_institution_name
        )

        if existing_identifier_identity is not None:
            existing_institution_id = (
                existing_identifier_identity.institution_id
            )

            # external_identifier is unique within a DataSource.
            # Therefore, if it already belongs to another institution,
            # stop before attempting an INSERT that would violate the
            # database uniqueness constraint.
            if existing_institution_id is not None:
                if (
                    institution is None
                    or existing_institution_id != institution.id
                ):
                    return AcademicHierarchyPublicationResult(
                        result="REVIEW_REQUIRED",
                        reason=(
                            "The authoritative external identifier is "
                            "already mapped to a different institution."
                        ),
                        errors=[
                            "External identifier conflict requires review."
                        ],
                        dry_run=dry_run,
                    )

            # Defensive protection against a malformed identity that
            # points to a lower hierarchy target instead of an institution.
            elif institution is not None:
                return AcademicHierarchyPublicationResult(
                    result="REVIEW_REQUIRED",
                    reason=(
                        "The authoritative external identifier is already "
                        "mapped to a different hierarchy target."
                    ),
                    errors=[
                        "External identifier target conflict requires review."
                    ],
                    dry_run=dry_run,
                )

        created_institution = False
        created_academic_unit = False
        created_department = False
        created_programme = False

        created_source_identities = 0
        created_evidence = 0

        # -----------------------------------------------------------
        # Institution
        # -----------------------------------------------------------

        if institution is None:
            if dry_run:
                return AcademicHierarchyPublicationResult(
                    result="DRY_RUN_NEW_HIERARCHY",
                    institution_name=normalized.institution_name,
                    academic_unit_name=normalized.academic_unit_name,
                    department_name=normalized.department_name,
                    programme_name=normalized.programme_name,
                    reason=(
                        "Publication would create the institution and "
                        "the supplied lower hierarchy."
                    ),
                    dry_run=True,
                )

            institution = Institution(
                name=normalized.institution_name,
                institution_type="Other",
                directory_status="Pending Verification",
            )

            self.session.add(institution)
            self.session.flush()

            created_institution = True

        # -----------------------------------------------------------
        # Institution identity/evidence
        # -----------------------------------------------------------

        if not dry_run:
            institution_identity, identity_created = self._ensure_identity(
                data_source_id=data_source_id,
                external_identifier=normalized.external_identifier,
                external_name=normalized.institution_name,
                reference_url=normalized.reference_url,
                target_column="institution_id",
                target_id=institution.id,
            )

            if identity_created:
                created_source_identities += 1

            _, evidence_created = self._ensure_evidence(
                data_source_id=data_source_id,
                target_column="institution_id",
                target_id=institution.id,
                reference_url=normalized.reference_url,
                reference_text=normalized.institution_name,
            )

            if evidence_created:
                created_evidence += 1

        # -----------------------------------------------------------
        # No academic unit
        # -----------------------------------------------------------

        if not normalized.academic_unit_name:
            if dry_run:
                return AcademicHierarchyPublicationResult(
                    result="DRY_RUN_EXISTING_HIERARCHY",
                    institution_id=institution.id,
                    institution_name=institution.name,
                    reason=(
                        "Institution exists; no academic unit was supplied."
                    ),
                    dry_run=True,
                )

            return AcademicHierarchyPublicationResult(
                result="PUBLISHED",
                institution_id=institution.id,
                institution_name=institution.name,
                created_institution=created_institution,
                created_source_identities=created_source_identities,
                created_evidence=created_evidence,
                reason="Institution publication completed.",
            )

        # -----------------------------------------------------------
        # Academic Unit
        # -----------------------------------------------------------

        academic_unit = self._find_academic_unit(
            institution.id,
            normalized.normalized_academic_unit_name,
        )

        if academic_unit is None:
            if dry_run:
                return AcademicHierarchyPublicationResult(
                    result="DRY_RUN_NEW_HIERARCHY",
                    institution_id=institution.id,
                    institution_name=institution.name,
                    academic_unit_name=normalized.academic_unit_name,
                    department_name=normalized.department_name,
                    programme_name=normalized.programme_name,
                    reason="Academic unit would be created.",
                    dry_run=True,
                )

            academic_unit = AcademicUnit(
                institution_id=institution.id,
                name=normalized.academic_unit_name,
                unit_type=normalized.academic_unit_type,
            )

            self.session.add(academic_unit)
            self.session.flush()

            created_academic_unit = True

        if not dry_run:
            _, identity_created = self._ensure_identity(
                data_source_id=data_source_id,
                external_identifier=None,
                external_name=normalized.academic_unit_name,
                reference_url=normalized.reference_url,
                target_column="academic_unit_id",
                target_id=academic_unit.id,
            )

            if identity_created:
                created_source_identities += 1

            _, evidence_created = self._ensure_evidence(
                data_source_id=data_source_id,
                target_column="academic_unit_id",
                target_id=academic_unit.id,
                reference_url=normalized.reference_url,
                reference_text=normalized.academic_unit_name,
            )

            if evidence_created:
                created_evidence += 1

        # -----------------------------------------------------------
        # No department
        # -----------------------------------------------------------

        if not normalized.department_name:
            if dry_run:
                return AcademicHierarchyPublicationResult(
                    result="DRY_RUN_EXISTING_HIERARCHY",
                    institution_id=institution.id,
                    academic_unit_id=academic_unit.id,
                    institution_name=institution.name,
                    academic_unit_name=academic_unit.name,
                    reason=(
                        "Academic unit exists; no department was supplied."
                    ),
                    dry_run=True,
                )

            return AcademicHierarchyPublicationResult(
                result="PUBLISHED",
                institution_id=institution.id,
                academic_unit_id=academic_unit.id,
                institution_name=institution.name,
                academic_unit_name=academic_unit.name,
                created_institution=created_institution,
                created_academic_unit=created_academic_unit,
                created_source_identities=created_source_identities,
                created_evidence=created_evidence,
                reason="Academic unit publication completed.",
            )

        # -----------------------------------------------------------
        # Department
        # -----------------------------------------------------------

        department = self._find_department(
            academic_unit.id,
            normalized.normalized_department_name,
        )

        if department is None:
            if dry_run:
                return AcademicHierarchyPublicationResult(
                    result="DRY_RUN_NEW_HIERARCHY",
                    institution_id=institution.id,
                    academic_unit_id=academic_unit.id,
                    institution_name=institution.name,
                    academic_unit_name=academic_unit.name,
                    department_name=normalized.department_name,
                    programme_name=normalized.programme_name,
                    reason="Department would be created.",
                    dry_run=True,
                )

            department = Department(
                academic_unit_id=academic_unit.id,
                name=normalized.department_name,
            )

            self.session.add(department)
            self.session.flush()

            created_department = True

        if not dry_run:
            _, identity_created = self._ensure_identity(
                data_source_id=data_source_id,
                external_identifier=None,
                external_name=normalized.department_name,
                reference_url=normalized.reference_url,
                target_column="department_id",
                target_id=department.id,
            )

            if identity_created:
                created_source_identities += 1

            _, evidence_created = self._ensure_evidence(
                data_source_id=data_source_id,
                target_column="department_id",
                target_id=department.id,
                reference_url=normalized.reference_url,
                reference_text=normalized.department_name,
            )

            if evidence_created:
                created_evidence += 1

        # -----------------------------------------------------------
        # No programme
        # -----------------------------------------------------------

        if not normalized.programme_name:
            if dry_run:
                return AcademicHierarchyPublicationResult(
                    result="DRY_RUN_EXISTING_HIERARCHY",
                    institution_id=institution.id,
                    academic_unit_id=academic_unit.id,
                    department_id=department.id,
                    institution_name=institution.name,
                    academic_unit_name=academic_unit.name,
                    department_name=department.name,
                    reason=(
                        "Department exists; no programme was supplied."
                    ),
                    dry_run=True,
                )

            return AcademicHierarchyPublicationResult(
                result="PUBLISHED",
                institution_id=institution.id,
                academic_unit_id=academic_unit.id,
                department_id=department.id,
                institution_name=institution.name,
                academic_unit_name=academic_unit.name,
                department_name=department.name,
                created_institution=created_institution,
                created_academic_unit=created_academic_unit,
                created_department=created_department,
                created_source_identities=created_source_identities,
                created_evidence=created_evidence,
                reason="Department publication completed.",
            )

        # -----------------------------------------------------------
        # Programme
        # -----------------------------------------------------------

        programme = self._find_programme(
            department.id,
            normalized.normalized_programme_name,
            normalized.normalized_programme_award,
        )

        if programme is None:
            if dry_run:
                return AcademicHierarchyPublicationResult(
                    result="DRY_RUN_NEW_HIERARCHY",
                    institution_id=institution.id,
                    academic_unit_id=academic_unit.id,
                    department_id=department.id,
                    institution_name=institution.name,
                    academic_unit_name=academic_unit.name,
                    department_name=department.name,
                    programme_name=normalized.programme_name,
                    reason="Programme would be created.",
                    dry_run=True,
                )

            programme = Programme(
                department_id=department.id,
                name=normalized.programme_name,
                award=normalized.programme_award,
                duration_years=normalized.programme_duration_years,
            )

            self.session.add(programme)
            self.session.flush()

            created_programme = True

        if dry_run:
            return AcademicHierarchyPublicationResult(
                result="DRY_RUN_EXISTING_HIERARCHY",
                institution_id=institution.id,
                academic_unit_id=academic_unit.id,
                department_id=department.id,
                programme_id=programme.id,
                institution_name=institution.name,
                academic_unit_name=academic_unit.name,
                department_name=department.name,
                programme_name=programme.name,
                reason="Complete hierarchy is resolvable.",
                dry_run=True,
            )

        # Programme identity/evidence
        _, identity_created = self._ensure_identity(
            data_source_id=data_source_id,
            external_identifier=None,
            external_name=normalized.programme_name,
            reference_url=normalized.reference_url,
            target_column="programme_id",
            target_id=programme.id,
        )

        if identity_created:
            created_source_identities += 1

        _, evidence_created = self._ensure_evidence(
            data_source_id=data_source_id,
            target_column="programme_id",
            target_id=programme.id,
            reference_url=normalized.reference_url,
            reference_text=normalized.programme_name,
        )

        if evidence_created:
            created_evidence += 1

        return AcademicHierarchyPublicationResult(
            result="PUBLISHED",
            institution_id=institution.id,
            academic_unit_id=academic_unit.id,
            department_id=department.id,
            programme_id=programme.id,
            institution_name=institution.name,
            academic_unit_name=academic_unit.name,
            department_name=department.name,
            programme_name=programme.name,
            created_institution=created_institution,
            created_academic_unit=created_academic_unit,
            created_department=created_department,
            created_programme=created_programme,
            created_source_identities=created_source_identities,
            created_evidence=created_evidence,
            reason="Complete academic hierarchy publication completed.",
        )
