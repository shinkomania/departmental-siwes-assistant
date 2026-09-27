import unittest

from app import create_app
from models import (
    db,
    User,
    DirectoryRequest,
    DirectoryRequestMessage,
)


class DirectoryRequestMessageTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.requester = User(
            full_name="Directory Requester",
            email="directory.requester@example.com",
        )
        self.requester.set_password("RequesterPass123!")

        self.reviewer = User(
            full_name="Platform Reviewer",
            email="platform.reviewer@example.com",
        )
        self.reviewer.set_password("ReviewerPass123!")

        db.session.add_all([self.requester, self.reviewer])
        db.session.flush()

        self.directory_request = DirectoryRequest(
            user_id=self.requester.id,
            request_type=DirectoryRequest.TYPE_INSTITUTION,
            institution_name="Clarification Test University",
        )

        db.session.add(self.directory_request)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_clarification_messages_preserve_request_history(self):
        reviewer_message = DirectoryRequestMessage(
            directory_request_id=self.directory_request.id,
            author_user_id=self.reviewer.id,
            author_type=DirectoryRequestMessage.AUTHOR_REVIEWER,
            message="Please provide an official verification source.",
        )

        requester_message = DirectoryRequestMessage(
            directory_request_id=self.directory_request.id,
            author_user_id=self.requester.id,
            author_type=DirectoryRequestMessage.AUTHOR_REQUESTER,
            message="Here is the requested official source.",
            evidence_reference="https://example.edu/official-directory",
        )

        db.session.add(reviewer_message)
        db.session.commit()

        db.session.add(requester_message)
        db.session.commit()

        messages = self.directory_request.clarification_messages.all()

        self.assertEqual(len(messages), 2)

        self.assertEqual(
            messages[0].author_type,
            DirectoryRequestMessage.AUTHOR_REVIEWER,
        )
        self.assertEqual(
            messages[0].author_user_id,
            self.reviewer.id,
        )

        self.assertEqual(
            messages[1].author_type,
            DirectoryRequestMessage.AUTHOR_REQUESTER,
        )
        self.assertEqual(
            messages[1].author_user_id,
            self.requester.id,
        )
        self.assertEqual(
            messages[1].evidence_reference,
            "https://example.edu/official-directory",
        )

        self.assertEqual(messages[0].directory_request_id, self.directory_request.id)
        self.assertEqual(messages[1].directory_request_id, self.directory_request.id)


if __name__ == "__main__":
    unittest.main()