"""
Academic Directory Publication Service
--------------------------------------

E2.2 controlled publication boundary for authoritative academic-directory
source records.

Responsibilities:
    1. Accept a validated E2.1 importer result.
    2. Publish only exact canonical matches and genuinely new institutions.
    3. Create source-scoped identity records.
    4. Create provenance evidence for successful publication.
    5. Keep newly published institutions Pending Verification.
    6. Never infer or modify SIWES configuration.
    7. Never automatically mark imported institutions Verified.
    8. Never publish ambiguous importer results.

The service does not commit the SQLAlchemy session. The caller owns the
transaction boundary and may commit or roll back the work.

Dry-run mode performs all validation and resolution checks but creates no
database records.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from domain.academic_identity import normalize_directory_identity

from models import (
    AcademicDirectorySourceIdentity,
    DataSource,
    Institution,
    SourceEvidence,
)

from services.academic_directory_import import (
    AcademicDirectoryImportResult,
    AcademicDirectorySourceRecord,
)


PUBLICATION_RESULTS = (
    "INVALID",
    "REJECTED_RESULT",
    "DATA_SOURCE_NOT_FOUND",
    "EXISTING_SOURCE_IDENTITY",
    "EXACT_CANONICAL_MATCH_PUBLISHED",
    "NEW_INSTITUTION_PUBLISHED",
    "DRY_RUN_EXACT_CANONICAL_MATCH",
    "DRY_RUN_NEW_INSTITUTION",
)


@dataclass(frozen=True)
class AcademicDirectoryPublicationResult:
    """
    Result returned by the controlled publication service.
    """

    result: str
    institution_id: Optional[int] = None
    institution_name: Optional[str] = None
    source_identity_id: Optional[int] = None
    evidence_id: Optional[int] = None

    reason: Optional[str] = None
    errors: List[str] = field(default_factory=list)

    created_institution: bool = False
    created_source_identity: bool = False
    created_evidence: bool = False
    dry_run: bool = False


class AcademicDirectoryPublicationError(Exception):
    """Raised when publication cannot safely proceed."""


class AcademicDirectoryPublicationService:
    """
    Controlled E2.2 publication service.

    The service intentionally does not commit the database session.
    """

    PUBLISHABLE_IMPORT_RESULTS = {
        "EXACT_CANONICAL_MATCH",
        "NEW_INSTITUTION",
    }

    def __init__(self, session):
        self.session = session

    def publish(
        self,
        record: AcademicDirectorySourceRecord,
        import_result: AcademicDirectoryImportResult,
        *,
        data_source_id: int,
        dry_run: bool = False,
    ) -> AcademicDirectoryPublicationResult:
        """
        Publish one validated importer result.

        The caller owns the transaction. This method never calls commit().

        Safe publication rules:
            - INVALID results are rejected.
            - REVIEW_REQUIRED results are rejected.
            - EXISTING_SOURCE_IDENTITY results are rejected because the
              importer has already identified an existing source mapping.
            - EXACT_CANONICAL_MATCH may attach new provenance to the existing
              canonical institution.
            - NEW_INSTITUTION may create a Pending Verification institution.
        """

        errors = []

        if import_result.result not in self.PUBLISHABLE_IMPORT_RESULTS:
            return AcademicDirectoryPublicationResult(
                result="REJECTED_RESULT",
                reason=(
                    "Importer result is not eligible for controlled "
                    "publication."
                ),
                errors=[
                    (
                        "Unsupported importer result: "
                        f"{import_result.result}"
                    )
                ],
                dry_run=dry_run,
            )

        if not isinstance(data_source_id, int) or data_source_id <= 0:
            return AcademicDirectoryPublicationResult(
                result="DATA_SOURCE_NOT_FOUND",
                reason="A valid DataSource ID is required.",
                errors=["data_source_id must be a positive integer."],
                dry_run=dry_run,
            )

        data_source = self.session.get(DataSource, data_source_id)

        if data_source is None:
            return AcademicDirectoryPublicationResult(
                result="DATA_SOURCE_NOT_FOUND",
                reason="The supplied DataSource does not exist.",
                errors=[
                    f"No DataSource exists with id={data_source_id}."
                ],
                dry_run=dry_run,
            )

        if not data_source.is_active:
            return AcademicDirectoryPublicationResult(
                result="DATA_SOURCE_NOT_FOUND",
                reason="The supplied DataSource is inactive.",
                errors=[
                    f"DataSource id={data_source_id} is inactive."
                ],
                dry_run=dry_run,
            )

        source_name = (record.source_name or "").strip()
        external_name = (
            import_result.external_name
            or record.external_name
            or ""
        ).strip()

        normalized_external_name = (
            import_result.normalized_external_name or ""
        ).strip()

        external_identifier = (
            import_result.external_identifier
            if import_result.external_identifier is not None
            else None
        )

        reference_url = (
            record.reference_url.strip()
            if record.reference_url
            else None
        )

        if not source_name:
            errors.append("source_name is required.")

        if not external_name:
            errors.append("external_name is required.")

        if not normalized_external_name:
            errors.append("normalized_external_name is required.")

        if errors:
            return AcademicDirectoryPublicationResult(
                result="INVALID",
                reason="Publication input validation failed.",
                errors=errors,
                dry_run=dry_run,
            )

        # ------------------------------------------------------------------
        # Existing source-identity protection
        # ------------------------------------------------------------------

        identity_query = (
            self.session.query(AcademicDirectorySourceIdentity)
            .filter(
                AcademicDirectorySourceIdentity.data_source_id
                == data_source_id
            )
        )

        if external_identifier:
            existing_identity = (
                identity_query.filter(
                    AcademicDirectorySourceIdentity.external_identifier
                    == external_identifier
                )
                .first()
            )
        else:
            existing_identity = (
                identity_query.filter(
                    AcademicDirectorySourceIdentity.institution_id
                    == import_result.matched_institution_id
                    if import_result.matched_institution_id is not None
                    else AcademicDirectorySourceIdentity.id == -1,
                    AcademicDirectorySourceIdentity.normalized_external_name
                    == normalized_external_name,
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

            return AcademicDirectoryPublicationResult(
                result="EXISTING_SOURCE_IDENTITY",
                institution_id=(
                    institution.id if institution is not None else None
                ),
                institution_name=(
                    institution.name if institution is not None else None
                ),
                source_identity_id=existing_identity.id,
                reason=(
                    "The source identity already exists. Publication "
                    "would duplicate an existing source mapping."
                ),
                dry_run=dry_run,
            )

        # ------------------------------------------------------------------
        # Resolve canonical institution
        # ------------------------------------------------------------------

        institution = None
        created_institution = False

        if import_result.result == "EXACT_CANONICAL_MATCH":
            if import_result.matched_institution_id is None:
                return AcademicDirectoryPublicationResult(
                    result="INVALID",
                    reason=(
                        "EXACT_CANONICAL_MATCH is missing its "
                        "matched institution ID."
                    ),
                    errors=[
                        "matched_institution_id is required."
                    ],
                    dry_run=dry_run,
                )

            institution = self.session.get(
                Institution,
                import_result.matched_institution_id,
            )

            if institution is None:
                return AcademicDirectoryPublicationResult(
                    result="INVALID",
                    reason=(
                        "The importer referenced an institution that "
                        "does not exist."
                    ),
                    errors=[
                        (
                            "No Institution exists with id="
                            f"{import_result.matched_institution_id}."
                        )
                    ],
                    dry_run=dry_run,
                )

        elif import_result.result == "NEW_INSTITUTION":
            if dry_run:
                return AcademicDirectoryPublicationResult(
                    result="DRY_RUN_NEW_INSTITUTION",
                    institution_name=external_name,
                    reason=(
                        "The source record would create a new canonical "
                        "institution in Pending Verification status."
                    ),
                    dry_run=True,
                )

            institution = Institution(
                name=external_name,
                normalized_name=normalize_directory_identity(
                    external_name
                ),
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
                directory_status="Pending Verification",
                administration_status="Unclaimed",
                verification_source=(
                    "Imported from registered authoritative source: "
                    f"{source_name}."
                ),
                is_active=True,
            )

            self.session.add(institution)
            self.session.flush()

            created_institution = True

        # ------------------------------------------------------------------
        # Dry-run exact-match path
        # ------------------------------------------------------------------

        if dry_run:
            return AcademicDirectoryPublicationResult(
                result="DRY_RUN_EXACT_CANONICAL_MATCH",
                institution_id=institution.id,
                institution_name=institution.name,
                reason=(
                    "The source record would attach source identity and "
                    "provenance to the existing canonical institution."
                ),
                dry_run=True,
            )

        # ------------------------------------------------------------------
        # Source identity
        # ------------------------------------------------------------------

        source_identity = AcademicDirectorySourceIdentity(
            data_source_id=data_source_id,
            external_identifier=external_identifier,
            external_name=external_name,
            normalized_external_name=normalized_external_name,
            institution_id=institution.id,
            reference_url=reference_url,
        )

        self.session.add(source_identity)
        self.session.flush()

        # ------------------------------------------------------------------
        # Provenance evidence
        # ------------------------------------------------------------------

        evidence_note = (
            "Institution recognition evidence published from registered "
            f"source '{source_name}'."
        )

        if import_result.reason:
            evidence_note += f" Importer reason: {import_result.reason}"

        source_evidence = SourceEvidence(
            data_source_id=data_source_id,
            claim_type="Institution Recognition",
            institution_id=institution.id,
            reference_url=reference_url,
            reference_text=external_name,
            evidence_note=evidence_note,
        )

        self.session.add(source_evidence)
        self.session.flush()

        if created_institution:
            publication_result = "NEW_INSTITUTION_PUBLISHED"
        else:
            publication_result = "EXACT_CANONICAL_MATCH_PUBLISHED"

        return AcademicDirectoryPublicationResult(
            result=publication_result,
            institution_id=institution.id,
            institution_name=institution.name,
            source_identity_id=source_identity.id,
            evidence_id=source_evidence.id,
            reason=(
                "Institution publication completed with source identity "
                "and provenance evidence."
            ),
            created_institution=created_institution,
            created_source_identity=True,
            created_evidence=True,
            dry_run=False,
        )
