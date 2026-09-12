"""
Tests for DSA Administrative Role Applications
----------------------------------------------
Covers creation and review-state transitions for privileged role requests.

Important:
RoleApplication approval records the review decision only.
It does not itself grant permissions or create a UserRoleAssignment.
"""

import unittest

from app import create_app
from models.db import db
from models.user import User
from models.academic import Institution, AcademicUnit, Department
from models.access import Role
from models.role_application import RoleApplication


class RoleApplicationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.applicant = User(
            full_name="Coordinator Applicant",
            email="applicant@example.com",
            phone="08000000001",
            account_status="Active",
            email_verified=True,
        )
        self.applicant.set_password("test-password")

        self.reviewer = User(
            full_name="Platform Reviewer",
            email="reviewer@example.com",
            phone="08000000002",
            account_status="Active",
            email_verified=True,
        )
        self.reviewer.set_password("test-password")

        self.institution = Institution(
            name="Test University",
            institution_type="University",
            state="Kaduna",
            directory_status="Verified",
            administration_status="Claimed",
            is_active=True,
        )

        self.role = Role(
            name="Departmental SIWES Coordinator",
            slug="departmental_siwes_coordinator",
            description="Department-scoped SIWES coordinator",
            is_active=True,
        )

        db.session.add_all([
            self.applicant,
            self.reviewer,
            self.institution,
            self.role,
        ])
        db.session.flush()

        self.faculty = AcademicUnit(
            institution_id=self.institution.id,
            name="Faculty of Engineering",
            unit_type="Faculty",
            is_active=True,
        )
        db.session.add(self.faculty)
        db.session.flush()

        self.department = Department(
            academic_unit_id=self.faculty.id,
            name="Computer Engineering",
            is_active=True,
        )
        db.session.add(self.department)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _create_application(self):
        application = RoleApplication(
            user_id=self.applicant.id,
            requested_role_id=self.role.id,
            institution_id=self.institution.id,
            department_id=self.department.id,
            academic_session="2025/2026",
            official_position="Departmental SIWES Coordinator",
            institutional_email="coordinator@testuniversity.edu.ng",
            phone="08000000001",
            verification_method="Appointment Letter",
            evidence_reference="Appointment letter reference TEST-001",
            applicant_notes="Requesting coordinator access for the session.",
        )

        db.session.add(application)
        db.session.commit()
        return application

    def test_role_application_defaults_to_submitted(self):
        """A newly created application starts in Submitted state."""
        application = self._create_application()

        self.assertIsNotNone(application.id)
        self.assertEqual(
            application.status,
            RoleApplication.STATUS_SUBMITTED,
        )
        self.assertTrue(application.is_open)
        self.assertFalse(application.is_final)
        self.assertEqual(application.user_id, self.applicant.id)
        self.assertEqual(application.requested_role_id, self.role.id)
        self.assertEqual(application.institution_id, self.institution.id)
        self.assertEqual(application.department_id, self.department.id)

    def test_mark_under_review(self):
        """Reviewer can move an open application to Under Review."""
        application = self._create_application()

        application.mark_under_review(self.reviewer.id)
        db.session.commit()

        self.assertEqual(
            application.status,
            RoleApplication.STATUS_UNDER_REVIEW,
        )
        self.assertEqual(
            application.reviewed_by_user_id,
            self.reviewer.id,
        )
        self.assertIsNotNone(application.review_started_at)
        self.assertTrue(application.is_open)
        self.assertFalse(application.is_final)

    def test_request_more_information(self):
        """Reviewer can request more information without finalizing the case."""
        application = self._create_application()

        application.request_more_information(
            self.reviewer.id,
            "Please provide a clearer appointment letter.",
        )
        db.session.commit()

        self.assertEqual(
            application.status,
            RoleApplication.STATUS_MORE_INFO_REQUIRED,
        )
        self.assertEqual(
            application.reviewed_by_user_id,
            self.reviewer.id,
        )
        self.assertEqual(
            application.reviewer_notes,
            "Please provide a clearer appointment letter.",
        )
        self.assertTrue(application.is_open)
        self.assertFalse(application.is_final)

    def test_approve_application_records_decision(self):
        """Approval records a final review decision."""
        application = self._create_application()

        application.approve(
            self.reviewer.id,
            "Institutional appointment confirmed.",
        )
        db.session.commit()

        self.assertEqual(
            application.status,
            RoleApplication.STATUS_APPROVED,
        )
        self.assertEqual(
            application.reviewed_by_user_id,
            self.reviewer.id,
        )
        self.assertEqual(
            application.reviewer_notes,
            "Institutional appointment confirmed.",
        )
        self.assertIsNotNone(application.decided_at)
        self.assertFalse(application.is_open)
        self.assertTrue(application.is_final)

    def test_reject_application_records_decision(self):
        """Rejection records a final review decision."""
        application = self._create_application()

        application.reject(
            self.reviewer.id,
            "Unable to verify the submitted evidence.",
        )
        db.session.commit()

        self.assertEqual(
            application.status,
            RoleApplication.STATUS_REJECTED,
        )
        self.assertEqual(
            application.reviewed_by_user_id,
            self.reviewer.id,
        )
        self.assertEqual(
            application.reviewer_notes,
            "Unable to verify the submitted evidence.",
        )
        self.assertIsNotNone(application.decided_at)
        self.assertTrue(application.is_final)

    def test_withdraw_application(self):
        """Applicant-side withdrawal moves the application to a final state."""
        application = self._create_application()

        application.withdraw()
        db.session.commit()

        self.assertEqual(
            application.status,
            RoleApplication.STATUS_WITHDRAWN,
        )
        self.assertIsNotNone(application.decided_at)
        self.assertFalse(application.is_open)
        self.assertTrue(application.is_final)
