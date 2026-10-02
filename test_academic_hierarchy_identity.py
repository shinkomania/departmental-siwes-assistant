import unittest

from app import create_app
from models import db, AcademicUnit, Department, Institution, Programme

from services.academic_hierarchy_identity import (
    AcademicHierarchyIdentityResolver,
)
from services.academic_hierarchy_source import (
    AcademicHierarchySourceRecord,
)


class AcademicHierarchyIdentityResolverTests(unittest.TestCase):

    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _institution(self, name="Example University"):
        institution = Institution(
            name=name,
        )

        db.session.add(institution)
        db.session.commit()

        return institution

    def test_unmatched_institution_is_new_hierarchy(self):
        record = AcademicHierarchySourceRecord(
            source_name="NUC",
            source_type="regulatory_directory",
            external_identifier="NUC-001",
            institution_name="Unknown University",
        )

        resolver = AcademicHierarchyIdentityResolver(db.session)

        result = resolver.resolve(record)

        self.assertEqual(result.result, "NEW_ACADEMIC_HIERARCHY")
        self.assertIsNone(result.matched_institution_id)

    def test_existing_institution_without_unit_is_classified(self):
        institution = self._institution()

        record = AcademicHierarchySourceRecord(
            source_name="NUC",
            source_type="regulatory_directory",
            external_identifier="NUC-002",
            institution_name=institution.name,
        )

        resolver = AcademicHierarchyIdentityResolver(db.session)

        result = resolver.resolve(record)

        self.assertEqual(result.result, "EXISTING_INSTITUTION")
        self.assertEqual(result.matched_institution_id, institution.id)

    def test_full_existing_hierarchy_matches_exactly(self):
        institution = self._institution()

        unit = AcademicUnit(
            institution_id=institution.id,
            name="School of Engineering",
            unit_type="School",
        )

        db.session.add(unit)
        db.session.commit()

        department = Department(
            academic_unit_id=unit.id,
            name="Computer Engineering",
        )

        db.session.add(department)
        db.session.commit()

        programme = Programme(
            department_id=department.id,
            name="Computer Engineering",
            award="B.Eng.",
            duration_years=5,
        )

        db.session.add(programme)
        db.session.commit()

        record = AcademicHierarchySourceRecord(
            source_name="NUC",
            source_type="regulatory_directory",
            external_identifier="NUC-003",
            institution_name=institution.name,
            academic_unit_name=unit.name,
            academic_unit_type=unit.unit_type,
            department_name=department.name,
            programme_name=programme.name,
            programme_award=programme.award,
            programme_duration_years=programme.duration_years,
        )

        resolver = AcademicHierarchyIdentityResolver(db.session)

        result = resolver.resolve(record)

        self.assertEqual(result.result, "EXACT_HIERARCHY_MATCH")
        self.assertEqual(result.matched_institution_id, institution.id)
        self.assertEqual(result.matched_academic_unit_id, unit.id)
        self.assertEqual(result.matched_department_id, department.id)
        self.assertEqual(result.matched_programme_id, programme.id)

    def test_existing_unit_but_missing_department_is_not_exact(self):
        institution = self._institution()

        unit = AcademicUnit(
            institution_id=institution.id,
            name="School of Engineering",
            unit_type="School",
        )

        db.session.add(unit)
        db.session.commit()

        record = AcademicHierarchySourceRecord(
            source_name="NUC",
            source_type="regulatory_directory",
            external_identifier="NUC-004",
            institution_name=institution.name,
            academic_unit_name=unit.name,
            academic_unit_type=unit.unit_type,
            department_name="Computer Engineering",
        )

        resolver = AcademicHierarchyIdentityResolver(db.session)

        result = resolver.resolve(record)

        self.assertEqual(result.result, "EXISTING_ACADEMIC_UNIT")
        self.assertEqual(result.matched_academic_unit_id, unit.id)
        self.assertIsNone(result.matched_department_id)

    def test_existing_department_but_missing_programme_is_not_exact(self):
        institution = self._institution()

        unit = AcademicUnit(
            institution_id=institution.id,
            name="School of Engineering",
            unit_type="School",
        )

        db.session.add(unit)
        db.session.commit()

        department = Department(
            academic_unit_id=unit.id,
            name="Computer Engineering",
        )

        db.session.add(department)
        db.session.commit()

        record = AcademicHierarchySourceRecord(
            source_name="NUC",
            source_type="regulatory_directory",
            external_identifier="NUC-005",
            institution_name=institution.name,
            academic_unit_name=unit.name,
            academic_unit_type=unit.unit_type,
            department_name=department.name,
            programme_name="Computer Engineering",
            programme_award="B.Eng.",
        )

        resolver = AcademicHierarchyIdentityResolver(db.session)

        result = resolver.resolve(record)

        self.assertEqual(result.result, "EXISTING_DEPARTMENT")
        self.assertEqual(result.matched_department_id, department.id)
        self.assertIsNone(result.matched_programme_id)

    def test_invalid_source_is_non_mutating(self):
        before = db.session.query(Institution).count()

        record = AcademicHierarchySourceRecord(
            source_name="",
            source_type="",
            external_identifier=None,
            institution_name="",
        )

        resolver = AcademicHierarchyIdentityResolver(db.session)

        result = resolver.resolve(record)

        after = db.session.query(Institution).count()

        self.assertEqual(result.result, "INVALID")
        self.assertEqual(before, after)

    def test_dry_run_resolves_collection_without_writes(self):
        institution = self._institution()

        records = [
            AcademicHierarchySourceRecord(
                source_name="NUC",
                source_type="regulatory_directory",
                external_identifier="NUC-006",
                institution_name=institution.name,
            ),
            AcademicHierarchySourceRecord(
                source_name="NUC",
                source_type="regulatory_directory",
                external_identifier="NUC-007",
                institution_name="Another University",
            ),
        ]

        before = db.session.query(Institution).count()

        resolver = AcademicHierarchyIdentityResolver(db.session)

        results = resolver.dry_run(records)

        after = db.session.query(Institution).count()

        self.assertEqual(len(results), 2)
        self.assertEqual(before, after)
        self.assertEqual(results[0].result, "EXISTING_INSTITUTION")
        self.assertEqual(results[1].result, "NEW_ACADEMIC_HIERARCHY")


if __name__ == "__main__":
    unittest.main()
