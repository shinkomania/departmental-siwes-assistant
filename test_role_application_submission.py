import unittest

from app import create_app
from models import (
    db,
    User,
    Role,
    Institution,
    AcademicUnit,
    Department,
    Programme,
    RoleApplication,
)
from services.role_application import (
    RoleApplicationSubmissionError,
    submit_role_application,
)


class RoleApplicationSubmissionServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.applicant = User(
            full_name="Applicant User",
            email="applicant@example.com",
            account_status="Active",
        )
        self.applicant.set_password("password123")

        self.institution = Institution(
            name="Test University",
            institution_type="Federal University",
            state="Kaduna",
            is_active=True,
        )
        self.other_institution = Institution(
            name="Other University",
            institution_type="State University",
            state="Kano",
            is_active=True,
        )

        db.session.add_all(
            [self.applicant, self.institution, self.other_institution]
        )
        db.session.flush()

        self.faculty = AcademicUnit(
            institution_id=self.institution.id,
            name="Faculty of Engineering",
            unit_type="Faculty",
            is_active=True,
        )
        self.other_faculty = AcademicUnit(
            institution_id=self.other_institution.id,
            name="Faculty of Science",
            unit_type="Faculty",
            is_active=True,
        )
        db.session.add_all([self.faculty, self.other_faculty])
        db.session.flush()

        self.department = Department(
            academic_unit_id=self.faculty.id,
            name="Computer Engineering",
            is_active=True,
        )
        self.other_department = Department(
            academic_unit_id=self.other_faculty.id,
            name="Computer Science",
            is_active=True,
        )
        db.session.add_all([self.department, self.other_department])
        db.session.flush()

        self.programme = Programme(
            department_id=self.department.id,
            name="B.Eng. Computer Engineering",
            award="B.Eng.",
            is_active=True,
        )
        self.other_programme = Programme(
            department_id=self.other_department.id,
            name="B.Sc. Computer Science",
            award="B.Sc.",
            is_active=True,
        )

        self.coordinator_role = Role(
            name="Departmental SIWES Coordinator",
            slug="departmental_siwes_coordinator",
            is_active=True,
        )
        self.institution_admin_role = Role(
            name="Primary Institution Administrator",
            slug="primary_institution_administrator",
            is_active=True,
        )
        self.siwes_officer_role = Role(
            name="Institution SIWES Officer",
            slug="institution_siwes_officer",
            is_active=True,
        )
        self.platform_admin_role = Role(
            name="Platform Administrator",
            slug="platform_administrator",
            is_active=True,
        )
        self.student_role = Role(
            name="Student",
            slug="student",
            is_active=True,
        )

        db.session.add_all(
            [
                self.programme,
                self.other_programme,
                self.coordinator_role,
                self.institution_admin_role,
                self.siwes_officer_role,
                self.platform_admin_role,
                self.student_role,
            ]
        )
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _submit_coordinator(self, **overrides):
        data = {
            "applicant_user": self.applicant,
            "requested_role": self.coordinator_role,
            "institution_id": self.institution.id,
            "department_id": self.department.id,
            "official_position": "Departmental SIWES Coordinator",
            "academic_session": "2026/2027",
            "verification_method": "Appointment Letter",
        }
        data.update(overrides)
        return submit_role_application(**data)

    def test_department_coordinator_can_apply_for_whole_department(self):
        application = self._submit_coordinator()

        self.assertEqual(application.department_id, self.department.id)
        self.assertIsNone(application.programme_id)
        self.assertEqual(application.status, RoleApplication.STATUS_SUBMITTED)

    def test_department_coordinator_can_apply_for_specific_programme(self):
        application = self._submit_coordinator(
            programme_id=self.programme.id
        )

        self.assertEqual(application.department_id, self.department.id)
        self.assertEqual(application.programme_id, self.programme.id)

    def test_institution_admin_application_is_institution_only(self):
        application = submit_role_application(
            self.applicant,
            self.institution_admin_role,
            self.institution.id,
            "Registrar",
            academic_session="2026/2027",
        )

        self.assertEqual(application.institution_id, self.institution.id)
        self.assertIsNone(application.department_id)
        self.assertIsNone(application.programme_id)

    def test_siwes_officer_application_is_institution_only(self):
        application = submit_role_application(
            self.applicant,
            self.siwes_officer_role,
            self.institution.id,
            "SIWES Officer",
        )

        self.assertIsNone(application.department_id)
        self.assertIsNone(application.programme_id)

    def test_coordinator_requires_department(self):
        with self.assertRaises(RoleApplicationSubmissionError):
            self._submit_coordinator(department_id=None)

    def test_department_must_belong_to_selected_institution(self):
        with self.assertRaises(RoleApplicationSubmissionError):
            self._submit_coordinator(
                department_id=self.other_department.id
            )

    def test_programme_must_belong_to_selected_department(self):
        with self.assertRaises(RoleApplicationSubmissionError):
            self._submit_coordinator(
                programme_id=self.other_programme.id
            )

    def test_platform_admin_cannot_be_requested(self):
        with self.assertRaises(RoleApplicationSubmissionError):
            submit_role_application(
                self.applicant,
                self.platform_admin_role,
                self.institution.id,
                "Platform Administrator",
            )

    def test_student_role_cannot_be_requested(self):
        with self.assertRaises(RoleApplicationSubmissionError):
            submit_role_application(
                self.applicant,
                self.student_role,
                self.institution.id,
                "Student",
            )

    def test_inactive_applicant_cannot_submit(self):
        self.applicant.account_status = "Suspended"
        db.session.commit()

        with self.assertRaises(RoleApplicationSubmissionError):
            self._submit_coordinator()

    def test_inactive_role_cannot_be_requested(self):
        self.coordinator_role.is_active = False
        db.session.commit()

        with self.assertRaises(RoleApplicationSubmissionError):
            self._submit_coordinator()

    def test_official_position_is_required(self):
        with self.assertRaises(RoleApplicationSubmissionError):
            self._submit_coordinator(official_position="   ")

    def test_invalid_verification_method_is_rejected(self):
        with self.assertRaises(RoleApplicationSubmissionError):
            self._submit_coordinator(
                verification_method="Social Media Message"
            )

    def test_duplicate_open_application_is_rejected(self):
        self._submit_coordinator()

        with self.assertRaises(RoleApplicationSubmissionError):
            self._submit_coordinator()

        self.assertEqual(RoleApplication.query.count(), 1)

    def test_final_application_does_not_block_new_application(self):
        first = self._submit_coordinator()
        first.status = RoleApplication.STATUS_REJECTED
        db.session.commit()

        second = self._submit_coordinator()

        self.assertNotEqual(first.id, second.id)
        self.assertEqual(RoleApplication.query.count(), 2)

    def test_different_programme_scope_is_not_exact_duplicate(self):
        self._submit_coordinator()

        second = self._submit_coordinator(
            programme_id=self.programme.id
        )

        self.assertEqual(RoleApplication.query.count(), 2)
        self.assertEqual(second.programme_id, self.programme.id)

    def test_different_academic_session_is_not_duplicate(self):
        self._submit_coordinator()

        second = self._submit_coordinator(
            academic_session="2027/2028"
        )

        self.assertEqual(RoleApplication.query.count(), 2)
        self.assertEqual(second.academic_session, "2027/2028")


if __name__ == "__main__":
    unittest.main()
