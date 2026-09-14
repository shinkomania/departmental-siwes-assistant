"""
CSRF protection tests for the Departmental SIWES Assistant.

The normal testing configuration disables CSRF so existing tests can
exercise application behavior directly.

These tests explicitly enable CSRF to verify that the application's
real CSRF protection is functioning.
"""

import re
import unittest

from app import create_app
from models.db import db


class CSRFProtectionTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app("testing")

        # Explicitly enable CSRF for this dedicated security test.
        self.app.config["WTF_CSRF_ENABLED"] = True

        self.client = self.app.test_client()

        self.app_context = self.app.app_context()
        self.app_context.push()

        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _get_login_csrf_token(self):
        """
        Load the login form and extract its generated CSRF token.
        """
        response = self.client.get("/auth/login")

        self.assertEqual(response.status_code, 200)

        html = response.get_data(as_text=True)

        match = re.search(
            r'name="csrf_token"\s+value="([^"]+)"',
            html,
        )

        self.assertIsNotNone(
            match,
            "Login form did not contain a CSRF token.",
        )

        return match.group(1)

    def test_post_without_csrf_token_is_rejected(self):
        """
        A state-changing POST without a CSRF token must be rejected.
        """
        response = self.client.post(
            "/auth/login",
            data={
                "email": "missing@example.com",
                "password": "incorrect-password",
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_post_with_valid_csrf_token_reaches_application(self):
        """
        A valid CSRF token must allow the request past CSRF validation.
        """
        csrf_token = self._get_login_csrf_token()

        response = self.client.post(
            "/auth/login",
            data={
                "csrf_token": csrf_token,
                "email": "missing@example.com",
                "password": "incorrect-password",
            },
        )

        self.assertNotEqual(
            response.status_code,
            400,
            "A valid CSRF token was incorrectly rejected.",
        )


if __name__ == "__main__":
    unittest.main()