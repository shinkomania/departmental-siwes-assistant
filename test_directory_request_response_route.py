import unittest

from app import create_app
from models import db, User, DirectoryRequest, DirectoryRequestMessage


class DirectoryRequestResponseRouteTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        db.create_all()

        self.requester = User(
            full_name="Directory Request Student",
            email="directory-response@example.com",
            account_status="Active",
        )
        self.requester.set_password("RequesterPass123!")

        self.other_user = User(
            full_name="Other Student",
            email="other-directory-user@example.com",
            account_status="Active",
        )
        self.other_user.set_password("OtherPass123!")

        self.reviewer = User(
            full_name="Assigned Reviewer",
            email="assigned-reviewer@example.com",
            account_status="Active",
        )
        self.reviewer.set_password("ReviewerPass123!")

        db.session.add_all([
            self.requester,
            self.other_user,
            self.reviewer,
        ])
        db.session.flush()

        self.directory_request = DirectoryRequest(
            user_id=self.requester.id,
            request_type=DirectoryRequest.TYPE_INSTITUTION,
            institution_name="Clarification Test University",
            status=DirectoryRequest.STATUS_MORE_INFO_REQUIRED,
            reviewed_by_user_id=self.reviewer.id,
            reviewer_notes="Please provide official evidence.",
        )

        db.session.add(self.directory_request)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, user):
        with self.client.session_transaction() as sess:
            sess.clear()
            sess["user_id"] = user.id

    def test_requester_can_submit_clarification(self):
        self._login(self.requester)

        response = self.client.post(
            (
                f"/academic/directory-requests/"
                f"{self.directory_request.id}/respond"
            ),
            data={
                "clarification_message": (
                    "The institution's official website confirms the details."
                ),
                "evidence_reference": "https://example.edu/official",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)

        db.session.refresh(self.directory_request)

        self.assertEqual(
            self.directory_request.status,
            DirectoryRequest.STATUS_UNDER_REVIEW,
        )
        self.assertEqual(
            self.directory_request.reviewed_by_user_id,
            self.reviewer.id,
        )

        messages = self.directory_request.clarification_messages.all()
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            messages[0].author_type,
            DirectoryRequestMessage.AUTHOR_REQUESTER,
        )
        self.assertEqual(
            messages[0].evidence_reference,
            "https://example.edu/official",
        )

    def test_other_user_cannot_respond_to_request(self):
        self._login(self.other_user)

        response = self.client.post(
            (
                f"/academic/directory-requests/"
                f"{self.directory_request.id}/respond"
            ),
            data={
                "clarification_message": "Unauthorized response.",
            },
        )

        self.assertEqual(response.status_code, 404)

        db.session.refresh(self.directory_request)

        self.assertEqual(
            self.directory_request.status,
            DirectoryRequest.STATUS_MORE_INFO_REQUIRED,
        )
        self.assertEqual(
            self.directory_request.clarification_messages.count(),
            0,
        )

    def test_unauthenticated_user_cannot_respond(self):
        response = self.client.post(
            (
                f"/academic/directory-requests/"
                f"{self.directory_request.id}/respond"
            ),
            data={
                "clarification_message": "Unauthenticated response.",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

        db.session.refresh(self.directory_request)

        self.assertEqual(
            self.directory_request.status,
            DirectoryRequest.STATUS_MORE_INFO_REQUIRED,
        )

    def test_blank_clarification_does_not_change_request(self):
        self._login(self.requester)

        response = self.client.post(
            (
                f"/academic/directory-requests/"
                f"{self.directory_request.id}/respond"
            ),
            data={
                "clarification_message": "   ",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)

        db.session.refresh(self.directory_request)

        self.assertEqual(
            self.directory_request.status,
            DirectoryRequest.STATUS_MORE_INFO_REQUIRED,
        )
        self.assertEqual(
            self.directory_request.clarification_messages.count(),
            0,
        )


    def test_requester_can_open_directory_request_list(self):
        self._login(self.requester)

        response = self.client.get("/academic/directory-requests")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"My Directory Requests", response.data)
        self.assertIn(
            b"Clarification Test University",
            response.data,
        )

    def test_requester_can_open_own_directory_request_detail(self):
        self._login(self.requester)

        response = self.client.get(
            f"/academic/directory-requests/{self.directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Clarification Test University",
            response.data,
        )
        self.assertIn(b"More Info Required", response.data)
        self.assertIn(b"Provide clarification", response.data)
        self.assertIn(b'csrf_token', response.data)

    def test_other_user_cannot_view_directory_request_detail(self):
        self._login(self.other_user)

        response = self.client.get(
            f"/academic/directory-requests/{self.directory_request.id}"
        )

        self.assertEqual(response.status_code, 404)

    def test_missing_directory_request_detail_returns_404(self):
        self._login(self.requester)

        response = self.client.get(
            "/academic/directory-requests/999999"
        )

        self.assertEqual(response.status_code, 404)

    def test_detail_renders_clarification_history(self):
        reviewer_message = DirectoryRequestMessage(
            directory_request_id=self.directory_request.id,
            author_user_id=self.reviewer.id,
            author_type=DirectoryRequestMessage.AUTHOR_REVIEWER,
            message="Please provide the institution's official webpage.",
        )

        db.session.add(reviewer_message)
        db.session.commit()

        self._login(self.requester)

        response = self.client.get(
            f"/academic/directory-requests/{self.directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)
        from html import unescape

        rendered_html = unescape(response.get_data(as_text=True))

        self.assertIn(
            "Please provide the institution's official webpage.",
            rendered_html,
        )
        self.assertIn(
            "DSA Directory Reviewer",
            rendered_html,
        )

    def test_response_form_hidden_when_more_info_not_required(self):
        self.directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        db.session.commit()

        self._login(self.requester)

        response = self.client.get(
            f"/academic/directory-requests/{self.directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Submit Clarification", response.data)

    def test_unauthenticated_user_cannot_open_directory_request_list(self):
        response = self.client.get(
            "/academic/directory-requests",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    def test_successful_response_redirects_to_request_detail(self):
        self._login(self.requester)

        response = self.client.post(
            (
                f"/academic/directory-requests/"
                f"{self.directory_request.id}/respond"
            ),
            data={
                "clarification_message": "Requested clarification supplied.",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            f"/academic/directory-requests/{self.directory_request.id}",
            response.location,
        )

if __name__ == "__main__":
    unittest.main()