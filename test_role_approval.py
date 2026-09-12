import unittest
from datetime import datetime, timedelta

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
    UserRoleAssignment,
)
from services.role_approval import (
    RoleApprovalError,
    approve_role_application,
)


class RoleApprovalServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

        db.create_all()

        self.applicant = User(
            full_name="Applicant User",
            email="applicant@example.com",
            account_status="Active",
        )
        self.applicant.set_password("password123")

        self.reviewer = User(
            full_name="Reviewer User",
            email="reviewer@example.com",
            account_status="Active",
        )
        self.reviewer.set_password("password123")

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

        db.session.add_all([
            self.applicant,
            self.reviewer,
            self.institution,
            self.other_institution,
        ])
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

        db.session.add_all([
            self.programme,
            self.other_programme,
            self.coordinator_role,
            self.institution_admin_role,
            self.siwes_officer_role,
            self.platform_admin_role,
        ])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _application(
        self,
        role,
        *,
        institution_id=None,
        department_id=None,
        programme_id=None,
        status=None,
        academic_session="2026/2027",
    ):
        application = RoleApplication(
            user_id=self.applicant.id,
            requested_role_id=role.id,
            institution_id=(
                self.institution.id
                if institution_id is None
                else institution_id
            ),
            department_id=department_id,
            programme_id=programme_id,
            academic_session=academic_session,
            official_position="SIWES Coordinator",
            institutional_email="staff@test.edu.ng",
            phone="08000000000",
            status=status or RoleApplication.STATUS_SUBMITTED,
        )
        db.session.add(application)
        db.session.commit()
        return application

    def test_approve_department_coordinator_creates_scoped_assignment(self):
        application = self._application(
            self.coordinator_role,
            department_id=self.department.id,
            programme_id=self.programme.id,
        )

        assignment = approve_role_application(
            application,
            self.reviewer,
            reviewer_notes="Verified appointment evidence.",
        )

        self.assertEqual(application.status, RoleApplication.STATUS_APPROVED)
        self.assertEqual(application.reviewed_by_user_id, self.reviewer.id)
        self.assertIsNotNone(application.decided_at)

        self.assertEqual(assignment.user_id, self.applicant.id)
        self.assertEqual(assignment.role_id, self.coordinator_role.id)
        self.assertEqual(assignment.institution_id, self.institution.id)
        self.assertEqual(assignment.department_id, self.department.id)
        self.assertEqual(assignment.programme_id, self.programme.id)
        self.assertEqual(assignment.status, "Approved")
        self.assertEqual(assignment.academic_session, "2026/2027")
        self.assertEqual(assignment.approved_by_user_id, self.reviewer.id)
        self.assertIsNotNone(assignment.approved_at)

    def test_institution_admin_is_institution_scoped_only(self):
        application = self._application(self.institution_admin_role)

        assignment = approve_role_application(application, self.reviewer)

        self.assertEqual(assignment.institution_id, self.institution.id)
        self.assertIsNone(assignment.department_id)
        self.assertIsNone(assignment.programme_id)

    def test_institution_role_rejects_department_scope(self):
        application = self._application(
            self.siwes_officer_role,
            department_id=self.department.id,
        )

        with self.assertRaises(RoleApprovalError):
            approve_role_application(application, self.reviewer)

        db.session.refresh(application)
        self.assertNotEqual(application.status, RoleApplication.STATUS_APPROVED)
        self.assertEqual(UserRoleAssignment.query.count(), 0)

    def test_department_coordinator_requires_department(self):
        application = self._application(self.coordinator_role)

        with self.assertRaises(RoleApprovalError):
            approve_role_application(application, self.reviewer)

        self.assertEqual(UserRoleAssignment.query.count(), 0)

    def test_mismatched_department_and_institution_is_rejected(self):
        application = self._application(
            self.coordinator_role,
            department_id=self.other_department.id,
        )

        with self.assertRaises(RoleApprovalError):
            approve_role_application(application, self.reviewer)

        self.assertEqual(UserRoleAssignment.query.count(), 0)

    def test_programme_must_belong_to_selected_department(self):
        application = self._application(
            self.coordinator_role,
            department_id=self.department.id,
            programme_id=self.other_programme.id,
        )

        with self.assertRaises(RoleApprovalError):
            approve_role_application(application, self.reviewer)

        self.assertEqual(UserRoleAssignment.query.count(), 0)

    def test_platform_admin_cannot_be_approved_through_this_workflow(self):
        application = self._application(self.platform_admin_role)

        with self.assertRaises(RoleApprovalError):
            approve_role_application(application, self.reviewer)

        self.assertEqual(UserRoleAssignment.query.count(), 0)

    def test_duplicate_approved_assignment_is_rejected(self):
        first = self._application(
            self.coordinator_role,
            department_id=self.department.id,
        )
        approve_role_application(first, self.reviewer)

        second = self._application(
            self.coordinator_role,
            department_id=self.department.id,
        )

        with self.assertRaises(RoleApprovalError):
            approve_role_application(second, self.reviewer)

        self.assertEqual(UserRoleAssignment.query.count(), 1)

    def test_final_application_status_cannot_be_approved_again(self):
        application = self._application(
            self.coordinator_role,
            department_id=self.department.id,
            status=RoleApplication.STATUS_REJECTED,
        )

        with self.assertRaises(RoleApprovalError):
            approve_role_application(application, self.reviewer)

        self.assertEqual(UserRoleAssignment.query.count(), 0)

    def test_inactive_applicant_is_rejected(self):
        self.applicant.account_status = "Suspended"
        db.session.commit()

        application = self._application(
            self.coordinator_role,
            department_id=self.department.id,
        )

        with self.assertRaises(RoleApprovalError):
            approve_role_application(application, self.reviewer)

        self.assertEqual(UserRoleAssignment.query.count(), 0)

    def test_inactive_reviewer_is_rejected(self):
        self.reviewer.account_status = "Suspended"
        db.session.commit()

        application = self._application(
            self.coordinator_role,
            department_id=self.department.id,
        )

        with self.assertRaises(RoleApprovalError):
            approve_role_application(application, self.reviewer)

        self.assertEqual(UserRoleAssignment.query.count(), 0)

    def test_expiry_is_copied_to_assignment(self):
        application = self._application(
            self.coordinator_role,
            department_id=self.department.id,
        )
        expiry = datetime.utcnow() + timedelta(days=365)

        assignment = approve_role_application(
            application,
            self.reviewer,
            expires_at=expiry,
        )

        self.assertEqual(assignment.expires_at, expiry)


if __name__ == "__main__":
    unittest.main()
