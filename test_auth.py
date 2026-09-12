"""
Authentication Test Suite for Departmental SIWES Assistant (DSA)
----------------------------------------------------------------
Tests unified User registration, login, logout, account status,
session behavior, password handling, and safe redirects.
"""

import unittest

from app import create_app
from models.db import db
from models.user import User


class AuthenticationTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()

        self.app_context = self.app.app_context()
        self.app_context.push()

        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _create_user(
        self,
        email="existing@example.com",
        password="Test12345",
        account_status="Active",
    ):
        user = User(
            full_name="Existing DSA User",
            email=email,
            phone="08000000000",
            account_status=account_status,
            email_verified=False,
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        return user

    def test_register_page_loads(self):
        response = self.client.get("/auth/register")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Create Your DSA Account", response.data)

    def test_login_page_loads(self):
        response = self.client.get("/auth/login")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome Back", response.data)

    def test_registration_creates_user_and_logs_in(self):
        response = self.client.post(
            "/auth/register",
            data={
                "full_name": "Test DSA User",
                "email": "newuser@example.com",
                "phone": "08012345678",
                "password": "Test12345",
                "confirm_password": "Test12345",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        user = User.query.filter_by(
            email="newuser@example.com"
        ).first()

        self.assertIsNotNone(user)
        self.assertEqual(user.full_name, "Test DSA User")
        self.assertEqual(user.phone, "08012345678")
        self.assertEqual(user.account_status, "Active")
        self.assertFalse(user.email_verified)

        # Password must be hashed rather than stored directly.
        self.assertNotEqual(user.password_hash, "Test12345")
        self.assertTrue(user.check_password("Test12345"))

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("user_id"), user.id)

    def test_registration_normalizes_email(self):
        self.client.post(
            "/auth/register",
            data={
                "full_name": "Email Test",
                "email": "  TESTUSER@EXAMPLE.COM  ",
                "phone": "",
                "password": "Test12345",
                "confirm_password": "Test12345",
            },
        )

        user = User.query.filter_by(
            email="testuser@example.com"
        ).first()

        self.assertIsNotNone(user)

    def test_registration_requires_full_name(self):
        response = self.client.post(
            "/auth/register",
            data={
                "full_name": "",
                "email": "test@example.com",
                "phone": "",
                "password": "Test12345",
                "confirm_password": "Test12345",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Please enter your full name.", response.data)

        self.assertIsNone(
            User.query.filter_by(email="test@example.com").first()
        )

    def test_registration_requires_email(self):
        response = self.client.post(
            "/auth/register",
            data={
                "full_name": "Test User",
                "email": "",
                "phone": "",
                "password": "Test12345",
                "confirm_password": "Test12345",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Please enter your email address.", response.data)

    def test_registration_rejects_short_password(self):
        response = self.client.post(
            "/auth/register",
            data={
                "full_name": "Test User",
                "email": "short@example.com",
                "phone": "",
                "password": "short",
                "confirm_password": "short",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Password must contain at least 8 characters.",
            response.data,
        )

        self.assertIsNone(
            User.query.filter_by(email="short@example.com").first()
        )

    def test_registration_rejects_password_mismatch(self):
        response = self.client.post(
            "/auth/register",
            data={
                "full_name": "Test User",
                "email": "mismatch@example.com",
                "phone": "",
                "password": "Test12345",
                "confirm_password": "Different12345",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"The passwords do not match.", response.data)

        self.assertIsNone(
            User.query.filter_by(
                email="mismatch@example.com"
            ).first()
        )

    def test_registration_rejects_duplicate_email(self):
        self._create_user(email="duplicate@example.com")

        response = self.client.post(
            "/auth/register",
            data={
                "full_name": "Another User",
                "email": "DUPLICATE@EXAMPLE.COM",
                "phone": "",
                "password": "Another12345",
                "confirm_password": "Another12345",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"An account already exists with that email address.",
            response.data,
        )

        count = User.query.filter_by(
            email="duplicate@example.com"
        ).count()

        self.assertEqual(count, 1)

    def test_active_user_can_login(self):
        user = self._create_user()

        response = self.client.post(
            "/auth/login",
            data={
                "email": "existing@example.com",
                "password": "Test12345",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome back, Existing DSA User.", response.data)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("user_id"), user.id)

    def test_login_normalizes_email(self):
        user = self._create_user(
            email="normal@example.com"
        )

        response = self.client.post(
            "/auth/login",
            data={
                "email": "  NORMAL@EXAMPLE.COM  ",
                "password": "Test12345",
            },
        )

        self.assertEqual(response.status_code, 302)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("user_id"), user.id)

    def test_login_rejects_wrong_password(self):
        self._create_user()

        response = self.client.post(
            "/auth/login",
            data={
                "email": "existing@example.com",
                "password": "WrongPassword",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Invalid email address or password.",
            response.data,
        )

        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    def test_login_rejects_unknown_email(self):
        response = self.client.post(
            "/auth/login",
            data={
                "email": "unknown@example.com",
                "password": "Test12345",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Invalid email address or password.",
            response.data,
        )

        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    def test_inactive_account_cannot_login(self):
        self._create_user(
            email="suspended@example.com",
            account_status="Suspended",
        )

        response = self.client.post(
            "/auth/login",
            data={
                "email": "suspended@example.com",
                "password": "Test12345",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"This account is currently unavailable.",
            response.data,
        )

        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    def test_authenticated_user_is_redirected_from_login(self):
        user = self._create_user()

        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id

        response = self.client.get("/auth/login")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/"))

    def test_authenticated_user_is_redirected_from_register(self):
        user = self._create_user()

        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id

        response = self.client.get("/auth/register")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/"))

    def test_logout_clears_user_and_legacy_sessions(self):
        user = self._create_user()

        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["student_id"] = 999
            sess["is_admin"] = True

        response = self.client.post(
            "/auth/logout",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"You have been logged out successfully.",
            response.data,
        )

        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))
            self.assertIsNone(sess.get("student_id"))
            self.assertIsNone(sess.get("is_admin"))

    def test_logout_does_not_accept_get(self):
        response = self.client.get("/auth/logout")

        self.assertEqual(response.status_code, 405)

    def test_login_allows_safe_internal_next_redirect(self):
        self._create_user()

        response = self.client.post(
            "/auth/login?next=/about",
            data={
                "email": "existing@example.com",
                "password": "Test12345",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/about"))

    def test_login_blocks_external_next_redirect(self):
        self._create_user()

        response = self.client.post(
            "/auth/login?next=https://evil.example/phishing",
            data={
                "email": "existing@example.com",
                "password": "Test12345",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.assertFalse(
            response.location.startswith("https://evil.example")
        )

        self.assertTrue(response.location.endswith("/"))


if __name__ == "__main__":
    unittest.main()