import unittest

from services.academic_hierarchy_source import (
    AcademicHierarchySourceRecord,
    NormalizedAcademicHierarchySourceRecord,
    normalize_hierarchy_source_record,
)


class AcademicHierarchySourceContractTests(unittest.TestCase):

    def test_full_hierarchy_record_normalizes_without_database_access(self):
        record = AcademicHierarchySourceRecord(
            source_name="NBTE",
            source_type="regulatory_directory",
            external_identifier="NBTE-123",
            institution_name="Example Polytechnic",
            academic_unit_name="School of Engineering",
            academic_unit_type="School",
            department_name="Computer Engineering",
            programme_name="Higher National Diploma Computer Engineering",
            programme_award="HND",
            programme_duration_years=2,
            reference_url="https://example.test/programmes/123",
            source_snapshot={"status": "Accredited"},
        )

        normalized = normalize_hierarchy_source_record(record)

        self.assertIsInstance(
            normalized,
            NormalizedAcademicHierarchySourceRecord,
        )

        self.assertEqual(
            normalized.institution_name,
            "Example Polytechnic",
        )

        self.assertEqual(
            normalized.normalized_institution_name,
            "example polytechnic",
        )

        self.assertEqual(
            normalized.academic_unit_name,
            "School of Engineering",
        )

        self.assertEqual(
            normalized.department_name,
            "Computer Engineering",
        )

        self.assertEqual(
            normalized.programme_name,
            "Higher National Diploma Computer Engineering",
        )

        self.assertEqual(normalized.programme_award, "HND")
        self.assertEqual(normalized.normalized_programme_award, "hnd")
        self.assertEqual(normalized.programme_duration_years, 2)

        self.assertEqual(
            normalized.source_snapshot,
            {"status": "Accredited"},
        )

    def test_partial_institution_record_is_allowed(self):
        record = AcademicHierarchySourceRecord(
            source_name="NUC",
            source_type="regulatory_directory",
            external_identifier="NUC-001",
            institution_name="Example University",
        )

        normalized = normalize_hierarchy_source_record(record)

        self.assertEqual(
            normalized.normalized_institution_name,
            "example university",
        )

        self.assertIsNone(normalized.normalized_academic_unit_name)
        self.assertIsNone(normalized.normalized_department_name)
        self.assertIsNone(normalized.normalized_programme_name)

    def test_department_requires_academic_unit(self):
        record = AcademicHierarchySourceRecord(
            source_name="NBTE",
            source_type="regulatory_directory",
            external_identifier="NBTE-002",
            institution_name="Example Polytechnic",
            department_name="Computer Engineering",
        )

        with self.assertRaises(ValueError) as context:
            normalize_hierarchy_source_record(record)

        self.assertIn(
            "academic_unit_name is required",
            str(context.exception),
        )

    def test_programme_requires_department(self):
        record = AcademicHierarchySourceRecord(
            source_name="NBTE",
            source_type="regulatory_directory",
            external_identifier="NBTE-003",
            institution_name="Example Polytechnic",
            academic_unit_name="School of Engineering",
            academic_unit_type="School",
            programme_name="Computer Engineering",
        )

        with self.assertRaises(ValueError) as context:
            normalize_hierarchy_source_record(record)

        self.assertIn(
            "department_name is required",
            str(context.exception),
        )

    def test_academic_unit_requires_unit_type(self):
        record = AcademicHierarchySourceRecord(
            source_name="NBTE",
            source_type="regulatory_directory",
            external_identifier="NBTE-004",
            institution_name="Example Polytechnic",
            academic_unit_name="School of Engineering",
        )

        with self.assertRaises(ValueError) as context:
            normalize_hierarchy_source_record(record)

        self.assertIn(
            "academic_unit_type is required",
            str(context.exception),
        )

    def test_invalid_duration_is_rejected(self):
        record = AcademicHierarchySourceRecord(
            source_name="NBTE",
            source_type="regulatory_directory",
            external_identifier="NBTE-005",
            institution_name="Example Polytechnic",
            programme_duration_years=0,
        )

        with self.assertRaises(ValueError) as context:
            normalize_hierarchy_source_record(record)

        self.assertIn(
            "programme_duration_years must be greater than zero",
            str(context.exception),
        )

    def test_normalization_does_not_modify_source_snapshot(self):
        snapshot = {
            "programme": "Computer Engineering",
            "award": "HND",
        }

        record = AcademicHierarchySourceRecord(
            source_name="NBTE",
            source_type="regulatory_directory",
            external_identifier="NBTE-006",
            institution_name="Example Polytechnic",
            source_snapshot=snapshot,
        )

        normalized = normalize_hierarchy_source_record(record)

        self.assertEqual(normalized.source_snapshot, snapshot)
        self.assertIsNot(normalized.source_snapshot, snapshot)


if __name__ == "__main__":
    unittest.main()
