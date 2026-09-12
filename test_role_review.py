import unittest
from datetime import datetime

from app import create_app
from models import (
    db,
    User,
    Role,
    Permission,
    Institution,
    AcademicUnit,
    Department,
    RoleApplication,
    UserRoleAssignment,
)
from services.role_review import (
    RoleReviewError,
    mark_role_application_under_review,
    request_role_application_more_information,
    reject_role_application,
    withdraw_role_application,
)


class RoleReviewServiceTestCase(unittest.TestCase):
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

        self.platform_reviewer = User(
            full_name="Platform Reviewer",
            email="platform@example.com",
            account_status="Active",
        )
        self.platform_reviewer.set_password("password123")

        self.institution_reviewer = User(
            full_name="Institution Reviewer",
            email="institution@example.com",
            account_status="Active",
        )
        self.institution_reviewer.set_password("password123")

        self.unauthorized_user = User(
            full_name="Unauthorized User",
            email="unauthorized@example.com",
            account_status="Active",
        )
        self.unauthorized_user.set_password("password123")

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
            [
                self.applicant,
                self.platform_reviewer,
                self.institution_reviewer,
                self.unauthorized_user,
                self.institution,
                self.other_institution,
            ]
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

        db.session.add_all(
            [
                self.coordinator_role,
                self.institution_admin_role,
                self.siwes_officer_role,
                self.platform_admin_role,
                self.review_coordinator,
                self.review_institution_admin,
                self.review_siwes_officer,
            ]
        )
        db.session.flush()

        self.platform_admin_role.permissions = [
            self.review_coordinator,
            self.review_institution_admin,
            self.review_siwes_officer,
        ]
        self.institution_admin_role.permissions = [
            self.review_coordinator,
        ]

        db.session.add(
            UserRoleAssignment(
                user_id=self.platform_reviewer.id,
                role_id=self.platform_admin_role.id,
                status="Approved",
                approved_at=datetime.utcnow(),
            )
        )

        db.session.add(
            UserRoleAssignment(
                user_id=self.institution_reviewer.id,
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
        *,
        role=None,
        institution_id=None,
        department_id=None,
        status=None,
    ):
        role = role or self.coordinator_role
        institution_id = (
            self.institution.id
            if institution_id is None
            else institution_id
        )

        if department_id is None and role.slug == "departmental_siwes_coordinator":
            department_id = self.department.id

        application = RoleApplication(
            user_id=self.applicant.id,
            requested_role_id=role.id,
            institution_id=institution_id,
            department_id=department_id,
            academic_session="2026/2027",
            official_position="SIWES Coordinator",
            status=status or RoleApplication.STATUS_SUBMITTED,
        )
        db.session.add(application)
        db.session.commit()
        return application

    def test_platform_admin_can_mark_coordinator_application_under_review(self):
        application = self._application()

        result = mark_role_application_under_review(
            application,
            self.platform_reviewer,
        )

        self.assertEqual(result.status, RoleApplication.STATUS_UNDER_REVIEW)
        self.assertEqual(
            result.reviewed_by_user_id,
            self.platform_reviewer.id,
        )
        self.assertIsNotNone(result.review_started_at)

    def test_institution_admin_can_review_coordinator_in_own_institution(self):
        application = self._application()

        result = mark_role_application_under_review(
            application,
            self.institution_reviewer,
        )

        self.assertEqual(result.status, RoleApplication.STATUS_UNDER_REVIEW)

    def test_institution_admin_cannot_review_other_institution(self):
        application = self._application(
            institution_id=self.other_institution.id,
            department_id=self.other_department.id,
        )

        with self.assertRaises(RoleReviewError):
            mark_role_application_under_review(
                application,
                self.institution_reviewer,
            )

    def test_unauthorized_user_cannot_review(self):
        application = self._application()

        with self.assertRaises(RoleReviewError):
            mark_role_application_under_review(
                application,
                self.unauthorized_user,
            )

    def test_applicant_cannot_review_own_application(self):
        # Give applicant the global platform reviewer role so the test proves
        # that explicit permission still does not allow self-review.
        db.session.add(
            UserRoleAssignment(
                user_id=self.applicant.id,
                role_id=self.platform_admin_role.id,
                status="Approved",
                approved_at=datetime.utcnow(),
            )
        )
        db.session.commit()

        application = self._application()

        with self.assertRaises(RoleReviewError):
            mark_role_application_under_review(
                application,
                self.applicant,
            )

    def test_request_more_information_requires_notes(self):
        application = self._application()

        with self.assertRaises(RoleReviewError):
            request_role_application_more_information(
                application,
                self.platform_reviewer,
                "   ",
            )

    def test_request_more_information_updates_status(self):
        application = self._application()

        result = request_role_application_more_information(
            application,
            self.platform_reviewer,
            "Please provide your appointment letter.",
        )

        self.assertEqual(
            result.status,
            RoleApplication.STATUS_MORE_INFO_REQUIRED,
        )
        self.assertEqual(
            result.reviewer_notes,
            "Please provide your appointment letter.",
        )

    def test_more_info_application_can_return_to_under_review(self):
        application = self._application(
            status=RoleApplication.STATUS_MORE_INFO_REQUIRED
        )

        result = mark_role_application_under_review(
            application,
            self.platform_reviewer,
        )

        self.assertEqual(result.status, RoleApplication.STATUS_UNDER_REVIEW)

    def test_rejection_requires_notes(self):
        application = self._application()

        with self.assertRaises(RoleReviewError):
            reject_role_application(
                application,
                self.platform_reviewer,
                "",
            )

    def test_reviewer_can_reject_open_application(self):
        application = self._application(
            status=RoleApplication.STATUS_UNDER_REVIEW
        )

        result = reject_role_application(
            application,
            self.platform_reviewer,
            "Evidence could not be verified.",
        )

        self.assertEqual(result.status, RoleApplication.STATUS_REJECTED)
        self.assertIsNotNone(result.decided_at)

    def test_final_application_cannot_be_rejected_again(self):
        application = self._application(
            status=RoleApplication.STATUS_APPROVED
        )

        with self.assertRaises(RoleReviewError):
            reject_role_application(
                application,
                self.platform_reviewer,
                "No longer valid.",
            )

    def test_applicant_can_withdraw_own_open_application(self):
        application = self._application()

        result = withdraw_role_application(
            application,
            self.applicant,
        )

        self.assertEqual(result.status, RoleApplication.STATUS_WITHDRAWN)
        self.assertIsNotNone(result.decided_at)

    def test_other_user_cannot_withdraw_application(self):
        application = self._application()

        with self.assertRaises(RoleReviewError):
            withdraw_role_application(
                application,
                self.unauthorized_user,
            )

    def test_final_application_cannot_be_withdrawn(self):
        application = self._application(
            status=RoleApplication.STATUS_REJECTED
        )

        with self.assertRaises(RoleReviewError):
            withdraw_role_application(
                application,
                self.applicant,
            )

    def test_inactive_reviewer_cannot_review(self):
        self.platform_reviewer.account_status = "Suspended"
        db.session.commit()

        application = self._application()

        with self.assertRaises(RoleReviewError):
            mark_role_application_under_review(
                application,
                self.platform_reviewer,
            )

    def test_inactive_applicant_cannot_withdraw(self):
        self.applicant.account_status = "Suspended"
        db.session.commit()

        application = self._application()

        with self.assertRaises(RoleReviewError):
            withdraw_role_application(
                application,
                self.applicant,
            )

    def test_institution_admin_cannot_review_institution_admin_application(self):
        application = self._application(
            role=self.institution_admin_role,
            department_id=None,
        )

        with self.assertRaises(RoleReviewError):
            mark_role_application_under_review(
                application,
                self.institution_reviewer,
            )

    def test_platform_admin_can_review_institution_admin_application(self):
        application = self._application(
            role=self.institution_admin_role,
            department_id=None,
        )

        result = mark_role_application_under_review(
            application,
            self.platform_reviewer,
        )

        self.assertEqual(result.status, RoleApplication.STATUS_UNDER_REVIEW)


if __name__ == "__main__":
    unittest.main()
