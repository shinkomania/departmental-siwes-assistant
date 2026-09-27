"""Tests for the secured DirectoryRequest review service."""

import unittest

from app import create_app
from models.db import db
from models.directory_request import DirectoryRequest
from models.user import User
from models.access import Role, Permission, UserRoleAssignment


class DirectoryRequestReviewServiceTestCase(unittest.TestCase):
    """Security and transition tests for academic directory review."""

    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        permission = Permission(
            slug="access_platform_admin_panel",
            name="Access Platform Admin Panel",
        )
        role = Role(
            slug="platform_administrator",
            name="Platform Administrator",
            is_active=True,
        )
        role.permissions.append(permission)

        self.reviewer = User(
            full_name="Directory Review Admin",
            email="directory-review-admin@example.com",
            password_hash="test-password-hash",
            account_status="Active",
        )
        self.ordinary_user = User(
            full_name="Ordinary Review User",
            email="ordinary-review-user@example.com",
            password_hash="test-password-hash",
            account_status="Active",
        )
        self.requester = User(
            full_name="Directory Requester",
            email="directory-requester@example.com",
            password_hash="test-password-hash",
            account_status="Active",
        )

        db.session.add_all([
            permission,
            role,
            self.reviewer,
            self.ordinary_user,
            self.requester,
        ])
        db.session.flush()

        assignment = UserRoleAssignment(
            user_id=self.reviewer.id,
            role_id=role.id,
            status="Approved",
        )
        db.session.add(assignment)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _directory_request(self, status=DirectoryRequest.STATUS_SUBMITTED):
        directory_request = DirectoryRequest(
            user_id=self.requester.id,
            request_type=DirectoryRequest.TYPE_INSTITUTION,
            institution_name="Review Test University",
            status=status,
        )

        if status == DirectoryRequest.STATUS_UNDER_REVIEW:
            directory_request.reviewed_by_user_id = self.reviewer.id
        db.session.add(directory_request)
        db.session.commit()
        return directory_request

    def test_platform_admin_can_mark_submitted_request_under_review(self):
        from services.directory_request_review import mark_directory_request_under_review

        directory_request = self._directory_request()

        result = mark_directory_request_under_review(
            directory_request,
            self.reviewer,
        )

        self.assertEqual(result.status, DirectoryRequest.STATUS_UNDER_REVIEW)

    def test_mark_under_review_records_reviewer_and_start_time(self):
        from services.directory_request_review import mark_directory_request_under_review

        directory_request = self._directory_request()

        result = mark_directory_request_under_review(
            directory_request,
            self.reviewer,
        )

        self.assertEqual(result.reviewed_by_user_id, self.reviewer.id)
        self.assertIsNotNone(result.review_started_at)

    def test_unauthorized_user_cannot_mark_request_under_review(self):
        from services.directory_request_review import (
            DirectoryRequestReviewError,
            mark_directory_request_under_review,
        )

        directory_request = self._directory_request()

        with self.assertRaises(DirectoryRequestReviewError):
            mark_directory_request_under_review(
                directory_request,
                self.ordinary_user,
            )

        self.assertEqual(directory_request.status, DirectoryRequest.STATUS_SUBMITTED)

    def test_final_request_cannot_be_marked_under_review(self):
        from services.directory_request_review import (
            DirectoryRequestReviewError,
            mark_directory_request_under_review,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_APPROVED
        )

        with self.assertRaises(DirectoryRequestReviewError):
            mark_directory_request_under_review(
                directory_request,
                self.reviewer,
            )

        self.assertEqual(directory_request.status, DirectoryRequest.STATUS_APPROVED)

    def test_platform_admin_can_request_more_information(self):
        from services.directory_request_review import (
            request_directory_request_more_information,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_UNDER_REVIEW
        )

        result = request_directory_request_more_information(
            directory_request,
            self.reviewer,
            "Please provide an official university webpage.",
        )

        self.assertEqual(
            result.status,
            DirectoryRequest.STATUS_MORE_INFO_REQUIRED,
        )
        self.assertEqual(
            result.reviewer_notes,
            "Please provide an official university webpage.",
        )

    def test_request_more_information_creates_reviewer_history_message(self):
        from models.directory_request import DirectoryRequestMessage
        from services.directory_request_review import (
            request_directory_request_more_information,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_UNDER_REVIEW
        )

        request_directory_request_more_information(
            directory_request,
            self.reviewer,
            "Please provide an official university webpage.",
        )

        messages = directory_request.clarification_messages.all()

        self.assertEqual(len(messages), 1)

        message = messages[0]

        self.assertEqual(
            message.author_type,
            DirectoryRequestMessage.AUTHOR_REVIEWER,
        )
        self.assertEqual(message.author_user_id, self.reviewer.id)
        self.assertEqual(
            message.message,
            "Please provide an official university webpage.",
        )
        self.assertIsNone(message.evidence_reference)
    def test_request_more_information_records_reviewer_and_start_time(self):
        from services.directory_request_review import (
            request_directory_request_more_information,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_UNDER_REVIEW
        )

        result = request_directory_request_more_information(
            directory_request,
            self.reviewer,
            "Please provide additional official evidence.",
        )

        self.assertEqual(result.reviewed_by_user_id, self.reviewer.id)
        self.assertIsNotNone(result.review_started_at)

    def test_request_more_information_requires_reviewer_notes(self):
        from services.directory_request_review import (
            DirectoryRequestReviewError,
            request_directory_request_more_information,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_UNDER_REVIEW
        )

        with self.assertRaises(DirectoryRequestReviewError):
            request_directory_request_more_information(
                directory_request,
                self.reviewer,
                "   ",
            )

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_UNDER_REVIEW,
        )

    def test_final_request_cannot_request_more_information(self):
        from services.directory_request_review import (
            DirectoryRequestReviewError,
            request_directory_request_more_information,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_APPROVED
        )

        with self.assertRaises(DirectoryRequestReviewError):
            request_directory_request_more_information(
                directory_request,
                self.reviewer,
                "Please provide more information.",
            )

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_APPROVED,
        )

    def test_requester_can_respond_to_more_information_request(self):
        from models.directory_request import DirectoryRequestMessage
        from services.directory_request_review import (
            respond_to_directory_request_more_information,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_MORE_INFO_REQUIRED
        )
        directory_request.reviewed_by_user_id = self.reviewer.id
        db.session.commit()

        result = respond_to_directory_request_more_information(
            directory_request,
            self.requester,
            "The official university directory confirms the institution.",
            "https://example.edu/directory",
        )

        self.assertEqual(
            result.status,
            DirectoryRequest.STATUS_UNDER_REVIEW,
        )
        self.assertEqual(
            result.reviewed_by_user_id,
            self.reviewer.id,
        )

        messages = directory_request.clarification_messages.all()
        self.assertEqual(len(messages), 1)

        message = messages[0]
        self.assertEqual(
            message.author_type,
            DirectoryRequestMessage.AUTHOR_REQUESTER,
        )
        self.assertEqual(message.author_user_id, self.requester.id)
        self.assertEqual(
            message.message,
            "The official university directory confirms the institution.",
        )
        self.assertEqual(
            message.evidence_reference,
            "https://example.edu/directory",
        )

    def test_requester_clarification_requires_message(self):
        from services.directory_request_review import (
            DirectoryRequestReviewError,
            respond_to_directory_request_more_information,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_MORE_INFO_REQUIRED
        )
        directory_request.reviewed_by_user_id = self.reviewer.id
        db.session.commit()

        with self.assertRaises(DirectoryRequestReviewError):
            respond_to_directory_request_more_information(
                directory_request,
                self.requester,
                "   ",
            )

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_MORE_INFO_REQUIRED,
        )
        self.assertEqual(
            directory_request.clarification_messages.count(),
            0,
        )

    def test_different_user_cannot_respond_to_directory_request(self):
        from models.user import User
        from services.directory_request_review import (
            DirectoryRequestReviewError,
            respond_to_directory_request_more_information,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_MORE_INFO_REQUIRED
        )
        directory_request.reviewed_by_user_id = self.reviewer.id

        other_user = User(
            full_name="Different Requester",
            email="different.requester@example.com",
        )
        other_user.set_password("DifferentPass123!")

        db.session.add(other_user)
        db.session.commit()

        with self.assertRaises(DirectoryRequestReviewError):
            respond_to_directory_request_more_information(
                directory_request,
                other_user,
                "Attempted response.",
            )

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_MORE_INFO_REQUIRED,
        )
        self.assertEqual(
            directory_request.clarification_messages.count(),
            0,
        )

    def test_requester_cannot_respond_when_more_information_not_required(self):
        from services.directory_request_review import (
            DirectoryRequestReviewError,
            respond_to_directory_request_more_information,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_UNDER_REVIEW
        )

        with self.assertRaises(DirectoryRequestReviewError):
            respond_to_directory_request_more_information(
                directory_request,
                self.requester,
                "Additional information.",
            )

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_UNDER_REVIEW,
        )
        self.assertEqual(
            directory_request.clarification_messages.count(),
            0,
        )
    def test_platform_admin_can_approve_under_review_request(self):
        from services.directory_request_review import (
            approve_directory_request,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_UNDER_REVIEW
        )

        result = approve_directory_request(
            directory_request,
            self.reviewer,
            "Official evidence reviewed.",
        )

        self.assertEqual(
            result.status,
            DirectoryRequest.STATUS_APPROVED,
        )
        self.assertEqual(
            result.reviewer_notes,
            "Official evidence reviewed.",
        )

    def test_approve_records_reviewer_and_decision_time(self):
        from services.directory_request_review import (
            approve_directory_request,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_UNDER_REVIEW
        )

        result = approve_directory_request(
            directory_request,
            self.reviewer,
        )

        self.assertEqual(result.reviewed_by_user_id, self.reviewer.id)
        self.assertIsNotNone(result.review_started_at)
        self.assertIsNotNone(result.decided_at)

    def test_approve_allows_blank_reviewer_notes(self):
        from services.directory_request_review import (
            approve_directory_request,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_UNDER_REVIEW
        )

        result = approve_directory_request(
            directory_request,
            self.reviewer,
            "   ",
        )

        self.assertEqual(
            result.status,
            DirectoryRequest.STATUS_APPROVED,
        )
        self.assertIsNone(result.reviewer_notes)

    def test_final_request_cannot_be_approved(self):
        from services.directory_request_review import (
            DirectoryRequestReviewError,
            approve_directory_request,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_REJECTED
        )

        with self.assertRaises(DirectoryRequestReviewError):
            approve_directory_request(
                directory_request,
                self.reviewer,
            )

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_REJECTED,
        )

    def test_platform_admin_can_reject_under_review_request(self):
        from services.directory_request_review import (
            reject_directory_request,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_UNDER_REVIEW
        )

        result = reject_directory_request(
            directory_request,
            self.reviewer,
            "Submitted evidence could not be verified.",
        )

        self.assertEqual(
            result.status,
            DirectoryRequest.STATUS_REJECTED,
        )
        self.assertEqual(
            result.reviewer_notes,
            "Submitted evidence could not be verified.",
        )

    def test_reject_records_reviewer_and_decision_time(self):
        from services.directory_request_review import (
            reject_directory_request,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_UNDER_REVIEW
        )

        result = reject_directory_request(
            directory_request,
            self.reviewer,
            "Request does not meet directory requirements.",
        )

        self.assertEqual(result.reviewed_by_user_id, self.reviewer.id)
        self.assertIsNotNone(result.review_started_at)
        self.assertIsNotNone(result.decided_at)

    def test_reject_requires_reviewer_notes(self):
        from services.directory_request_review import (
            DirectoryRequestReviewError,
            reject_directory_request,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_UNDER_REVIEW
        )

        with self.assertRaises(DirectoryRequestReviewError):
            reject_directory_request(
                directory_request,
                self.reviewer,
                "   ",
            )

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_UNDER_REVIEW,
        )

    def test_final_request_cannot_be_rejected(self):
        from services.directory_request_review import (
            DirectoryRequestReviewError,
            reject_directory_request,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_APPROVED
        )

        with self.assertRaises(DirectoryRequestReviewError):
            reject_directory_request(
                directory_request,
                self.reviewer,
                "Attempted rejection.",
            )

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_APPROVED,
        )
    def _second_platform_admin(self):
        from datetime import datetime

        from models import Permission, Role, User, UserRoleAssignment

        permission = Permission.query.filter_by(
            slug="access_platform_admin_panel"
        ).first()

        if permission is None:
            permission = Permission(
                name="Access Platform Admin Panel",
                slug="access_platform_admin_panel",
                description="Test permission for Platform Admin access.",
                is_active=True,
            )
            db.session.add(permission)
            db.session.flush()

        role = Role(
            name="Second Test Platform Administrator",
            slug="second_test_platform_administrator",
            description="Second Platform Admin used for review ownership tests.",
            is_active=True,
        )
        role.permissions.append(permission)

        second_admin = User(
            full_name="Second Review Administrator",
            email="second-review-admin@example.com",
            password_hash="test-password-hash",
            account_status="Active",
        )

        db.session.add_all([role, second_admin])
        db.session.flush()

        assignment = UserRoleAssignment(
            user_id=second_admin.id,
            role_id=role.id,
            institution_id=None,
            department_id=None,
            programme_id=None,
            status="Approved",
            approved_at=datetime.utcnow(),
        )

        db.session.add(assignment)
        db.session.commit()

        return second_admin

    def test_different_platform_admin_cannot_request_more_information(self):
        from services.directory_request_review import (
            DirectoryRequestReviewError,
            request_directory_request_more_information,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_UNDER_REVIEW
        )
        directory_request.reviewed_by_user_id = self.reviewer.id
        db.session.commit()

        second_admin = self._second_platform_admin()

        with self.assertRaises(DirectoryRequestReviewError):
            request_directory_request_more_information(
                directory_request,
                second_admin,
                "Please provide additional evidence.",
            )

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_UNDER_REVIEW,
        )
        self.assertEqual(
            directory_request.reviewed_by_user_id,
            self.reviewer.id,
        )

    def test_different_platform_admin_cannot_approve_claimed_request(self):
        from services.directory_request_review import (
            DirectoryRequestReviewError,
            approve_directory_request,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_UNDER_REVIEW
        )
        directory_request.reviewed_by_user_id = self.reviewer.id
        db.session.commit()

        second_admin = self._second_platform_admin()

        with self.assertRaises(DirectoryRequestReviewError):
            approve_directory_request(
                directory_request,
                second_admin,
                "Attempted approval by another reviewer.",
            )

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_UNDER_REVIEW,
        )
        self.assertEqual(
            directory_request.reviewed_by_user_id,
            self.reviewer.id,
        )

    def test_different_platform_admin_cannot_reject_claimed_request(self):
        from services.directory_request_review import (
            DirectoryRequestReviewError,
            reject_directory_request,
        )

        directory_request = self._directory_request(
            status=DirectoryRequest.STATUS_UNDER_REVIEW
        )
        directory_request.reviewed_by_user_id = self.reviewer.id
        db.session.commit()

        second_admin = self._second_platform_admin()

        with self.assertRaises(DirectoryRequestReviewError):
            reject_directory_request(
                directory_request,
                second_admin,
                "Attempted rejection by another reviewer.",
            )

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_UNDER_REVIEW,
        )
        self.assertEqual(
            directory_request.reviewed_by_user_id,
            self.reviewer.id,
        )

if __name__ == "__main__":
    unittest.main()
