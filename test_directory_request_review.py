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

if __name__ == "__main__":
    unittest.main()
