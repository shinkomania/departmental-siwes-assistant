import unittest
from datetime import datetime, timedelta

from app import create_app
from models import (
    db,
    User,
    Role,
    Permission,
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
            full_name="Platform Reviewer",
            email="reviewer@example.com",
            account_status="Active",
        )
        self.reviewer.set_password("password123")

        self.institution_admin_reviewer = User(
            full_name="Institution Reviewer",
            email="institution-reviewer@example.com",
            account_status="Active",
        )
        self.institution_admin_reviewer.set_password("password123")

        self.unauthorized_reviewer = User(
            full_name="Unauthorized Reviewer",
            email="unauthorized@example.com",
            account_status="Active",
        )
        self.unauthorized_reviewer.set_password("password123")

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
            self.institution_admin_reviewer,
            self.unauthorized_reviewer,
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

        self.review_coordinator = Permission(
            name="Review Coordinator Applications",
            slug="review_coordinator_applications",
        )
        self.review_institution_admin = Permission(
            name="Review Institution Administrator Applications",
            slug="review_institution_admin_applications",
        )
        self.review_siwes_officer = Permission(
            name="Review Institution SIWES Officer Applications",
            slug="review_institution_siwes_officer_applications",
        )

        db.session.add_all([
            self.programme,
            self.other_programme,
            self.coordinator_role,
            self.institution_admin_role,
            self.siwes_officer_role,
            self.platform_admin_role,
            self.review_coordinator,
            self.review_institution_admin,
            self.review_siwes_officer,
        ])
        db.session.flush()

        self.platform_admin_role.permissions = [
            self.review_coordinator,
            self.review_institution_admin,
            self.review_siwes_officer,
        ]
        self.institution_admin_role.permissions = [
            self.review_coordinator,
        ]

        # Global Platform Administrator reviewer assignment.
        db.session.add(
            UserRoleAssignment(
                user_id=self.reviewer.id,
                role_id=self.platform_admin_role.id,
                status="Approved",
                approved_at=datetime.utcnow(),
            )
        )

        # Institution-scoped Primary Institution Administrator reviewer assignment.
        db.session.add(
            UserRoleAssignment(
                user_id=self.institution_admin_reviewer.id,
                role_id=self.institution_admin_role.id,
                institution_id=self.institution.id,
                status="Approved",
                approved_at=datetime.utcnow(),
            )
        )

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

    def test_platform_admin_can_approve_department_coordinator(self):
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
        self.assertEqual(assignment.department_id, self.department.id)
        self.assertEqual(assignment.programme_id, self.programme.id)
        self.assertEqual(assignment.status, "Approved")

    def test_platform_admin_can_approve_institution_admin(self):
        application = self._application(self.institution_admin_role)

        assignment = approve_role_application(application, self.reviewer)

        self.assertEqual(assignment.institution_id, self.institution.id)
        self.assertIsNone(assignment.department_id)
        self.assertIsNone(assignment.programme_id)

    def test_platform_admin_can_approve_institution_siwes_officer(self):
        application = self._application(self.siwes_officer_role)

        assignment = approve_role_application(application, self.reviewer)

        self.assertEqual(assignment.institution_id, self.institution.id)
        self.assertIsNone(assignment.department_id)

    def test_unauthorized_active_user_cannot_approve(self):
        application = self._application(
            self.coordinator_role,
            department_id=self.department.id,
        )

        with self.assertRaises(RoleApprovalError):
            approve_role_application(application, self.unauthorized_reviewer)

        self.assertEqual(
            UserRoleAssignment.query.filter_by(
                user_id=self.applicant.id
            ).count(),
            0,
        )
    
    def test_user_cannot_approve_own_role_application(self):
        # Give the applicant global Platform Administrator authority so
        # they would otherwise have permission to approve this request.
        db.session.add(
            UserRoleAssignment(
                user_id=self.applicant.id,
                role_id=self.platform_admin_role.id,
                status="Approved",
                approved_at=datetime.utcnow(),
            )
        )
        db.session.commit()

        application = self._application(
            self.coordinator_role,
            department_id=self.department.id,
        )

        with self.assertRaisesRegex(
            RoleApprovalError,
            "A user cannot approve their own role application.",
        ):
            approve_role_application(
                application,
                self.applicant,
            )

        # The privileged coordinator role must not have been granted.
        coordinator_assignments = UserRoleAssignment.query.filter_by(
            user_id=self.applicant.id,
            role_id=self.coordinator_role.id,
        ).count()

        self.assertEqual(coordinator_assignments, 0)

        # The application must remain untouched.
        self.assertEqual(
            application.status,
            RoleApplication.STATUS_SUBMITTED,
        )
        self.assertIsNone(application.reviewed_by_user_id)
        self.assertIsNone(application.decided_at)

    def test_institution_admin_can_approve_coordinator_in_own_institution(self):
        application = self._application(
            self.coordinator_role,
            department_id=self.department.id,
        )

        assignment = approve_role_application(
            application,
            self.institution_admin_reviewer,
        )

        self.assertEqual(assignment.institution_id, self.institution.id)
        self.assertEqual(assignment.department_id, self.department.id)

    def test_institution_admin_cannot_approve_coordinator_in_other_institution(self):
        application = self._application(
            self.coordinator_role,
            institution_id=self.other_institution.id,
            department_id=self.other_department.id,
        )

        with self.assertRaises(RoleApprovalError):
            approve_role_application(
                application,
                self.institution_admin_reviewer,
            )

        self.assertEqual(
            UserRoleAssignment.query.filter_by(
                user_id=self.applicant.id
            ).count(),
            0,
        )

    def test_institution_admin_cannot_approve_institution_admin_application(self):
        application = self._application(self.institution_admin_role)

        with self.assertRaises(RoleApprovalError):
            approve_role_application(
                application,
                self.institution_admin_reviewer,
            )

    def test_institution_admin_cannot_approve_siwes_officer_application(self):
        application = self._application(self.siwes_officer_role)

        with self.assertRaises(RoleApprovalError):
            approve_role_application(
                application,
                self.institution_admin_reviewer,
            )

    def test_institution_role_rejects_department_scope(self):
        application = self._application(
            self.siwes_officer_role,
            department_id=self.department.id,
        )

        with self.assertRaises(RoleApprovalError):
            approve_role_application(application, self.reviewer)

    def test_department_coordinator_requires_department(self):
        application = self._application(self.coordinator_role)

        with self.assertRaises(RoleApprovalError):
            approve_role_application(application, self.reviewer)

    def test_mismatched_department_and_institution_is_rejected(self):
        application = self._application(
            self.coordinator_role,
            department_id=self.other_department.id,
        )

        with self.assertRaises(RoleApprovalError):
            approve_role_application(application, self.reviewer)

    def test_programme_must_belong_to_selected_department(self):
        application = self._application(
            self.coordinator_role,
            department_id=self.department.id,
            programme_id=self.other_programme.id,
        )

        with self.assertRaises(RoleApprovalError):
            approve_role_application(application, self.reviewer)

    def test_platform_admin_role_cannot_be_requested_through_workflow(self):
        application = self._application(self.platform_admin_role)

        with self.assertRaises(RoleApprovalError):
            approve_role_application(application, self.reviewer)

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

        applicant_assignments = UserRoleAssignment.query.filter_by(
            user_id=self.applicant.id
        ).count()
        self.assertEqual(applicant_assignments, 1)

    def test_final_application_status_cannot_be_approved_again(self):
        application = self._application(
            self.coordinator_role,
            department_id=self.department.id,
            status=RoleApplication.STATUS_REJECTED,
        )

        with self.assertRaises(RoleApprovalError):
            approve_role_application(application, self.reviewer)

    def test_inactive_applicant_is_rejected(self):
        self.applicant.account_status = "Suspended"
        db.session.commit()

        application = self._application(
            self.coordinator_role,
            department_id=self.department.id,
        )

        with self.assertRaises(RoleApprovalError):
            approve_role_application(application, self.reviewer)

    def test_inactive_reviewer_is_rejected(self):
        self.reviewer.account_status = "Suspended"
        db.session.commit()

        application = self._application(
            self.coordinator_role,
            department_id=self.department.id,
        )

        with self.assertRaises(RoleApprovalError):
            approve_role_application(application, self.reviewer)

    def test_expired_reviewer_assignment_cannot_approve(self):
        reviewer_assignment = UserRoleAssignment.query.filter_by(
            user_id=self.reviewer.id,
            role_id=self.platform_admin_role.id,
        ).first()
        reviewer_assignment.expires_at = datetime.utcnow() - timedelta(days=1)
        db.session.commit()

        application = self._application(
            self.coordinator_role,
            department_id=self.department.id,
        )

        with self.assertRaises(RoleApprovalError):
            approve_role_application(application, self.reviewer)

    def test_expiry_is_copied_to_new_assignment(self):
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
