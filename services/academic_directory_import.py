"""
Academic Directory Import Service
----------------------------------
E2.1 foundation for controlled national-directory ingestion.

This module deliberately separates:

1. Source-record validation
2. Canonical identity normalization
3. Existing source-identity matching
4. Canonical institution matching
5. Dry-run classification

This first implementation performs NO database writes.

Database publication, DataSource creation, SourceEvidence creation,
AcademicDirectorySourceIdentity creation, and automatic verification
remain controlled later-stage operations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from domain.academic_identity import normalize_directory_identity
from models import (
    AcademicDirectorySourceIdentity,
    Institution,
)


IMPORT_RESULTS = (
    "INVALID",
    "REVIEW_REQUIRED",
    "EXISTING_SOURCE_IDENTITY",
    "EXACT_CANONICAL_MATCH",
    "NEW_INSTITUTION",
)


@dataclass(frozen=True)
class AcademicDirectorySourceRecord:
    """
    Standardized record produced by an authoritative source adapter.

    Source-specific adapters should convert their native records into this
    structure before passing them to the import service.
    """

    source_name: str
    source_type: str
    external_identifier: Optional[str]
    external_name: str

    institution_type: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    official_website: Optional[str] = None
    reference_url: Optional[str] = None

    source_snapshot: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedAcademicDirectorySourceRecord:
    """
    Validated/normalized representation of a source record.

    The original source-facing values are retained while the canonical
    matching value is stored separately.
    """

    source_name: str
    source_type: str
    external_identifier: Optional[str]
    external_name: str
    normalized_external_name: str

    institution_type: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    official_website: Optional[str] = None
    reference_url: Optional[str] = None

    source_snapshot: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AcademicDirectoryImportResult:
    """
    Non-mutating result produced by the dry-run resolver.
    """

    result: str
    source_name: str
    external_identifier: Optional[str]
    external_name: str
    normalized_external_name: Optional[str]

    matched_institution_id: Optional[int] = None
    matched_institution_name: Optional[str] = None

    reason: Optional[str] = None

    errors: List[str] = field(default_factory=list)


def normalize_source_record(
    record: AcademicDirectorySourceRecord,
) -> NormalizedAcademicDirectorySourceRecord:
    """
    Validate and normalize a source record without touching the database.
    """

    errors = []

    source_name = (record.source_name or "").strip()
    source_type = (record.source_type or "").strip()
    external_name = (record.external_name or "").strip()

    if not source_name:
        errors.append("source_name is required.")

    if not source_type:
        errors.append("source_type is required.")

    if not external_name:
        errors.append("external_name is required.")

    if errors:
        raise ValueError(" ".join(errors))

    external_identifier = record.external_identifier

    if external_identifier is not None:
        external_identifier = external_identifier.strip() or None

    normalized_external_name = normalize_directory_identity(
        external_name
    )

    return NormalizedAcademicDirectorySourceRecord(
        source_name=source_name,
        source_type=source_type,
        external_identifier=external_identifier,
        external_name=external_name,
        normalized_external_name=normalized_external_name,
        institution_type=(
            record.institution_type.strip()
            if record.institution_type
            else None
        ),
        city=record.city.strip() if record.city else None,
        state=record.state.strip() if record.state else None,
        official_website=(
            record.official_website.strip()
            if record.official_website
            else None
        ),
        reference_url=(
            record.reference_url.strip()
            if record.reference_url
            else None
        ),
        source_snapshot=dict(record.source_snapshot or {}),
    )


class AcademicDirectoryImportService:
    """
    Read-only E2.1 directory resolver.

    This service intentionally does not create, update, delete, verify,
    publish, or SIWES-enable records.
    """

    def __init__(self, session):
        self.session = session

    def resolve(
        self,
        record: AcademicDirectorySourceRecord,
        *,
        data_source_id: Optional[int] = None,
    ) -> AcademicDirectoryImportResult:
        """
        Resolve one source record without modifying the database.
        """

        try:
            normalized = normalize_source_record(record)
        except ValueError as exc:
            return AcademicDirectoryImportResult(
                result="INVALID",
                source_name=(record.source_name or "").strip(),
                external_identifier=record.external_identifier,
                external_name=(record.external_name or "").strip(),
                normalized_external_name=None,
                reason="Source record validation failed.",
                errors=[str(exc)],
            )

        if data_source_id is not None and normalized.external_identifier:
            existing_identity = (
                self.session.query(AcademicDirectorySourceIdentity)
                .filter(
                    AcademicDirectorySourceIdentity.data_source_id
                    == data_source_id,
                    AcademicDirectorySourceIdentity.external_identifier
                    == normalized.external_identifier,
                )
                .first()
            )

            if existing_identity is not None:
                institution = None

                if existing_identity.institution_id is not None:
                    institution = self.session.get(
                        Institution,
                        existing_identity.institution_id,
                    )

                return AcademicDirectoryImportResult(
                    result="EXISTING_SOURCE_IDENTITY",
                    source_name=normalized.source_name,
                    external_identifier=normalized.external_identifier,
                    external_name=normalized.external_name,
                    normalized_external_name=(
                        normalized.normalized_external_name
                    ),
                    matched_institution_id=(
                        institution.id if institution else None
                    ),
                    matched_institution_name=(
                        institution.name if institution else None
                    ),
                    reason=(
                        "Source identity already exists for this "
                        "authoritative source and external identifier."
                    ),
                )

        matches = (
            self.session.query(Institution)
            .filter(
                Institution.normalized_name
                == normalized.normalized_external_name
            )
            .all()
        )

        if len(matches) == 1:
            institution = matches[0]

            return AcademicDirectoryImportResult(
                result="EXACT_CANONICAL_MATCH",
                source_name=normalized.source_name,
                external_identifier=normalized.external_identifier,
                external_name=normalized.external_name,
                normalized_external_name=(
                    normalized.normalized_external_name
                ),
                matched_institution_id=institution.id,
                matched_institution_name=institution.name,
                reason=(
                    "The normalized authoritative source name matches "
                    "one canonical DSA institution."
                ),
            )

        if len(matches) > 1:
            return AcademicDirectoryImportResult(
                result="REVIEW_REQUIRED",
                source_name=normalized.source_name,
                external_identifier=normalized.external_identifier,
                external_name=normalized.external_name,
                normalized_external_name=(
                    normalized.normalized_external_name
                ),
                reason=(
                    "Multiple canonical institutions matched the same "
                    "normalized identity."
                ),
                errors=[
                    "Canonical identity collision requires review."
                ],
            )

        return AcademicDirectoryImportResult(
            result="NEW_INSTITUTION",
            source_name=normalized.source_name,
            external_identifier=normalized.external_identifier,
            external_name=normalized.external_name,
            normalized_external_name=(
                normalized.normalized_external_name
            ),
            reason=(
                "No existing source identity or canonical institution "
                "matched this source record."
            ),
        )

    def dry_run(
        self,
        records: Iterable[AcademicDirectorySourceRecord],
        *,
        data_source_id: Optional[int] = None,
    ) -> List[AcademicDirectoryImportResult]:
        """
        Resolve multiple records without database mutation.
        """

        return [
            self.resolve(
                record,
                data_source_id=data_source_id,
            )
            for record in records
        ]


def summarize_results(
    results: Iterable[AcademicDirectoryImportResult],
) -> Dict[str, int]:
    """
    Produce deterministic counts suitable for dry-run reporting.
    """

    summary = {
        result_type: 0
        for result_type in IMPORT_RESULTS
    }

    for result in results:
        summary[result.result] = summary.get(result.result, 0) + 1

    summary["TOTAL"] = sum(summary.values())

    return summary
