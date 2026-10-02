import unittest

from app import create_app
from models import (
    db,
    AcademicDirectorySourceIdentity,
    AcademicUnit,
    DataSource,
    Department,
    Institution,
    Programme,
    SIWESConfiguration,
    SourceEvidence,
)

from services.academic_hierarchy_publication import (
    AcademicHierarchyPublicationService,
)
from services.academic_hierarchy_source import (
    AcademicHierarchySourceRecord,
)


class AcademicHierarchyPublicationTests(unittest.TestCase):

    def setUp(self):
        self.app = create_app("testing")
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

        self.source = DataSource(
            name="E4 Test Authority",
            source_type="Regulator",
            authority_name="E4 Test Authority",
            base_url="https://example.test/",
            is_active=True,
        )

        db.session.add(self.source)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def _record(
        self,
        *,
        institution="Example University",
        unit="Faculty of Engineering",
        unit_type="Faculty",
        department="Computer Engineering",
        programme="Computer Engineering",
        award="B.Eng.",
        duration=5,
        identifier="E4-001",
    ):
        return AcademicHierarchySourceRecord(
            source_name="E4 Test Authority",
            source_type="Regulator",
            external_identifier=identifier,
            institution_name=institution,
            academic_unit_name=unit,
            academic_unit_type=unit_type,
            department_name=department,
            programme_name=programme,
            programme_award=award,
            programme_duration_years=duration,
            reference_url="https://example.test/programmes",
            source_snapshot={"test": True},
        )

    def test_full_hierarchy_is_published(self):
        service = AcademicHierarchyPublicationService(db.session)

        result = service.publish(
            self._record(),
            data_source_id=self.source.id,
        )

        self.assertEqual(result.result, "PUBLISHED")
        self.assertTrue(result.created_institution)
        self.assertTrue(result.created_academic_unit)
        self.assertTrue(result.created_department)
        self.assertTrue(result.created_programme)

        self.assertEqual(Institution.query.count(), 1)
        self.assertEqual(AcademicUnit.query.count(), 1)
        self.assertEqual(Department.query.count(), 1)
        self.assertEqual(Programme.query.count(), 1)

        self.assertEqual(
            AcademicDirectorySourceIdentity.query.count(),
            4,
        )

        self.assertEqual(
            SourceEvidence.query.count(),
            4,
        )

        self.assertEqual(
            result.created_source_identities,
            4,
        )

        self.assertEqual(
            result.created_evidence,
            4,
        )

    def test_new_institution_is_pending_verification(self):
        service = AcademicHierarchyPublicationService(db.session)

        result = service.publish(
            self._record(),
            data_source_id=self.source.id,
        )

        institution = db.session.get(
            Institution,
            result.institution_id,
        )

        self.assertEqual(
            institution.directory_status,
            "Pending Verification",
        )

    def test_publication_does_not_create_siwes_configuration(self):
        service = AcademicHierarchyPublicationService(db.session)

        result = service.publish(
            self._record(),
            data_source_id=self.source.id,
        )

        self.assertEqual(result.result, "PUBLISHED")
        self.assertEqual(
            SIWESConfiguration.query.count(),
            0,
        )

    def test_each_source_identity_has_exactly_one_target(self):
        service = AcademicHierarchyPublicationService(db.session)

        service.publish(
            self._record(),
            data_source_id=self.source.id,
        )

        identities = AcademicDirectorySourceIdentity.query.all()

        self.assertEqual(len(identities), 4)

        self.assertEqual(
            sorted(identity.target_type for identity in identities),
            [
                "AcademicUnit",
                "Department",
                "Institution",
                "Programme",
            ],
        )

        for identity in identities:
            target_ids = [
                identity.institution_id,
                identity.academic_unit_id,
                identity.department_id,
                identity.programme_id,
            ]

            self.assertEqual(
                sum(value is not None for value in target_ids),
                1,
            )

    def test_only_institution_identity_receives_source_identifier(self):
        service = AcademicHierarchyPublicationService(db.session)

        service.publish(
            self._record(),
            data_source_id=self.source.id,
        )

        identities = AcademicDirectorySourceIdentity.query.all()

        institution_identity = next(
            item
            for item in identities
            if item.institution_id is not None
        )

        lower_identities = [
            item
            for item in identities
            if item.institution_id is None
        ]

        self.assertEqual(
            institution_identity.external_identifier,
            "E4-001",
        )

        self.assertTrue(
            all(
                item.external_identifier is None
                for item in lower_identities
            )
        )

    def test_each_evidence_record_is_academic_structure(self):
        service = AcademicHierarchyPublicationService(db.session)

        service.publish(
            self._record(),
            data_source_id=self.source.id,
        )

        evidence = SourceEvidence.query.all()

        self.assertEqual(len(evidence), 4)

        self.assertTrue(
            all(
                item.claim_type == "Academic Structure"
                for item in evidence
            )
        )

    def test_dry_run_creates_nothing(self):
        service = AcademicHierarchyPublicationService(db.session)

        result = service.publish(
            self._record(),
            data_source_id=self.source.id,
            dry_run=True,
        )

        self.assertEqual(
            result.result,
            "DRY_RUN_NEW_HIERARCHY",
        )

        self.assertTrue(result.dry_run)

        self.assertEqual(Institution.query.count(), 0)
        self.assertEqual(AcademicUnit.query.count(), 0)
        self.assertEqual(Department.query.count(), 0)
        self.assertEqual(Programme.query.count(), 0)
        self.assertEqual(
            AcademicDirectorySourceIdentity.query.count(),
            0,
        )
        self.assertEqual(SourceEvidence.query.count(), 0)

    def test_existing_source_identity_is_not_duplicated(self):
        service = AcademicHierarchyPublicationService(db.session)

        first = service.publish(
            self._record(),
            data_source_id=self.source.id,
        )

        self.assertEqual(first.result, "PUBLISHED")

        before = (
            Institution.query.count(),
            AcademicUnit.query.count(),
            Department.query.count(),
            Programme.query.count(),
            AcademicDirectorySourceIdentity.query.count(),
            SourceEvidence.query.count(),
        )

        second = service.publish(
            self._record(),
            data_source_id=self.source.id,
        )

        self.assertEqual(
            second.result,
            "PUBLISHED",
        )

        after = (
            Institution.query.count(),
            AcademicUnit.query.count(),
            Department.query.count(),
            Programme.query.count(),
            AcademicDirectorySourceIdentity.query.count(),
            SourceEvidence.query.count(),
        )

        self.assertEqual(before, after)

        self.assertFalse(second.created_institution)
        self.assertFalse(second.created_academic_unit)
        self.assertFalse(second.created_department)
        self.assertFalse(second.created_programme)
        self.assertEqual(second.created_source_identities, 0)
        self.assertEqual(second.created_evidence, 0)

    def test_external_identifier_conflict_requires_review(self):
        service = AcademicHierarchyPublicationService(db.session)

        first = service.publish(
            self._record(
                institution="First University",
                identifier="SHARED-001",
            ),
            data_source_id=self.source.id,
        )

        self.assertEqual(first.result, "PUBLISHED")

        second = service.publish(
            self._record(
                institution="Second University",
                identifier="SHARED-001",
            ),
            data_source_id=self.source.id,
        )

        self.assertEqual(
            second.result,
            "REVIEW_REQUIRED",
        )

        self.assertEqual(
            Institution.query.count(),
            1,
        )

    def test_partial_unit_can_be_published(self):
        institution = Institution(
            name="Example University",
            institution_type="University",
            directory_status="Pending Verification",
        )

        db.session.add(institution)
        db.session.flush()

        record = self._record(
            department=None,
            programme=None,
        )

        service = AcademicHierarchyPublicationService(db.session)

        result = service.publish(
            record,
            data_source_id=self.source.id,
        )

        self.assertEqual(result.result, "PUBLISHED")
        self.assertIsNotNone(result.academic_unit_id)
        self.assertIsNone(result.department_id)

        self.assertEqual(
            AcademicDirectorySourceIdentity.query.count(),
            2,
        )

        self.assertEqual(
            SourceEvidence.query.count(),
            2,
        )

    def test_partial_department_can_be_published(self):
        institution = Institution(
            name="Example University",
            institution_type="University",
            directory_status="Pending Verification",
        )

        db.session.add(institution)
        db.session.flush()

        unit = AcademicUnit(
            institution_id=institution.id,
            name="Faculty of Engineering",
            unit_type="Faculty",
        )

        db.session.add(unit)
        db.session.flush()

        record = self._record(
            department="Computer Engineering",
            programme=None,
        )

        service = AcademicHierarchyPublicationService(db.session)

        result = service.publish(
            record,
            data_source_id=self.source.id,
        )

        self.assertEqual(result.result, "PUBLISHED")
        self.assertIsNotNone(result.department_id)
        self.assertIsNone(result.programme_id)

        self.assertEqual(
            AcademicDirectorySourceIdentity.query.count(),
            3,
        )

        self.assertEqual(
            SourceEvidence.query.count(),
            3,
        )

    def test_programme_duration_does_not_create_siwes_configuration(self):
        service = AcademicHierarchyPublicationService(db.session)

        result = service.publish(
            self._record(duration=4),
            data_source_id=self.source.id,
        )

        programme = db.session.get(
            Programme,
            result.programme_id,
        )

        self.assertEqual(programme.duration_years, 4)
        self.assertEqual(
            SIWESConfiguration.query.count(),
            0,
        )

    def test_invalid_record_is_non_mutating(self):
        service = AcademicHierarchyPublicationService(db.session)

        record = AcademicHierarchySourceRecord(
            source_name="",
            source_type="",
            external_identifier=None,
            institution_name="",
        )

        result = service.publish(
            record,
            data_source_id=self.source.id,
        )

        self.assertEqual(result.result, "INVALID")
        self.assertEqual(Institution.query.count(), 0)
        self.assertEqual(AcademicUnit.query.count(), 0)
        self.assertEqual(Department.query.count(), 0)
        self.assertEqual(Programme.query.count(), 0)

    def test_inactive_data_source_is_rejected(self):
        self.source.is_active = False
        db.session.commit()

        service = AcademicHierarchyPublicationService(db.session)

        result = service.publish(
            self._record(),
            data_source_id=self.source.id,
        )

        self.assertEqual(
            result.result,
            "DATA_SOURCE_NOT_FOUND",
        )

        self.assertEqual(Institution.query.count(), 0)


if __name__ == "__main__":
    unittest.main()
