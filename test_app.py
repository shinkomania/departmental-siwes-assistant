"""
Automated Test Suite for Departmental SIWES Assistant (DSA)
------------------------------------------------------------
Tests database models, route endpoints, placement search,
student profile persistence, admin authentication, and
role + permission + scope authorization.
"""
import unittest
from datetime import datetime, timedelta

from app import create_app
from models.db import db
from models.student import StudentProfile
from models.organization import Organization
from models.guide import GuideTopic
from models.application import SavedOrganization, PlacementApplication
from models.user import User
from models.academic import Institution, AcademicUnit, Department, Programme
from models.access import Role, Permission, UserRoleAssignment
from models.directory_request import DirectoryRequest, DirectoryRequestMessage
from models.notification import Notification
from services.placement_search import PlacementSearchService
from services.authorization import user_has_permission
from services.notification_service import (
    NotificationServiceError,
    create_notification,
    get_notifications_for_user,
    get_unread_count_for_user,
    get_notification_for_user,
    mark_notification_read,
    mark_all_notifications_read,
)


class DSATestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.guide = GuideTopic(
            slug='test-guide',
            title='Test Guide Topic',
            category='Overview',
            order_num=1,
            summary='Test summary',
            content='Test content here'
        )
        self.org = Organization(
            name='NITDA Test',
            description='Test description',
            state='FCT Abuja',
            city='Abuja',
            industry='Government organization',
            relevance_areas='Software Development, AI',
            verification_status='Verified',
            source='Official Portal'
        )
        db.session.add_all([self.guide, self.org])
        db.session.commit()


    def _create_notification_route_users(self):
        user_a = User(
            full_name="Notification User A",
            email="notification-user-a@example.com",
            account_status="Active",
        )
        user_a.set_password("notification-user-a-password")

        user_b = User(
            full_name="Notification User B",
            email="notification-user-b@example.com",
            account_status="Active",
        )
        user_b.set_password("notification-user-b-password")

        db.session.add_all([user_a, user_b])
        db.session.commit()

        return user_a, user_b

    def _login_notification_user(self, user):
        with self.client.session_transaction() as sess:
            sess.clear()
            sess["user_id"] = user.id

    def test_notification_centre_requires_authentication(self):
        response = self.client.get(
            "/notifications/",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_notification_centre_only_shows_current_users_notifications(self):
        user_a, user_b = self._create_notification_route_users()

        notification_a = create_notification(
            recipient_user=user_a,
            category=Notification.CATEGORY_SYSTEM,
            notification_type="route_isolation_a",
            title="Private notification for User A",
            message="Only User A should see this notification.",
        )
        create_notification(
            recipient_user=user_b,
            category=Notification.CATEGORY_SYSTEM,
            notification_type="route_isolation_b",
            title="Private notification for User B",
            message="User A must never see this notification.",
        )

        self._login_notification_user(user_a)

        response = self.client.get("/notifications/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            notification_a.title.encode(),
            response.data,
        )
        self.assertNotIn(
            b"Private notification for User B",
            response.data,
        )

    def test_user_cannot_mark_another_users_notification_read(self):
        user_a, user_b = self._create_notification_route_users()

        foreign_notification = create_notification(
            recipient_user=user_b,
            category=Notification.CATEGORY_SYSTEM,
            notification_type="foreign_read_attempt",
            title="User B private notification",
            message="This belongs only to User B.",
        )

        self._login_notification_user(user_a)

        response = self.client.post(
            f"/notifications/{foreign_notification.id}/read",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 404)

        db.session.refresh(foreign_notification)

        self.assertIsNone(foreign_notification.read_at)
        self.assertFalse(foreign_notification.is_read)

    def test_user_cannot_open_another_users_notification(self):
        user_a, user_b = self._create_notification_route_users()

        foreign_notification = create_notification(
            recipient_user=user_b,
            category=Notification.CATEGORY_SYSTEM,
            notification_type="foreign_open_attempt",
            title="User B private action",
            message="User A must not open this.",
            action_url="/",
        )

        self._login_notification_user(user_a)

        response = self.client.post(
            f"/notifications/{foreign_notification.id}/open",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 404)

        db.session.refresh(foreign_notification)

        self.assertIsNone(foreign_notification.read_at)

    def test_mark_all_read_only_changes_current_users_notifications(self):
        user_a, user_b = self._create_notification_route_users()

        notification_a = create_notification(
            recipient_user=user_a,
            category=Notification.CATEGORY_SYSTEM,
            notification_type="mark_all_a",
            title="User A unread notification",
            message="This should become read.",
        )
        notification_b = create_notification(
            recipient_user=user_b,
            category=Notification.CATEGORY_SYSTEM,
            notification_type="mark_all_b",
            title="User B unread notification",
            message="This must remain unread.",
        )

        self._login_notification_user(user_a)

        response = self.client.post(
            "/notifications/read-all",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)

        db.session.refresh(notification_a)
        db.session.refresh(notification_b)

        self.assertTrue(notification_a.is_read)
        self.assertFalse(notification_b.is_read)
        self.assertIsNone(notification_b.read_at)

    def test_inactive_user_cannot_access_notification_centre_with_stale_session(self):
        inactive_user = User(
            full_name="Inactive Notification User",
            email="inactive-notification-user@example.com",
            account_status="Suspended",
        )
        inactive_user.set_password("inactive-notification-password")

        db.session.add(inactive_user)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess.clear()
            sess["user_id"] = inactive_user.id

        response = self.client.get(
            "/notifications/",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_platform_admin_cannot_open_another_users_private_notification(self):
        data = self._create_platform_admin_security_fixture()
        platform_admin = data["platform_admin"]
        managed_user = data["managed_user"]

        private_notification = create_notification(
            recipient_user=managed_user,
            category=Notification.CATEGORY_SYSTEM,
            notification_type="admin_foreign_open_attempt",
            title="Managed user private notification",
            message="Platform authority does not transfer inbox ownership.",
            action_url="/",
        )

        with self.client.session_transaction() as sess:
            sess.clear()
            sess["user_id"] = platform_admin.id

        response = self.client.post(
            f"/notifications/{private_notification.id}/open",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 404)

        db.session.refresh(private_notification)

        self.assertIsNone(private_notification.read_at)
        self.assertFalse(private_notification.is_read)
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _create_authorization_fixture(self):
        institution_a = Institution(
            name='Institution A',
            institution_type='University',
            city='Zaria',
            state='Kaduna',
            directory_status='Verified',
            administration_status='Claimed',
            is_active=True
        )
        institution_b = Institution(
            name='Institution B',
            institution_type='University',
            state='Lagos',
            directory_status='Verified',
            administration_status='Claimed',
            is_active=True
        )
        db.session.add_all([institution_a, institution_b])
        db.session.flush()

        faculty_a = AcademicUnit(
            institution_id=institution_a.id,
            name='Faculty of Engineering',
            unit_type='Faculty',
            is_active=True
        )
        faculty_b = AcademicUnit(
            institution_id=institution_b.id,
            name='Faculty of Engineering',
            unit_type='Faculty',
            is_active=True
        )
        db.session.add_all([faculty_a, faculty_b])
        db.session.flush()

        department_a = Department(
            academic_unit_id=faculty_a.id,
            name='Computer Engineering',
            is_active=True
        )
        department_a_other = Department(
            academic_unit_id=faculty_a.id,
            name='Mechanical Engineering',
            is_active=True
        )
        department_b = Department(
            academic_unit_id=faculty_b.id,
            name='Computer Engineering',
            is_active=True
        )
        db.session.add_all([department_a, department_a_other, department_b])
        db.session.flush()

        programme_a = Programme(
            department_id=department_a.id,
            name='B.Eng Computer Engineering',
            award='B.Eng',
            is_active=True
        )
        programme_a_other = Programme(
            department_id=department_a_other.id,
            name='B.Eng Mechanical Engineering',
            award='B.Eng',
            is_active=True
        )
        programme_b = Programme(
            department_id=department_b.id,
            name='B.Eng Computer Engineering',
            award='B.Eng',
            is_active=True
        )
        db.session.add_all([programme_a, programme_a_other, programme_b])
        db.session.flush()

        user = User(
            full_name='Coordinator Test',
            email='coordinator@example.com',
            phone='08000000000',
            account_status='Active',
            email_verified=True
        )
        user.set_password('test-password')

        permission = Permission(
            name='View Department Students',
            slug='view_department_students'
        )
        role = Role(
            name='Departmental SIWES Coordinator',
            slug='departmental_siwes_coordinator',
            description='Department-scoped SIWES coordinator',
            is_active=True
        )
        db.session.add_all([user, permission, role])
        db.session.flush()

        role.permissions.append(permission)

        assignment = UserRoleAssignment(
            user_id=user.id,
            role_id=role.id,
            institution_id=institution_a.id,
            department_id=department_a.id,
            status='Approved',
            academic_session='2025/2026',
            approved_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=365)
        )
        db.session.add(assignment)
        db.session.commit()

        return {
            'user': user,
            'role': role,
            'assignment': assignment,
            'institution_a': institution_a,
            'institution_b': institution_b,
            'faculty_a': faculty_a,
            'faculty_b': faculty_b,
            'department_a': department_a,
            'department_a_other': department_a_other,
            'department_b': department_b,
            'programme_a': programme_a,
            'programme_a_other': programme_a_other,
            'programme_b': programme_b,
        }

    def test_phase4_academic_directory_returns_verified_institutions(self):
        """Student institution directory exposes only active Verified records."""
        verified = Institution(
            name="Verified University",
            institution_type="University",
            city="Zaria",
            state="Kaduna",
            directory_status="Verified",
            administration_status="Unclaimed",
            is_active=True,
        )
        pending = Institution(
            name="Pending University",
            institution_type="University",
            city="Kano",
            state="Kano",
            directory_status="Pending Verification",
            administration_status="Unclaimed",
            is_active=True,
        )
        inactive = Institution(
            name="Inactive University",
            institution_type="University",
            city="Lagos",
            state="Lagos",
            directory_status="Verified",
            administration_status="Unclaimed",
            is_active=False,
        )

        db.session.add_all([verified, pending, inactive])
        db.session.commit()

        response = self.client.get("/academic/institutions")

        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        names = [item["name"] for item in data]

        self.assertIn("Verified University", names)
        self.assertNotIn("Pending University", names)
        self.assertNotIn("Inactive University", names)

        verified_item = next(
            item for item in data
            if item["name"] == "Verified University"
        )

        self.assertEqual(verified_item["city"], "Zaria")
        self.assertEqual(verified_item["state"], "Kaduna")
        self.assertEqual(verified_item["directory_status"], "Verified")

    def test_phase4_academic_directory_cascade(self):
        """Verified academic hierarchy is available through the cascade APIs."""
        fixture = self._create_authorization_fixture()

        units_response = self.client.get(
            f"/academic/institutions/{fixture['institution_a'].id}/units"
        )
        self.assertEqual(units_response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in units_response.get_json()],
            [fixture["faculty_a"].id],
        )

        departments_response = self.client.get(
            f"/academic/units/{fixture['faculty_a'].id}/departments"
        )
        self.assertEqual(departments_response.status_code, 200)

        department_ids = {
            item["id"]
            for item in departments_response.get_json()
        }

        self.assertIn(fixture["department_a"].id, department_ids)
        self.assertIn(fixture["department_a_other"].id, department_ids)
        self.assertNotIn(fixture["department_b"].id, department_ids)

        programmes_response = self.client.get(
            f"/academic/departments/{fixture['department_a'].id}/programmes"
        )
        self.assertEqual(programmes_response.status_code, 200)

        programme_ids = {
            item["id"]
            for item in programmes_response.get_json()
        }

        self.assertIn(fixture["programme_a"].id, programme_ids)
        self.assertNotIn(fixture["programme_a_other"].id, programme_ids)
        self.assertNotIn(fixture["programme_b"].id, programme_ids)

    def test_phase4_pending_institution_hierarchy_is_not_exposed(self):
        """Pending institutions cannot expose child academic records."""
        pending = Institution(
            name="Pending Polytechnic",
            institution_type="Polytechnic",
            city="Kaduna",
            state="Kaduna",
            directory_status="Pending Verification",
            administration_status="Unclaimed",
            is_active=True,
        )
        db.session.add(pending)
        db.session.flush()

        unit = AcademicUnit(
            institution_id=pending.id,
            name="School of Engineering",
            unit_type="School",
            is_active=True,
        )
        db.session.add(unit)
        db.session.flush()

        department = Department(
            academic_unit_id=unit.id,
            name="Computer Engineering Technology",
            is_active=True,
        )
        db.session.add(department)
        db.session.flush()

        programme = Programme(
            department_id=department.id,
            name="Computer Engineering Technology",
            award="ND",
            is_active=True,
        )
        db.session.add(programme)
        db.session.commit()

        units_response = self.client.get(
            f"/academic/institutions/{pending.id}/units"
        )
        departments_response = self.client.get(
            f"/academic/units/{unit.id}/departments"
        )
        programmes_response = self.client.get(
            f"/academic/departments/{department.id}/programmes"
        )

        self.assertEqual(units_response.status_code, 200)
        self.assertEqual(departments_response.status_code, 200)
        self.assertEqual(programmes_response.status_code, 200)

        self.assertEqual(units_response.get_json(), [])
        self.assertEqual(departments_response.get_json(), [])
        self.assertEqual(programmes_response.get_json(), [])

    def test_phase4_student_can_request_missing_institution(self):
        """Authenticated users can request a missing institution for review."""
        user = User(
            full_name="Directory Request Student",
            email="directory-request@example.com",
            password_hash="test-password-hash",
            account_status="Active",
        )

        db.session.add(user)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id

        response = self.client.post(
            "/academic/directory-request",
            data={
                "request_type": DirectoryRequest.TYPE_INSTITUTION,
                "institution_name": "Example College of Technology",
                "institution_type": "College of Technology",
                "city": "Example City",
                "state": "Kaduna",
                "official_website": "https://example.edu.ng",
                "evidence_reference": "https://example.edu.ng/about",
                "requester_notes": "Institution is missing from the directory.",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/profile"))

        directory_request = DirectoryRequest.query.filter_by(
            user_id=user.id,
            request_type=DirectoryRequest.TYPE_INSTITUTION,
        ).first()

        self.assertIsNotNone(directory_request)
        self.assertEqual(
            directory_request.institution_name,
            "Example College of Technology",
        )
        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_SUBMITTED,
        )
        self.assertIsNone(directory_request.institution_id)

        # A request must not automatically create authoritative directory data.
        self.assertIsNone(
            Institution.query.filter_by(
                name="Example College of Technology"
            ).first()
        )

    def test_phase4_student_can_request_missing_programme(self):
        """Programme requests use an existing verified institution."""
        fixture = self._create_authorization_fixture()

        user = User(
            full_name="Programme Request Student",
            email="programme-request@example.com",
            password_hash="test-password-hash",
            account_status="Active",
        )

        db.session.add(user)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id

        response = self.client.post(
            "/academic/directory-request",
            data={
                "request_type": DirectoryRequest.TYPE_PROGRAMME,
                "institution_id": str(fixture["institution_a"].id),
                "institution_name": "Tampered Institution Name",
                "programme_name": "B.Eng. Mechatronics Engineering",
                "award": "B.Eng.",
                "academic_unit_name": "Faculty of Engineering",
                "academic_unit_type": "Faculty",
                "department_name": "Mechatronics Engineering",
                "evidence_reference": "Official programme handbook",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/profile"))

        directory_request = DirectoryRequest.query.filter_by(
            user_id=user.id,
            request_type=DirectoryRequest.TYPE_PROGRAMME,
        ).first()

        self.assertIsNotNone(directory_request)
        self.assertEqual(
            directory_request.institution_id,
            fixture["institution_a"].id,
        )

        # Existing directory data must override submitted institution text.
        self.assertEqual(
            directory_request.institution_name,
            fixture["institution_a"].name,
        )
        self.assertEqual(
            directory_request.programme_name,
            "B.Eng. Mechatronics Engineering",
        )
        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_SUBMITTED,
        )

        # A request must not automatically create a Programme.
        self.assertIsNone(
            Programme.query.filter_by(
                name="B.Eng. Mechatronics Engineering"
            ).first()
        )

    def test_phase4_duplicate_open_directory_request_is_prevented(self):
        """The same user cannot submit the same open request repeatedly."""
        user = User(
            full_name="Duplicate Request Student",
            email="duplicate-directory-request@example.com",
            password_hash="test-password-hash",
            account_status="Active",
        )

        db.session.add(user)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id

        request_data = {
            "request_type": DirectoryRequest.TYPE_INSTITUTION,
            "institution_name": "Duplicate Test Polytechnic",
            "institution_type": "Polytechnic",
            "city": "Test City",
            "state": "Kano",
        }

        first_response = self.client.post(
            "/academic/directory-request",
            data=request_data,
            follow_redirects=False,
        )

        second_response = self.client.post(
            "/academic/directory-request",
            data=request_data,
            follow_redirects=False,
        )

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 302)

        request_count = DirectoryRequest.query.filter_by(
            user_id=user.id,
            request_type=DirectoryRequest.TYPE_INSTITUTION,
            institution_name="Duplicate Test Polytechnic",
        ).count()

        self.assertEqual(request_count, 1)

    def test_phase4_any_open_directory_request_blocks_another_request(self):
        """One open request blocks a different directory request."""
        user = User(
            full_name="Single Open Request Student",
            email="single-open-request@example.com",
            password_hash="test-password-hash",
            account_status="Active",
        )

        db.session.add(user)
        db.session.commit()

        existing_request = DirectoryRequest(
            user_id=user.id,
            request_type=DirectoryRequest.TYPE_INSTITUTION,
            institution_name="First Missing University",
            status=DirectoryRequest.STATUS_SUBMITTED,
        )

        db.session.add(existing_request)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id

        response = self.client.post(
            "/academic/directory-request",
            data={
                "request_type": DirectoryRequest.TYPE_INSTITUTION,
                "institution_name": "Second Missing University",
                "institution_type": "University",
                "state": "Kaduna",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/profile"))
        self.assertEqual(
            DirectoryRequest.query.filter_by(user_id=user.id).count(),
            1,
        )

    def test_phase4_all_open_directory_request_statuses_block_new_request(self):
        """Every non-final review status counts as an open request."""
        open_statuses = (
            DirectoryRequest.STATUS_SUBMITTED,
            DirectoryRequest.STATUS_UNDER_REVIEW,
            DirectoryRequest.STATUS_MORE_INFO_REQUIRED,
        )

        for index, status in enumerate(open_statuses):
            with self.subTest(status=status):
                user = User(
                    full_name=f"Open Status Student {index}",
                    email=f"open-status-{index}@example.com",
                    password_hash="test-password-hash",
                    account_status="Active",
                )

                db.session.add(user)
                db.session.commit()

                existing_request = DirectoryRequest(
                    user_id=user.id,
                    request_type=DirectoryRequest.TYPE_INSTITUTION,
                    institution_name=f"Existing Institution {index}",
                    status=status,
                )

                db.session.add(existing_request)
                db.session.commit()

                with self.client.session_transaction() as sess:
                    sess["user_id"] = user.id

                response = self.client.post(
                    "/academic/directory-request",
                    data={
                        "request_type": DirectoryRequest.TYPE_INSTITUTION,
                        "institution_name": f"New Institution {index}",
                    },
                    follow_redirects=False,
                )

                self.assertEqual(response.status_code, 302)
                self.assertEqual(
                    DirectoryRequest.query.filter_by(
                        user_id=user.id
                    ).count(),
                    1,
                )

    def test_phase4_final_directory_request_statuses_do_not_block_new_request(self):
        """Completed request history does not permanently block new requests."""
        final_statuses = (
            DirectoryRequest.STATUS_APPROVED,
            DirectoryRequest.STATUS_REJECTED,
            DirectoryRequest.STATUS_WITHDRAWN,
        )

        for index, status in enumerate(final_statuses):
            with self.subTest(status=status):
                user = User(
                    full_name=f"Final Status Student {index}",
                    email=f"final-status-{index}@example.com",
                    password_hash="test-password-hash",
                    account_status="Active",
                )

                db.session.add(user)
                db.session.commit()

                old_request = DirectoryRequest(
                    user_id=user.id,
                    request_type=DirectoryRequest.TYPE_INSTITUTION,
                    institution_name=f"Old Institution {index}",
                    status=status,
                )

                db.session.add(old_request)
                db.session.commit()

                with self.client.session_transaction() as sess:
                    sess["user_id"] = user.id

                response = self.client.post(
                    "/academic/directory-request",
                    data={
                        "request_type": DirectoryRequest.TYPE_INSTITUTION,
                        "institution_name": f"New Institution {index}",
                        "institution_type": "University",
                        "state": "Kaduna",
                    },
                    follow_redirects=False,
                )

                self.assertEqual(response.status_code, 302)
                self.assertEqual(
                    DirectoryRequest.query.filter_by(
                        user_id=user.id
                    ).count(),
                    2,
                )

    def test_phase4_structured_programme_blocks_missing_directory_requests(self):
        """Linked academic identity cannot use the missing-record workflow."""
        fixture = self._create_authorization_fixture()

        user = User(
            full_name="Linked Programme Student",
            email="linked-programme-request@example.com",
            password_hash="test-password-hash",
            account_status="Active",
        )

        db.session.add(user)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id

        profile_response = self.client.post(
            "/profile",
            data={
                "full_name": "Linked Programme Student",
                "matric_no": "PHASE4/DIR/001",
                "institution_id": str(fixture["institution_a"].id),
                "academic_unit_id": str(fixture["faculty_a"].id),
                "department_id": str(fixture["department_a"].id),
                "programme_id": str(fixture["programme_a"].id),
                "level": "400 level",
                "siwes_session": "2026",
                "preferred_state": "Kaduna",
                "preferred_city": "Zaria",
                "area_of_interest": "Software Development",
                "preferred_org_type": "Technology company",
                "skills": "Python, SQL",
                "bio": "Directory request eligibility test",
            },
            follow_redirects=False,
        )

        self.assertEqual(profile_response.status_code, 302)

        student = StudentProfile.query.filter_by(
            user_id=user.id
        ).first()

        self.assertIsNotNone(student)
        self.assertEqual(
            student.programme_id,
            fixture["programme_a"].id,
        )


        institution_response = self.client.post(
            "/academic/directory-request",
            data={
                "request_type": DirectoryRequest.TYPE_INSTITUTION,
                "institution_name": "Another University",
            },
            follow_redirects=False,
        )

        programme_response = self.client.post(
            "/academic/directory-request",
            data={
                "request_type": DirectoryRequest.TYPE_PROGRAMME,
                "institution_id": str(fixture["institution_a"].id),
                "programme_name": "B.Eng. Another Engineering",
            },
            follow_redirects=False,
        )

        self.assertEqual(institution_response.status_code, 302)
        self.assertEqual(programme_response.status_code, 302)
        self.assertEqual(
            DirectoryRequest.query.filter_by(user_id=user.id).count(),
            0,
        )

    def test_phase4_directory_request_requires_authentication(self):
        """Unauthenticated users cannot submit academic directory requests."""
        response = self.client.post(
            "/academic/directory-request",
            data={
                "request_type": DirectoryRequest.TYPE_INSTITUTION,
                "institution_name": "Unauthenticated Test Institution",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

        request_count = DirectoryRequest.query.filter_by(
            institution_name="Unauthenticated Test Institution",
        ).count()

        self.assertEqual(request_count, 0)

    def test_phase4_programme_request_rejects_unverified_institution(self):
        """Programme requests require an active verified institution."""
        user = User(
            full_name="Unverified Institution Request Student",
            email="unverified-directory-request@example.com",
            password_hash="test-password-hash",
            account_status="Active",
        )

        unverified_institution = Institution(
            name="Pending Review University",
            institution_type="University",
            city="Test City",
            state="Kaduna",
            directory_status="Pending Review",
        )

        db.session.add_all([
            user,
            unverified_institution,
        ])
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id

        response = self.client.post(
            "/academic/directory-request",
            data={
                "request_type": DirectoryRequest.TYPE_PROGRAMME,
                "institution_id": str(unverified_institution.id),
                "programme_name": "B.Eng. Test Engineering",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/profile"))

        request_count = DirectoryRequest.query.filter_by(
            user_id=user.id,
            request_type=DirectoryRequest.TYPE_PROGRAMME,
        ).count()

        self.assertEqual(request_count, 0)

    def test_phase4_structured_profile_saves_academic_hierarchy(self):
        """Structured selection saves programme FK and legacy compatibility fields."""
        fixture = self._create_authorization_fixture()

        student_user = User(
            full_name="Structured Student",
            email="structured.student@example.com",
            phone="08000000002",
            account_status="Active",
            email_verified=True,
        )
        student_user.set_password("student-password-123")

        db.session.add(student_user)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = student_user.id

        response = self.client.post(
            "/profile",
            data={
                "full_name": "Structured Student",
                "matric_no": "PHASE4/001",
                "institution_id": str(fixture["institution_a"].id),
                "academic_unit_id": str(fixture["faculty_a"].id),
                "department_id": str(fixture["department_a"].id),
                "programme_id": str(fixture["programme_a"].id),
                "level": "400 level",
                "siwes_session": "2026",
                "preferred_state": "Kaduna",
                "preferred_city": "Zaria",
                "area_of_interest": "Software Development",
                "preferred_org_type": "Technology company",
                "skills": "Python, SQL",
                "bio": "Phase 4 structured profile test",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        student = StudentProfile.query.filter_by(
            user_id=student_user.id
        ).first()

        self.assertIsNotNone(student)
        self.assertEqual(student.programme_id, fixture["programme_a"].id)
        self.assertEqual(student.level, "400 level")
        self.assertEqual(student.siwes_session, "2026")

        self.assertEqual(
            student.department,
            fixture["department_a"].name,
        )
        self.assertEqual(
            student.faculty,
            fixture["faculty_a"].name,
        )
        self.assertEqual(
            student.university,
            fixture["institution_a"].name,
        )

        self.assertEqual(
            student.academic_department_name,
            fixture["department_a"].name,
        )
        self.assertEqual(
            student.academic_unit_name,
            fixture["faculty_a"].name,
        )
        self.assertEqual(
            student.institution_name,
            fixture["institution_a"].name,
        )
        self.assertEqual(
            student.institution_display_name,
            "Institution A, Zaria",
        )

    def test_phase4_profile_directory_support_eligible_state(self):
        """Eligible profile shows the missing-directory request workspace."""
        user = User(
            full_name="Directory UI Eligible Student",
            email="directory-ui-eligible@example.com",
            password_hash="test-password-hash",
            account_status="Active",
        )

        db.session.add(user)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id

        response = self.client.get("/profile")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Request Missing Record", response.data)
        self.assertIn(b'id="directoryRequestLauncher"', response.data)
        self.assertIn(b'id="directoryRequestPanel"', response.data)
        self.assertNotIn(b"View Active Request", response.data)
        self.assertNotIn(b"Academic directory linked", response.data)

    def test_phase4_profile_directory_support_active_request_state(self):
        """Open request replaces the new-request workspace with tracking actions."""
        user = User(
            full_name="Directory UI Active Request Student",
            email="directory-ui-active@example.com",
            password_hash="test-password-hash",
            account_status="Active",
        )

        db.session.add(user)
        db.session.flush()

        directory_request = DirectoryRequest(
            user_id=user.id,
            request_type=DirectoryRequest.TYPE_INSTITUTION,
            institution_name="Missing UI Test University",
            institution_type="University",
            state="Kaduna",
            status=DirectoryRequest.STATUS_SUBMITTED,
        )

        db.session.add(directory_request)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id

        response = self.client.get("/profile")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Directory request in progress", response.data)
        self.assertIn(b"View Active Request", response.data)
        self.assertNotIn(b'id="directoryRequestLauncher"', response.data)
        self.assertNotIn(b'id="directoryRequestPanel"', response.data)

    def test_phase4_profile_directory_support_linked_state(self):
        """Linked academic identity does not render the missing-record workspace."""
        fixture = self._create_authorization_fixture()

        user = User(
            full_name="Directory UI Linked Student",
            email="directory-ui-linked@example.com",
            password_hash="test-password-hash",
            account_status="Active",
        )

        db.session.add(user)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id

        profile_response = self.client.post(
            "/profile",
            data={
                "full_name": "Directory UI Linked Student",
                "matric_no": "PHASE4/DIR/UI/001",
                "institution_id": str(fixture["institution_a"].id),
                "academic_unit_id": str(fixture["faculty_a"].id),
                "department_id": str(fixture["department_a"].id),
                "programme_id": str(fixture["programme_a"].id),
                "level": "400 level",
                "siwes_session": "2026",
                "preferred_state": "Kaduna",
                "preferred_city": "Zaria",
                "area_of_interest": "Software Development",
                "preferred_org_type": "Technology company",
                "skills": "Python, SQL",
                "bio": "Directory support linked-state test",
            },
            follow_redirects=False,
        )

        self.assertEqual(profile_response.status_code, 302)

        response = self.client.get("/profile")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Academic directory linked", response.data)
        self.assertIn(b"My Directory Requests", response.data)
        self.assertNotIn(b"Request Missing Record", response.data)
        self.assertNotIn(b'id="directoryRequestLauncher"', response.data)
        self.assertNotIn(b'id="directoryRequestPanel"', response.data)


    def test_phase4_profile_rejects_mismatched_academic_hierarchy(self):
        """A student cannot combine IDs belonging to different hierarchies."""
        fixture = self._create_authorization_fixture()

        student_user = User(
            full_name="Hierarchy Test Student",
            email="hierarchy.student@example.com",
            account_status="Active",
            email_verified=True,
        )
        student_user.set_password("student-password-123")

        db.session.add(student_user)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = student_user.id

        response = self.client.post(
            "/profile",
            data={
                "full_name": "Hierarchy Test Student",
                "matric_no": "PHASE4/INVALID/001",
                "institution_id": str(fixture["institution_a"].id),
                "academic_unit_id": str(fixture["faculty_a"].id),
                "department_id": str(fixture["department_a"].id),
                "programme_id": str(fixture["programme_b"].id),
                "level": "400 level",
                "siwes_session": "2026",
                "preferred_state": "Kaduna",
                "preferred_city": "Zaria",
                "area_of_interest": "Software Development",
                "preferred_org_type": "Technology company",
                "skills": "Python",
                "bio": "",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        student = StudentProfile.query.filter_by(
            user_id=student_user.id
        ).first()

        self.assertIsNone(student)

        self.assertIn(
            b"The selected academic programme does not match the "
            b"institution hierarchy.",
            response.data,
        )
    def test_home_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Departmental', response.data)
        self.assertIn(b'SIWES Assistant', response.data)

    def test_siwes_guide_page(self):
        response = self.client.get('/siwes-guide')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Guide Topic', response.data)

    def test_siwes_guide_detail_page(self):
        response = self.client.get('/siwes-guide/test-guide')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test content here', response.data)

    def test_placement_search_form(self):
        response = self.client.get('/placement')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Find SIWES Placement', response.data)

    def test_placement_search_results(self):
        response = self.client.get('/placement/results?state=Abuja&interest=Software')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'NITDA Test', response.data)
        self.assertIn(b'Organizations matching your search', response.data)

    def test_organization_details(self):
        response = self.client.get(f'/placement/{self.org.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'NITDA Test', response.data)
        self.assertIn(b'Personal application tracker', response.data)

    def test_student_profile_create_and_dashboard(self):
        user = User(
            full_name="Musa Danladi",
            email="musa.student@example.com",
            phone="08000000001",
            account_status="Active",
        )
        user.set_password("student-password-123")

        db.session.add(user)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id

        post_data = {
            "full_name": "Musa Danladi",
            "matric_no": "ENG/2022/9999",
            "department": "Computer Engineering",
            "faculty": "Faculty of Engineering",
            "university": "Ahmadu Bello University",
            "preferred_state": "Kaduna",
            "preferred_city": "Zaria",
            "area_of_interest": "Software Development",
            "preferred_org_type": "Technology company",
            "skills": "Python, SQL",
            "bio": "Test bio",
        }

        response = self.client.post(
            "/profile",
            data=post_data,
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Musa Danladi", response.data)
        self.assertIn(b"ENG/2022/9999", response.data)

        student = StudentProfile.query.filter_by(
            matric_no="ENG/2022/9999"
        ).first()

        self.assertIsNotNone(student)
        self.assertEqual(student.user_id, user.id)

        dashboard_response = self.client.get(
            "/dashboard",
            follow_redirects=True,
        )

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn(b"Musa Danladi", dashboard_response.data)
        self.assertIn(b"ENG/2022/9999", dashboard_response.data)


    def test_bookmark_and_track_application(self):
        user = User(
            full_name="Test Student",
            email="placement.student@example.com",
            phone="08000000002",
            account_status="Active",
        )
        user.set_password("student-password-123")

        db.session.add(user)
        db.session.flush()

        student = StudentProfile(
            user_id=user.id,
            full_name="Test Student",
            matric_no="ENG/TEST/1",
            department="Computer Engineering",
            faculty="Engineering",
            university="University of Lagos",
            preferred_state="Lagos",
            preferred_city="Yaba",
            area_of_interest="Software Development",
            preferred_org_type="Technology company",
            skills="Python",
        )

        db.session.add(student)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id

        save_resp = self.client.post(
            f"/placement/save/{self.org.id}",
            follow_redirects=True,
        )

        self.assertEqual(save_resp.status_code, 200)

        saved = SavedOrganization.query.filter_by(
            student_id=student.id,
            organization_id=self.org.id,
        ).first()

        self.assertIsNotNone(saved)

        track_resp = self.client.post(
            f"/placement/track/{self.org.id}",
            data={
                "status": "Application Submitted",
                "notes": "Submitted SIWES application.",
            },
            follow_redirects=True,
        )

        self.assertEqual(track_resp.status_code, 200)

        app = PlacementApplication.query.filter_by(
            student_id=student.id,
            organization_id=self.org.id,
        ).first()

        self.assertIsNotNone(app)
        self.assertEqual(
            app.status,
            "Application Submitted",
        )

    def test_legacy_student_id_cannot_switch_authenticated_profile(self):
        owner = User(
            full_name="Profile Owner",
            email="owner@example.com",
            account_status="Active",
        )
        owner.set_password("owner-password-123")

        attacker = User(
            full_name="Other Student",
            email="other@example.com",
            account_status="Active",
        )
        attacker.set_password("other-password-123")

        db.session.add_all([owner, attacker])
        db.session.flush()

        owner_profile = StudentProfile(
            user_id=owner.id,
            full_name="Profile Owner",
            matric_no="SEC/OWNER/001",
            department="Computer Engineering",
            faculty="Engineering",
            university="Ahmadu Bello University",
            preferred_state="Kaduna",
            preferred_city="Zaria",
            area_of_interest="Software Development",
            preferred_org_type="Technology company",
        )

        attacker_profile = StudentProfile(
            user_id=attacker.id,
            full_name="Other Student",
            matric_no="SEC/OTHER/002",
            department="Computer Engineering",
            faculty="Engineering",
            university="Ahmadu Bello University",
            preferred_state="Kaduna",
            preferred_city="Zaria",
            area_of_interest="Software Development",
            preferred_org_type="Technology company",
        )

        db.session.add_all([owner_profile, attacker_profile])
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = attacker.id

            # Simulate the old insecure technique:
            # manually place somebody else's profile ID in the session.
            sess["student_id"] = owner_profile.id

        response = self.client.post(
            f"/placement/save/{self.org.id}",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        owner_saved = SavedOrganization.query.filter_by(
            student_id=owner_profile.id,
            organization_id=self.org.id,
        ).first()

        attacker_saved = SavedOrganization.query.filter_by(
            student_id=attacker_profile.id,
            organization_id=self.org.id,
        ).first()

        self.assertIsNone(owner_saved)
        self.assertIsNotNone(attacker_saved)

    def test_inactive_user_stale_session_cannot_save_placement(self):
        """
        A stale authenticated session must not give an inactive user
        access to StudentProfile-based placement actions.
        """
        suspended_user = User(
            full_name="Suspended Student",
            email="suspended.student@example.com",
            account_status="Suspended",
        )
        suspended_user.set_password("suspended-password-123")

        db.session.add(suspended_user)
        db.session.flush()

        suspended_profile = StudentProfile(
            user_id=suspended_user.id,
            full_name="Suspended Student",
            matric_no="SEC/SUSPENDED/001",
            department="Computer Engineering",
            faculty="Engineering",
            university="Ahmadu Bello University",
            preferred_state="Kaduna",
            preferred_city="Zaria",
            area_of_interest="Software Development",
            preferred_org_type="Technology company",
        )

        db.session.add(suspended_profile)
        db.session.commit()

        # Simulate stale session data that remained after the account
        # was suspended.
        with self.client.session_transaction() as sess:
            sess["user_id"] = suspended_user.id
            sess["student_id"] = suspended_profile.id

        response = self.client.post(
            f"/placement/save/{self.org.id}",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)

        saved = SavedOrganization.query.filter_by(
            student_id=suspended_profile.id,
            organization_id=self.org.id,
        ).first()

        self.assertIsNone(saved)

    def test_logged_out_user_cannot_submit_organization(self):
        """
        Anonymous visitors must not be able to create organization records.
        """
        before_count = Organization.query.count()

        response = self.client.post(
            "/placement/submit-org",
            data={
                "name": "Anonymous Submission Ltd",
                "state": "Kaduna",
                "city": "Zaria",
                "industry": "Technology",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.location)

        after_count = Organization.query.count()

        self.assertEqual(before_count, after_count)

    def test_inactive_user_cannot_submit_organization(self):
        """
        A stale session belonging to an inactive account must not allow
        organization submissions.
        """
        suspended_user = User(
            full_name="Suspended Contributor",
            email="suspended.contributor@example.com",
            account_status="Suspended",
        )
        suspended_user.set_password("suspended-password-123")

        db.session.add(suspended_user)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = suspended_user.id

        before_count = Organization.query.count()

        response = self.client.post(
            "/placement/submit-org",
            data={
                "name": "Suspended Submission Ltd",
                "state": "Kaduna",
                "city": "Zaria",
                "industry": "Technology",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.location)

        after_count = Organization.query.count()

        self.assertEqual(before_count, after_count)

    def test_active_user_without_student_profile_can_submit_organization(self):
        """
        An authenticated active User may suggest an organization even when
        they do not have a StudentProfile.

        A community suggestion must enter the provenance workflow as pending
        review and must not imply an approved listing, current SIWES intake,
        or programme suitability.
        """
        contributor = User(
            full_name="Community Contributor",
            email="community.contributor@example.com",
            account_status="Active",
        )
        contributor.set_password("contributor-password-123")

        db.session.add(contributor)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = contributor.id

        response = self.client.post(
            "/placement/submit-org",
            data={
                "name": "Community SIWES Company",
                "description": "Test community contribution",
                "address": "1 Test Road",
                "state": "Kaduna",
                "city": "Zaria",
                "industry": "Technology",
                "relevance_areas": "Software Development",
                "website": "https://example.com",
                "contact_email": "contact@example.com",
                "contact_phone": "08000000000",
                "why_relevant": "Known to accept SIWES students.",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)

        organization = Organization.query.filter_by(
            name="Community SIWES Company",
        ).first()

        self.assertIsNotNone(organization)

        # Provenance/review contract.
        self.assertEqual(
            organization.source_type,
            "Community Contribution",
        )
        self.assertEqual(
            organization.source_name,
            "DSA Community Contribution",
        )
        self.assertEqual(
            organization.review_status,
            "Pending",
        )
        self.assertEqual(
            organization.listing_status,
            "Unknown",
        )
        self.assertEqual(
            organization.acceptance_status,
            "Unknown",
        )
        self.assertFalse(organization.is_active)

        # Contributor context is preserved as provenance evidence.
        self.assertEqual(
            organization.provenance_notes,
            "Known to accept SIWES students.",
        )

        # Legacy non-null fields remain populated only for compatibility
        # while older code is migrated away from them.
        self.assertEqual(
            organization.verification_status,
            "Pending Review",
        )
        self.assertEqual(
            organization.source,
            "Community Contribution",
        )

    def test_dashboard_does_not_fallback_to_another_students_profile(self):
        profile_owner = User(
            full_name="Existing Student",
            email="existing.student@example.com",
            account_status="Active",
        )
        profile_owner.set_password("existing-password-123")

        account_without_profile = User(
            full_name="New Account",
            email="new.account@example.com",
            account_status="Active",
        )
        account_without_profile.set_password("new-password-123")

        db.session.add_all(
            [
                profile_owner,
                account_without_profile,
            ]
        )
        db.session.flush()

        existing_profile = StudentProfile(
            user_id=profile_owner.id,
            full_name="Existing Student",
            matric_no="SEC/EXISTING/001",
            department="Computer Engineering",
            faculty="Engineering",
            university="Ahmadu Bello University",
            preferred_state="Kaduna",
            preferred_city="Zaria",
            area_of_interest="Software Development",
            preferred_org_type="Technology company",
        )

        db.session.add(existing_profile)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = account_without_profile.id

        response = self.client.get(
            "/dashboard",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        # User without a profile must be sent to profile creation,
        # not shown another student's dashboard.
        self.assertNotIn(
            b"SEC/EXISTING/001",
            response.data,
        )

        self.assertIn(
            b"Please complete your student profile",
            response.data,
        )


    def test_user_cannot_claim_another_profiles_matric_number(self):
        original_user = User(
            full_name="Original Student",
            email="original.student@example.com",
            account_status="Active",
        )
        original_user.set_password("original-password-123")

        second_user = User(
            full_name="Second Student",
            email="second.student@example.com",
            account_status="Active",
        )
        second_user.set_password("second-password-123")

        db.session.add_all(
            [
                original_user,
                second_user,
            ]
        )
        db.session.flush()

        original_profile = StudentProfile(
            user_id=original_user.id,
            full_name="Original Student",
            matric_no="SEC/CLAIM/001",
            department="Computer Engineering",
            faculty="Engineering",
            university="Ahmadu Bello University",
            preferred_state="Kaduna",
            preferred_city="Zaria",
            area_of_interest="Software Development",
            preferred_org_type="Technology company",
        )

        db.session.add(original_profile)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = second_user.id

        response = self.client.post(
            "/profile",
            data={
                "full_name": "Second Student",
                "matric_no": "SEC/CLAIM/001",
                "department": "Computer Engineering",
                "faculty": "Engineering",
                "university": "Ahmadu Bello University",
                "preferred_state": "Kaduna",
                "preferred_city": "Zaria",
                "area_of_interest": "Software Development",
                "preferred_org_type": "Technology company",
                "skills": "",
                "bio": "",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        second_profile = StudentProfile.query.filter_by(
            user_id=second_user.id
        ).first()

        self.assertIsNone(second_profile)

        self.assertIn(
            b"already registered to another student profile",
            response.data,
        )

        original_profile = db.session.get(
            StudentProfile,
            original_profile.id,
        )

        self.assertEqual(
            original_profile.user_id,
            original_user.id,
        )

    def test_admin_authentication_and_dashboard(self):
        # 1. Unauthenticated visitors must be sent to normal account login.
        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login', response.location)

        # 2. Legacy session['is_admin'] alone must grant nothing.
        with self.client.session_transaction() as sess:
            sess['is_admin'] = True

        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login', response.location)

        # Clear the legacy session before testing a real account.
        with self.client.session_transaction() as sess:
            sess.clear()

        # 3. An ordinary authenticated user must not access platform admin.
        ordinary_user = User(
            full_name='Ordinary User',
            email='ordinary@example.com',
            account_status='Active',
        )
        ordinary_user.set_password('ordinary-password')

        db.session.add(ordinary_user)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = ordinary_user.id

        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 403)
        self.assertIn(
            b'Forbidden',
            response.data,
        )

        # 4. Create the explicit platform administration permission.
        admin_permission = Permission(
            name='Access Platform Administration Panel',
            slug='access_platform_admin_panel',
        )

        platform_role = Role(
            name='Platform Administrator',
            slug='platform_administrator',
            description='Global DSA platform administration role.',
            is_active=True,
        )

        platform_role.permissions.append(admin_permission)

        platform_admin = User(
            full_name='Platform Admin',
            email='platform-admin@example.com',
            account_status='Active',
        )
        platform_admin.set_password('platform-admin-password')

        db.session.add_all([
            admin_permission,
            platform_role,
            platform_admin,
        ])
        db.session.flush()

        assignment = UserRoleAssignment(
            user_id=platform_admin.id,
            role_id=platform_role.id,
            institution_id=None,
            department_id=None,
            programme_id=None,
            status='Approved',
            approved_at=datetime.utcnow(),
        )

        db.session.add(assignment)
        db.session.commit()

        # Replace the ordinary user's authenticated session.
        with self.client.session_transaction() as sess:
            sess.clear()
            sess['user_id'] = platform_admin.id

        # 5. Approved global Platform Administrator must be allowed.
        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'Platform Administration',
            response.data,
        )


    def _create_platform_admin_security_fixture(self):
        """Create reusable accounts and roles for Platform Admin security tests."""
        admin_permission = Permission(
            name="Access Platform Administration Panel",
            slug="access_platform_admin_panel",
        )

        platform_role = Role(
            name="Platform Administrator",
            slug="platform_administrator",
            description="Global DSA platform administration role.",
            is_active=True,
        )
        platform_role.permissions.append(admin_permission)

        secondary_role = Role(
            name="Test Privileged Role",
            slug="test_privileged_role",
            description="Secondary privileged role used by security tests.",
            is_active=True,
        )

        platform_admin = User(
            full_name="Security Test Platform Admin",
            email="security-platform-admin@example.com",
            account_status="Active",
        )
        platform_admin.set_password("platform-admin-password")

        managed_user = User(
            full_name="Managed Test User",
            email="managed-user@example.com",
            account_status="Active",
        )
        managed_user.set_password("managed-user-password")

        db.session.add_all([
            admin_permission,
            platform_role,
            secondary_role,
            platform_admin,
            managed_user,
        ])
        db.session.flush()

        platform_assignment = UserRoleAssignment(
            user_id=platform_admin.id,
            role_id=platform_role.id,
            institution_id=None,
            department_id=None,
            programme_id=None,
            status="Approved",
            approved_at=datetime.utcnow(),
        )

        admin_secondary_assignment = UserRoleAssignment(
            user_id=platform_admin.id,
            role_id=secondary_role.id,
            institution_id=None,
            department_id=None,
            programme_id=None,
            status="Approved",
            approved_at=datetime.utcnow(),
        )

        managed_user_assignment = UserRoleAssignment(
            user_id=managed_user.id,
            role_id=secondary_role.id,
            institution_id=None,
            department_id=None,
            programme_id=None,
            status="Approved",
            approved_at=datetime.utcnow(),
        )

        db.session.add_all([
            platform_assignment,
            admin_secondary_assignment,
            managed_user_assignment,
        ])
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess.clear()
            sess["user_id"] = platform_admin.id

        return {
            "platform_admin": platform_admin,
            "managed_user": managed_user,
            "platform_assignment": platform_assignment,
            "admin_secondary_assignment": admin_secondary_assignment,
            "managed_user_assignment": managed_user_assignment,
        }

    def _create_directory_request_queue_fixture(self):
        """Create directory requests used by Platform Admin queue tests."""
        data = self._create_platform_admin_security_fixture()

        submitted_institution = DirectoryRequest(
            user_id=data["managed_user"].id,
            request_type=DirectoryRequest.TYPE_INSTITUTION,
            institution_name="Northern Test University",
            state="Kaduna",
            city="Zaria",
            status=DirectoryRequest.STATUS_SUBMITTED,
        )

        submitted_programme = DirectoryRequest(
            user_id=data["managed_user"].id,
            request_type=DirectoryRequest.TYPE_PROGRAMME,
            institution_name="Existing Test University",
            academic_unit_name="Faculty of Engineering",
            department_name="Department of Computer Engineering",
            programme_name="Computer Engineering",
            award="B.Eng.",
            status=DirectoryRequest.STATUS_SUBMITTED,
        )

        approved_request = DirectoryRequest(
            user_id=data["managed_user"].id,
            request_type=DirectoryRequest.TYPE_INSTITUTION,
            institution_name="Approved Test Polytechnic",
            state="Kano",
            city="Kano",
            status=DirectoryRequest.STATUS_APPROVED,
            reviewed_by_user_id=data["platform_admin"].id,
            reviewer_notes="Test approval only.",
            decided_at=datetime.utcnow(),
        )

        db.session.add_all([
            submitted_institution,
            submitted_programme,
            approved_request,
        ])
        db.session.commit()

        data.update({
            "submitted_institution": submitted_institution,
            "submitted_programme": submitted_programme,
            "approved_request": approved_request,
        })

        return data

    def test_platform_admin_dashboard_attention_counts_are_scoped_and_derived(self):
        data = self._create_directory_request_queue_fixture()
        platform_admin = data["platform_admin"]
        requester = data["managed_user"]

        second_admin = User(
            full_name="Second Platform Admin",
            email="second-platform-admin@example.com",
            account_status="Active",
        )
        second_admin.set_password("second-platform-admin-password")
        db.session.add(second_admin)
        db.session.flush()

        platform_role = Role.query.filter_by(
            slug="platform_administrator"
        ).one()

        db.session.add(
            UserRoleAssignment(
                user_id=second_admin.id,
                role_id=platform_role.id,
                institution_id=None,
                department_id=None,
                programme_id=None,
                status="Approved",
                approved_at=datetime.utcnow(),
            )
        )

        active_review = DirectoryRequest(
            user_id=requester.id,
            request_type=DirectoryRequest.TYPE_INSTITUTION,
            institution_name="Active Review University",
            state="Kaduna",
            city="Zaria",
            status=DirectoryRequest.STATUS_UNDER_REVIEW,
            reviewed_by_user_id=platform_admin.id,
            review_started_at=datetime.utcnow(),
        )

        awaiting_requester = DirectoryRequest(
            user_id=requester.id,
            request_type=DirectoryRequest.TYPE_INSTITUTION,
            institution_name="Awaiting Requester University",
            state="Kaduna",
            city="Zaria",
            status=DirectoryRequest.STATUS_MORE_INFO_REQUIRED,
            reviewed_by_user_id=platform_admin.id,
            review_started_at=datetime.utcnow(),
        )

        response_received = DirectoryRequest(
            user_id=requester.id,
            request_type=DirectoryRequest.TYPE_INSTITUTION,
            institution_name="Response Received University",
            state="Kaduna",
            city="Zaria",
            status=DirectoryRequest.STATUS_UNDER_REVIEW,
            reviewed_by_user_id=platform_admin.id,
            review_started_at=datetime.utcnow(),
        )

        reviewer_latest = DirectoryRequest(
            user_id=requester.id,
            request_type=DirectoryRequest.TYPE_INSTITUTION,
            institution_name="Reviewer Latest University",
            state="Kaduna",
            city="Zaria",
            status=DirectoryRequest.STATUS_UNDER_REVIEW,
            reviewed_by_user_id=platform_admin.id,
            review_started_at=datetime.utcnow(),
        )

        other_admin_active = DirectoryRequest(
            user_id=requester.id,
            request_type=DirectoryRequest.TYPE_INSTITUTION,
            institution_name="Other Admin Active University",
            state="Kaduna",
            city="Zaria",
            status=DirectoryRequest.STATUS_UNDER_REVIEW,
            reviewed_by_user_id=second_admin.id,
            review_started_at=datetime.utcnow(),
        )

        other_admin_waiting = DirectoryRequest(
            user_id=requester.id,
            request_type=DirectoryRequest.TYPE_INSTITUTION,
            institution_name="Other Admin Waiting University",
            state="Kaduna",
            city="Zaria",
            status=DirectoryRequest.STATUS_MORE_INFO_REQUIRED,
            reviewed_by_user_id=second_admin.id,
            review_started_at=datetime.utcnow(),
        )

        db.session.add_all([
            active_review,
            awaiting_requester,
            response_received,
            reviewer_latest,
            other_admin_active,
            other_admin_waiting,
        ])
        db.session.flush()

        db.session.add_all([
            DirectoryRequestMessage(
                directory_request_id=response_received.id,
                author_user_id=platform_admin.id,
                author_type=DirectoryRequestMessage.AUTHOR_REVIEWER,
                message="Please provide more information.",
            ),
            DirectoryRequestMessage(
                directory_request_id=response_received.id,
                author_user_id=requester.id,
                author_type=DirectoryRequestMessage.AUTHOR_REQUESTER,
                message="The requested information is now available.",
            ),
            DirectoryRequestMessage(
                directory_request_id=reviewer_latest.id,
                author_user_id=requester.id,
                author_type=DirectoryRequestMessage.AUTHOR_REQUESTER,
                message="Here is my response.",
            ),
            DirectoryRequestMessage(
                directory_request_id=reviewer_latest.id,
                author_user_id=platform_admin.id,
                author_type=DirectoryRequestMessage.AUTHOR_REVIEWER,
                message="One additional clarification is required.",
            ),
        ])
        db.session.commit()

        recorded = {}

        def capture_template(sender, template, context, **extra):
            recorded["template"] = template.name
            recorded["context"] = context

        from flask import template_rendered

        template_rendered.connect(
            capture_template,
            self.app,
            weak=False,
        )

        try:
            response = self.client.get("/admin/")
        finally:
            template_rendered.disconnect(
                capture_template,
                self.app,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(recorded["template"], "admin/dashboard.html")

        context = recorded["context"]

        self.assertEqual(context["submitted_directory_requests"], 2)
        self.assertEqual(context["my_active_directory_reviews"], 3)
        self.assertEqual(context["awaiting_requester_directory_requests"], 1)
        self.assertEqual(context["response_received_directory_requests"], 1)

        expected_attention = (
            context["pending_reviews"]
            + 2
            + 3
            + 1
        )
        self.assertEqual(
            context["total_attention_items"],
            expected_attention,
        )

        # The response-received case is already one of the three active
        # reviews and therefore must not be counted a second time.
        self.assertNotEqual(
            context["total_attention_items"],
            expected_attention + context["response_received_directory_requests"],
        )

    def test_platform_admin_dashboard_exposes_submitted_directory_requests(self):
        self._create_directory_request_queue_fixture()

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Academic Directory Requests", response.data)
        self.assertIn(b"2", response.data)
        self.assertIn(b"submitted", response.data)
        self.assertIn(b"/admin/directory-requests", response.data)

    def test_platform_admin_can_open_directory_request_queue(self):
        self._create_directory_request_queue_fixture()

        response = self.client.get("/admin/directory-requests")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Northern Test University", response.data)
        self.assertIn(b"Computer Engineering", response.data)

    def test_directory_request_queue_defaults_to_submitted_requests(self):
        self._create_directory_request_queue_fixture()

        response = self.client.get("/admin/directory-requests")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Northern Test University", response.data)
        self.assertIn(b"Computer Engineering", response.data)
        self.assertNotIn(b"Approved Test Polytechnic", response.data)

    def test_directory_request_queue_can_filter_by_status(self):
        self._create_directory_request_queue_fixture()

        response = self.client.get(
            "/admin/directory-requests?status=Approved"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Approved Test Polytechnic", response.data)
        self.assertNotIn(b"Northern Test University", response.data)

    def test_directory_request_queue_can_filter_by_request_type(self):
        self._create_directory_request_queue_fixture()

        response = self.client.get(
            "/admin/directory-requests?status=all&type=Programme"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Computer Engineering", response.data)
        self.assertNotIn(b"Northern Test University", response.data)
        self.assertNotIn(b"Approved Test Polytechnic", response.data)

    def test_directory_request_queue_can_search_academic_fields(self):
        self._create_directory_request_queue_fixture()

        response = self.client.get(
            "/admin/directory-requests?status=all&q=Computer"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Computer Engineering", response.data)
        self.assertNotIn(b"Northern Test University", response.data)
        self.assertNotIn(b"Approved Test Polytechnic", response.data)

    def test_directory_request_queue_invalid_filters_fall_back_safely(self):
        self._create_directory_request_queue_fixture()

        response = self.client.get(
            "/admin/directory-requests?status=InvalidStatus&type=InvalidType"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Northern Test University", response.data)
        self.assertIn(b"Computer Engineering", response.data)
        self.assertNotIn(b"Approved Test Polytechnic", response.data)
    def test_platform_admin_can_open_directory_request_detail(self):
        data = self._create_directory_request_queue_fixture()
        request_id = data["submitted_institution"].id

        response = self.client.get(
            f"/admin/directory-requests/{request_id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Northern Test University", response.data)

    def test_submitted_directory_request_detail_shows_mark_under_review_action(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]

        response = self.client.get(
            f"/admin/directory-requests/{directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Mark Under Review", response.data)
        self.assertIn(
            f"/admin/directory-requests/{directory_request.id}/under-review".encode(),
            response.data,
        )
        self.assertIn(b'name="csrf_token"', response.data)

    def test_final_directory_request_detail_hides_mark_under_review_action(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["approved_request"]

        response = self.client.get(
            f"/admin/directory-requests/{directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Mark Under Review", response.data)
        self.assertNotIn(
            f"/admin/directory-requests/{directory_request.id}/under-review".encode(),
            response.data,
        )

    def test_under_review_directory_request_detail_shows_more_information_action(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        directory_request.reviewed_by_user_id = data["platform_admin"].id
        db.session.commit()

        response = self.client.get(
            f"/admin/directory-requests/{directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Request More Information", response.data)
        self.assertIn(
            f"/admin/directory-requests/{directory_request.id}/more-information".encode(),
            response.data,
        )
        self.assertIn(b'name="reviewer_notes"', response.data)
        self.assertIn(b'name="csrf_token"', response.data)
        self.assertNotIn(b"Mark Under Review", response.data)

    def test_submitted_directory_request_detail_hides_more_information_action(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]

        response = self.client.get(
            f"/admin/directory-requests/{directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Request More Information", response.data)
        self.assertNotIn(
            f"/admin/directory-requests/{directory_request.id}/more-information".encode(),
            response.data,
        )

    def test_final_directory_request_detail_hides_more_information_action(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["approved_request"]

        response = self.client.get(
            f"/admin/directory-requests/{directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Request More Information", response.data)
        self.assertNotIn(
            f"/admin/directory-requests/{directory_request.id}/more-information".encode(),
            response.data,
        )
        self.assertNotIn(b"Mark Under Review", response.data)

    def test_under_review_directory_request_detail_shows_approve_action(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        directory_request.reviewed_by_user_id = data["platform_admin"].id
        db.session.commit()

        response = self.client.get(
            f"/admin/directory-requests/{directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Approve Request", response.data)
        self.assertIn(
            f"/admin/directory-requests/{directory_request.id}/approve".encode(),
            response.data,
        )
        self.assertIn(b'name="csrf_token"', response.data)

    def test_submitted_directory_request_detail_hides_approve_action(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]

        response = self.client.get(
            f"/admin/directory-requests/{directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Approve Request", response.data)
        self.assertNotIn(
            f"/admin/directory-requests/{directory_request.id}/approve".encode(),
            response.data,
        )

    def test_final_directory_request_detail_hides_approve_action(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["approved_request"]

        response = self.client.get(
            f"/admin/directory-requests/{directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Approve Request", response.data)
        self.assertNotIn(
            f"/admin/directory-requests/{directory_request.id}/approve".encode(),
            response.data,
        )
    def test_under_review_directory_request_detail_shows_reject_action(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        directory_request.reviewed_by_user_id = data["platform_admin"].id
        db.session.commit()

        response = self.client.get(
            f"/admin/directory-requests/{directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Reject Request", response.data)
        self.assertIn(
            f"/admin/directory-requests/{directory_request.id}/reject".encode(),
            response.data,
        )
        self.assertIn(b'name="csrf_token"', response.data)
        self.assertIn(b'id="rejection_reviewer_notes"', response.data)
        self.assertIn(b'name="reviewer_notes"', response.data)
        self.assertIn(b"required", response.data)

    def test_submitted_directory_request_detail_hides_reject_action(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]

        response = self.client.get(
            f"/admin/directory-requests/{directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Reject Request", response.data)
        self.assertNotIn(
            f"/admin/directory-requests/{directory_request.id}/reject".encode(),
            response.data,
        )

    def test_final_directory_request_detail_hides_reject_action(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["approved_request"]

        response = self.client.get(
            f"/admin/directory-requests/{directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Reject Request", response.data)
        self.assertNotIn(
            f"/admin/directory-requests/{directory_request.id}/reject".encode(),
            response.data,
        )
    def test_directory_request_detail_shows_review_conversation(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        reviewer = data["platform_admin"]
        requester = directory_request.user

        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        directory_request.reviewed_by_user_id = reviewer.id

        reviewer_message = DirectoryRequestMessage(
            directory_request_id=directory_request.id,
            author_user_id=reviewer.id,
            author_type=DirectoryRequestMessage.AUTHOR_REVIEWER,
            message="Please provide the official programme reference.",
        )
        requester_message = DirectoryRequestMessage(
            directory_request_id=directory_request.id,
            author_user_id=requester.id,
            author_type=DirectoryRequestMessage.AUTHOR_REQUESTER,
            message="The requested programme reference is now provided.",
            evidence_reference="https://example.edu/programme-reference",
        )

        db.session.add_all([reviewer_message, requester_message])
        db.session.commit()

        response = self.client.get(
            f"/admin/directory-requests/{directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Review Conversation", response.data)
        self.assertIn(
            b"Please provide the official programme reference.",
            response.data,
        )
        self.assertIn(
            b"The requested programme reference is now provided.",
            response.data,
        )
        self.assertIn(
            b"https://example.edu/programme-reference",
            response.data,
        )
        self.assertIn(reviewer.full_name.encode(), response.data)
        self.assertIn(requester.full_name.encode(), response.data)

    def test_directory_request_detail_shows_clarifications_chronologically(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        reviewer = data["platform_admin"]
        requester = directory_request.user

        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        directory_request.reviewed_by_user_id = reviewer.id

        first_message = DirectoryRequestMessage(
            directory_request_id=directory_request.id,
            author_user_id=reviewer.id,
            author_type=DirectoryRequestMessage.AUTHOR_REVIEWER,
            message="FIRST REVIEW MESSAGE",
            created_at=datetime(2026, 9, 29, 10, 0, 0),
        )
        second_message = DirectoryRequestMessage(
            directory_request_id=directory_request.id,
            author_user_id=requester.id,
            author_type=DirectoryRequestMessage.AUTHOR_REQUESTER,
            message="SECOND REQUESTER MESSAGE",
            created_at=datetime(2026, 9, 29, 11, 0, 0),
        )

        db.session.add_all([second_message, first_message])
        db.session.commit()

        response = self.client.get(
            f"/admin/directory-requests/{directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)

        html = response.data.decode()

        self.assertIn("FIRST REVIEW MESSAGE", html)
        self.assertIn("SECOND REQUESTER MESSAGE", html)
        self.assertLess(
            html.index("FIRST REVIEW MESSAGE"),
            html.index("SECOND REQUESTER MESSAGE"),
        )

    def test_directory_request_detail_derives_response_received_state(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        reviewer = data["platform_admin"]
        requester = directory_request.user

        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        directory_request.reviewed_by_user_id = reviewer.id

        db.session.add_all(
            [
                DirectoryRequestMessage(
                    directory_request_id=directory_request.id,
                    author_user_id=reviewer.id,
                    author_type=DirectoryRequestMessage.AUTHOR_REVIEWER,
                    message="Please clarify the submitted information.",
                    created_at=datetime(2026, 9, 29, 10, 0, 0),
                ),
                DirectoryRequestMessage(
                    directory_request_id=directory_request.id,
                    author_user_id=requester.id,
                    author_type=DirectoryRequestMessage.AUTHOR_REQUESTER,
                    message="Here is the requested clarification.",
                    created_at=datetime(2026, 9, 29, 11, 0, 0),
                ),
            ]
        )
        db.session.commit()

        response = self.client.get(
            f"/admin/directory-requests/{directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Response received", response.data)

    def test_directory_request_detail_does_not_false_flag_response_received(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        reviewer = data["platform_admin"]

        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        directory_request.reviewed_by_user_id = reviewer.id

        db.session.add(
            DirectoryRequestMessage(
                directory_request_id=directory_request.id,
                author_user_id=reviewer.id,
                author_type=DirectoryRequestMessage.AUTHOR_REVIEWER,
                message="Please provide additional supporting information.",
            )
        )
        db.session.commit()

        response = self.client.get(
            f"/admin/directory-requests/{directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Response received", response.data)
    def test_other_platform_admin_can_view_claimed_request_without_review_actions(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        directory_request.reviewed_by_user_id = data["platform_admin"].id

        platform_role = Role.query.filter_by(slug="platform_administrator").one()

        second_admin = User(
            full_name="Second Platform Admin",
            email="second-platform-admin@example.com",
            account_status="Active",
        )
        second_admin.set_password("second-platform-admin-password")
        db.session.add(second_admin)
        db.session.flush()

        second_assignment = UserRoleAssignment(
            user_id=second_admin.id,
            role_id=platform_role.id,
            institution_id=None,
            department_id=None,
            programme_id=None,
            status="Approved",
            approved_at=datetime.utcnow(),
        )
        db.session.add(second_assignment)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess.clear()
            sess["user_id"] = second_admin.id

        response = self.client.get(
            f"/admin/directory-requests/{directory_request.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Northern Test University", response.data)
        self.assertIn(
            b"currently being reviewed by another Platform Admin",
            response.data,
        )
        self.assertNotIn(b"Request More Information", response.data)
        self.assertNotIn(b"Approve Request", response.data)
        self.assertNotIn(b"Reject Request", response.data)
        self.assertNotIn(
            f"/admin/directory-requests/{directory_request.id}/more-information".encode(),
            response.data,
        )
        self.assertNotIn(
            f"/admin/directory-requests/{directory_request.id}/approve".encode(),
            response.data,
        )
        self.assertNotIn(
            f"/admin/directory-requests/{directory_request.id}/reject".encode(),
            response.data,
        )

    def test_unauthorized_user_cannot_open_directory_request_detail(self):
        data = self._create_directory_request_queue_fixture()
        request_id = data["submitted_institution"].id

        with self.client.session_transaction() as sess:
            sess.clear()
            sess["user_id"] = data["managed_user"].id

        response = self.client.get(
            f"/admin/directory-requests/{request_id}"
        )

        self.assertEqual(response.status_code, 403)

    def test_platform_admin_can_mark_directory_request_under_review(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]

        response = self.client.post(
            f"/admin/directory-requests/{directory_request.id}/under-review",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)

        db.session.refresh(directory_request)

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_UNDER_REVIEW,
        )
        self.assertEqual(
            directory_request.reviewed_by_user_id,
            data["platform_admin"].id,
        )
        self.assertIsNotNone(directory_request.review_started_at)

    def test_unauthorized_user_cannot_mark_directory_request_under_review(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]

        with self.client.session_transaction() as sess:
            sess.clear()
            sess["user_id"] = data["managed_user"].id

        response = self.client.post(
            f"/admin/directory-requests/{directory_request.id}/under-review"
        )

        self.assertEqual(response.status_code, 403)

        db.session.refresh(directory_request)

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_SUBMITTED,
        )

    def test_mark_directory_request_under_review_returns_404_for_missing_request(self):
        self._create_directory_request_queue_fixture()

        response = self.client.post(
            "/admin/directory-requests/999999/under-review"
        )

        self.assertEqual(response.status_code, 404)

    def test_platform_admin_can_request_more_directory_information(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        directory_request.reviewed_by_user_id = data["platform_admin"].id
        db.session.commit()

        response = self.client.post(
            f"/admin/directory-requests/{directory_request.id}/more-information",
            data={
                "reviewer_notes": "Please provide an official university webpage."
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)

        db.session.refresh(directory_request)

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_MORE_INFO_REQUIRED,
        )
        self.assertEqual(
            directory_request.reviewed_by_user_id,
            data["platform_admin"].id,
        )
        self.assertEqual(
            directory_request.reviewer_notes,
            "Please provide an official university webpage.",
        )

    def test_request_more_directory_information_requires_notes(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        db.session.commit()

        response = self.client.post(
            f"/admin/directory-requests/{directory_request.id}/more-information",
            data={"reviewer_notes": "   "},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        db.session.refresh(directory_request)

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_UNDER_REVIEW,
        )

    def test_unauthorized_user_cannot_request_more_directory_information(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess.clear()
            sess["user_id"] = data["managed_user"].id

        response = self.client.post(
            f"/admin/directory-requests/{directory_request.id}/more-information",
            data={"reviewer_notes": "Please provide more information."},
        )

        self.assertEqual(response.status_code, 403)

        db.session.refresh(directory_request)

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_UNDER_REVIEW,
        )

    def test_request_more_directory_information_returns_404_for_missing_request(self):
        self._create_directory_request_queue_fixture()

        response = self.client.post(
            "/admin/directory-requests/999999/more-information",
            data={"reviewer_notes": "Please provide more information."},
        )

        self.assertEqual(response.status_code, 404)

    def test_platform_admin_can_approve_directory_request(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        directory_request.reviewed_by_user_id = data["platform_admin"].id
        db.session.commit()

        response = self.client.post(
            f"/admin/directory-requests/{directory_request.id}/approve",
            data={"reviewer_notes": "Official evidence reviewed."},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)

        db.session.refresh(directory_request)

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_APPROVED,
        )
        self.assertEqual(
            directory_request.reviewed_by_user_id,
            data["platform_admin"].id,
        )
        self.assertEqual(
            directory_request.reviewer_notes,
            "Official evidence reviewed.",
        )
        self.assertIsNotNone(directory_request.decided_at)

    def test_unauthorized_user_cannot_approve_directory_request(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess.clear()
            sess["user_id"] = data["managed_user"].id

        response = self.client.post(
            f"/admin/directory-requests/{directory_request.id}/approve",
            data={"reviewer_notes": "Approved."},
        )

        self.assertEqual(response.status_code, 403)

        db.session.refresh(directory_request)

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_UNDER_REVIEW,
        )

    def test_approve_directory_request_returns_404_for_missing_request(self):
        self._create_directory_request_queue_fixture()

        response = self.client.post(
            "/admin/directory-requests/999999/approve",
            data={"reviewer_notes": "Approved."},
        )

        self.assertEqual(response.status_code, 404)

    def test_final_directory_request_cannot_be_approved_via_admin(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["approved_request"]

        response = self.client.post(
            f"/admin/directory-requests/{directory_request.id}/approve",
            data={"reviewer_notes": "Approved again."},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        db.session.refresh(directory_request)

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_APPROVED,
        )
        self.assertIn(
            b"cannot be approved",
            response.data,
        )
    def test_platform_admin_can_reject_directory_request(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        directory_request.reviewed_by_user_id = data["platform_admin"].id
        db.session.commit()

        response = self.client.post(
            f"/admin/directory-requests/{directory_request.id}/reject",
            data={
                "reviewer_notes": "Submitted evidence could not be verified."
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)

        db.session.refresh(directory_request)

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_REJECTED,
        )
        self.assertEqual(
            directory_request.reviewed_by_user_id,
            data["platform_admin"].id,
        )
        self.assertEqual(
            directory_request.reviewer_notes,
            "Submitted evidence could not be verified.",
        )
        self.assertIsNotNone(directory_request.decided_at)

    def test_reject_directory_request_requires_notes(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        directory_request.reviewed_by_user_id = data["platform_admin"].id
        db.session.commit()

        response = self.client.post(
            f"/admin/directory-requests/{directory_request.id}/reject",
            data={"reviewer_notes": "   "},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        db.session.refresh(directory_request)

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_UNDER_REVIEW,
        )
        self.assertIn(
            b"Reviewer notes are required",
            response.data,
        )

    def test_unauthorized_user_cannot_reject_directory_request(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess.clear()
            sess["user_id"] = data["managed_user"].id

        response = self.client.post(
            f"/admin/directory-requests/{directory_request.id}/reject",
            data={"reviewer_notes": "Rejected."},
        )

        self.assertEqual(response.status_code, 403)

        db.session.refresh(directory_request)

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_UNDER_REVIEW,
        )

    def test_reject_directory_request_returns_404_for_missing_request(self):
        self._create_directory_request_queue_fixture()

        response = self.client.post(
            "/admin/directory-requests/999999/reject",
            data={"reviewer_notes": "Rejected."},
        )

        self.assertEqual(response.status_code, 404)

    def test_final_directory_request_cannot_be_rejected_via_admin(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["approved_request"]

        response = self.client.post(
            f"/admin/directory-requests/{directory_request.id}/reject",
            data={"reviewer_notes": "Attempted rejection."},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        db.session.refresh(directory_request)

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_APPROVED,
        )
        self.assertIn(
            b"cannot be rejected",
            response.data,
        )
    def test_final_directory_request_cannot_be_marked_under_review_via_admin(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["approved_request"]

        response = self.client.post(
            f"/admin/directory-requests/{directory_request.id}/under-review",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        db.session.refresh(directory_request)

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_APPROVED,
        )
        self.assertIn(
            b"cannot be marked under review",
            response.data,
        )
    def test_directory_request_detail_returns_404_for_missing_request(self):
        self._create_directory_request_queue_fixture()

        response = self.client.get(
            "/admin/directory-requests/999999"
        )

        self.assertEqual(response.status_code, 404)
    def test_admin_can_suspend_and_reactivate_another_account(self):
        data = self._create_platform_admin_security_fixture()
        managed_user_id = data["managed_user"].id

        response = self.client.post(
            f"/admin/users/{managed_user_id}/suspend",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        managed_user = db.session.get(User, managed_user_id)
        self.assertEqual(managed_user.account_status, "Suspended")
        self.assertIn(
            b'Suspended account for &#34;Managed Test User&#34;.',
            response.data,
        )

        response = self.client.post(
            f"/admin/users/{managed_user_id}/reactivate",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        managed_user = db.session.get(User, managed_user_id)
        self.assertEqual(managed_user.account_status, "Active")
        self.assertIn(
            b'Reactivated account for &#34;Managed Test User&#34;.',
            response.data,
        )

    def test_admin_cannot_suspend_own_platform_admin_account(self):
        data = self._create_platform_admin_security_fixture()
        platform_admin_id = data["platform_admin"].id

        response = self.client.post(
            f"/admin/users/{platform_admin_id}/suspend",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        platform_admin = db.session.get(User, platform_admin_id)
        self.assertEqual(platform_admin.account_status, "Active")
        self.assertIn(
            b"You cannot suspend the account you are currently using",
            response.data,
        )

    def test_admin_can_revoke_another_users_privileged_assignment(self):
        data = self._create_platform_admin_security_fixture()
        assignment_id = data["managed_user_assignment"].id

        response = self.client.post(
            f"/admin/role-assignments/{assignment_id}/revoke",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        assignment = db.session.get(
            UserRoleAssignment,
            assignment_id,
        )
        self.assertEqual(assignment.status, "Revoked")
        self.assertIn(
            b'Revoked &#34;Test Privileged Role&#34; access for &#34;Managed Test User&#34;.',
            response.data,
        )

    def test_admin_cannot_revoke_own_platform_admin_assignment(self):
        data = self._create_platform_admin_security_fixture()
        assignment_id = data["platform_assignment"].id

        response = self.client.post(
            f"/admin/role-assignments/{assignment_id}/revoke",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        assignment = db.session.get(
            UserRoleAssignment,
            assignment_id,
        )
        self.assertEqual(assignment.status, "Approved")
        self.assertIn(
            b"You cannot revoke your own active Platform Administration",
            response.data,
        )

    def test_admin_can_revoke_own_non_platform_admin_assignment(self):
        data = self._create_platform_admin_security_fixture()
        assignment_id = data["admin_secondary_assignment"].id

        response = self.client.post(
            f"/admin/role-assignments/{assignment_id}/revoke",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        assignment = db.session.get(
            UserRoleAssignment,
            assignment_id,
        )
        self.assertEqual(assignment.status, "Revoked")

        platform_assignment = db.session.get(
            UserRoleAssignment,
            data["platform_assignment"].id,
        )
        self.assertEqual(platform_assignment.status, "Approved")

    def test_authorization_allows_approved_department_scope(self):
        data = self._create_authorization_fixture()
        self.assertTrue(user_has_permission(
            data['user'],
            'view_department_students',
            institution_id=data['institution_a'].id,
            department_id=data['department_a'].id
        ))

    def test_authorization_allows_programme_inside_assigned_department(self):
        data = self._create_authorization_fixture()
        self.assertTrue(user_has_permission(
            data['user'],
            'view_department_students',
            programme_id=data['programme_a'].id
        ))

    def test_authorization_denies_other_department_same_institution(self):
        data = self._create_authorization_fixture()
        self.assertFalse(user_has_permission(
            data['user'],
            'view_department_students',
            institution_id=data['institution_a'].id,
            department_id=data['department_a_other'].id
        ))

    def test_authorization_denies_other_institution(self):
        data = self._create_authorization_fixture()
        self.assertFalse(user_has_permission(
            data['user'],
            'view_department_students',
            institution_id=data['institution_b'].id,
            department_id=data['department_b'].id
        ))

    def test_authorization_denies_mismatched_hierarchy(self):
        data = self._create_authorization_fixture()
        self.assertFalse(user_has_permission(
            data['user'],
            'view_department_students',
            institution_id=data['institution_a'].id,
            department_id=data['department_b'].id
        ))

    def test_authorization_denies_missing_permission(self):
        data = self._create_authorization_fixture()
        self.assertFalse(user_has_permission(
            data['user'],
            'manage_institution_settings',
            institution_id=data['institution_a'].id,
            department_id=data['department_a'].id
        ))

    def test_authorization_denies_pending_assignment(self):
        data = self._create_authorization_fixture()
        data['assignment'].status = 'Pending'
        db.session.commit()
        self.assertFalse(user_has_permission(
            data['user'],
            'view_department_students',
            institution_id=data['institution_a'].id,
            department_id=data['department_a'].id
        ))

    def test_authorization_denies_suspended_assignment(self):
        data = self._create_authorization_fixture()
        data['assignment'].status = 'Suspended'
        db.session.commit()
        self.assertFalse(user_has_permission(
            data['user'],
            'view_department_students',
            institution_id=data['institution_a'].id,
            department_id=data['department_a'].id
        ))

    def test_authorization_denies_revoked_assignment(self):
        data = self._create_authorization_fixture()
        data['assignment'].status = 'Revoked'
        db.session.commit()
        self.assertFalse(user_has_permission(
            data['user'],
            'view_department_students',
            institution_id=data['institution_a'].id,
            department_id=data['department_a'].id
        ))

    def test_authorization_denies_expired_assignment(self):
        data = self._create_authorization_fixture()
        data['assignment'].expires_at = datetime.utcnow() - timedelta(days=1)
        db.session.commit()
        self.assertFalse(user_has_permission(
            data['user'],
            'view_department_students',
            institution_id=data['institution_a'].id,
            department_id=data['department_a'].id
        ))

    def test_authorization_denies_inactive_role(self):
        data = self._create_authorization_fixture()
        data['role'].is_active = False
        db.session.commit()
        self.assertFalse(user_has_permission(
            data['user'],
            'view_department_students',
            institution_id=data['institution_a'].id,
            department_id=data['department_a'].id
        ))

    def test_authorization_denies_inactive_user(self):
        data = self._create_authorization_fixture()
        data['user'].account_status = 'Suspended'
        db.session.commit()
        self.assertFalse(user_has_permission(
            data['user'],
            'view_department_students',
            institution_id=data['institution_a'].id,
            department_id=data['department_a'].id
        ))

    def test_authorization_denies_department_assignment_without_scope(self):
        data = self._create_authorization_fixture()
        self.assertFalse(user_has_permission(
            data['user'],
            'view_department_students'
        ))


    def test_c4_clarification_request_notifies_requester(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        requester = data["managed_user"]
        reviewer = data["platform_admin"]
        sensitive_notes = "PRIVATE REVIEW NOTE: verify reference 88421."

        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        directory_request.reviewed_by_user_id = reviewer.id
        db.session.commit()

        response = self.client.post(
            f"/admin/directory-requests/{directory_request.id}/more-information",
            data={"reviewer_notes": sensitive_notes},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)

        notification = Notification.query.filter_by(
            recipient_user_id=requester.id,
            notification_type="directory_clarification_requested",
            source_id=directory_request.id,
        ).one()

        self.assertEqual(notification.category, "Directory & Reviews")
        self.assertEqual(notification.priority, "Important")
        self.assertEqual(notification.source_type, "DirectoryRequest")
        self.assertEqual(
            notification.action_url,
            f"/academic/directory-requests/{directory_request.id}",
        )
        self.assertNotIn(sensitive_notes, notification.message)

        self.assertEqual(
            Notification.query.filter_by(
                recipient_user_id=reviewer.id,
                notification_type="directory_clarification_requested",
                source_id=directory_request.id,
            ).count(),
            0,
        )

    def test_c4_requester_response_notifies_assigned_reviewer(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        requester = data["managed_user"]
        reviewer = data["platform_admin"]
        sensitive_response = "PRIVATE RESPONSE: registration reference 12345."

        directory_request.status = DirectoryRequest.STATUS_MORE_INFO_REQUIRED
        directory_request.reviewed_by_user_id = reviewer.id
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess.clear()
            sess["user_id"] = requester.id

        response = self.client.post(
            f"/academic/directory-requests/{directory_request.id}/respond",
            data={
                "clarification_message": sensitive_response,
                "evidence_reference": "https://example.edu/supporting-reference",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)

        db.session.refresh(directory_request)

        self.assertEqual(
            directory_request.status,
            DirectoryRequest.STATUS_UNDER_REVIEW,
        )
        self.assertEqual(
            directory_request.reviewed_by_user_id,
            reviewer.id,
        )

        notification = Notification.query.filter_by(
            recipient_user_id=reviewer.id,
            notification_type="directory_clarification_response_received",
            source_id=directory_request.id,
        ).one()

        self.assertEqual(notification.category, "Directory & Reviews")
        self.assertEqual(notification.priority, "Important")
        self.assertEqual(notification.source_type, "DirectoryRequest")
        self.assertEqual(
            notification.action_url,
            f"/admin/directory-requests/{directory_request.id}",
        )
        self.assertNotIn(sensitive_response, notification.message)
        self.assertNotIn(
            "https://example.edu/supporting-reference",
            notification.message,
        )

        self.assertEqual(
            Notification.query.filter_by(
                recipient_user_id=requester.id,
                notification_type="directory_clarification_response_received",
                source_id=directory_request.id,
            ).count(),
            0,
        )

    def test_c4_approval_notifies_requester_without_publishing_directory_record(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        requester = data["managed_user"]
        reviewer = data["platform_admin"]

        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        directory_request.reviewed_by_user_id = reviewer.id
        db.session.commit()

        response = self.client.post(
            f"/admin/directory-requests/{directory_request.id}/approve",
            data={"reviewer_notes": "Official evidence reviewed."},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)

        notification = Notification.query.filter_by(
            recipient_user_id=requester.id,
            notification_type="directory_request_approved",
            source_id=directory_request.id,
        ).one()

        self.assertEqual(notification.category, "Directory & Reviews")
        self.assertEqual(notification.priority, "Normal")
        self.assertEqual(notification.source_type, "DirectoryRequest")
        self.assertEqual(
            notification.action_url,
            f"/academic/directory-requests/{directory_request.id}",
        )

        self.assertIsNone(
            Institution.query.filter_by(
                name=directory_request.institution_name,
            ).first()
        )

    def test_c4_rejection_notifies_requester_without_exposing_reviewer_notes(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["submitted_institution"]
        requester = data["managed_user"]
        reviewer = data["platform_admin"]
        sensitive_notes = "PRIVATE REJECTION DETAIL: internal reference 7788."

        directory_request.status = DirectoryRequest.STATUS_UNDER_REVIEW
        directory_request.reviewed_by_user_id = reviewer.id
        db.session.commit()

        response = self.client.post(
            f"/admin/directory-requests/{directory_request.id}/reject",
            data={"reviewer_notes": sensitive_notes},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)

        notification = Notification.query.filter_by(
            recipient_user_id=requester.id,
            notification_type="directory_request_rejected",
            source_id=directory_request.id,
        ).one()

        self.assertEqual(notification.category, "Directory & Reviews")
        self.assertEqual(notification.priority, "Important")
        self.assertEqual(notification.source_type, "DirectoryRequest")
        self.assertEqual(
            notification.action_url,
            f"/academic/directory-requests/{directory_request.id}",
        )
        self.assertNotIn(sensitive_notes, notification.message)

    def test_c4_invalid_final_transition_creates_no_notification(self):
        data = self._create_directory_request_queue_fixture()
        directory_request = data["approved_request"]

        before_count = Notification.query.filter_by(
            source_type="DirectoryRequest",
            source_id=directory_request.id,
        ).count()

        response = self.client.post(
            f"/admin/directory-requests/{directory_request.id}/approve",
            data={"reviewer_notes": "Attempted duplicate approval."},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)

        after_count = Notification.query.filter_by(
            source_type="DirectoryRequest",
            source_id=directory_request.id,
        ).count()

        self.assertEqual(after_count, before_count)

    def test_notification_belongs_to_user(self):
        user = User(
            full_name="Notification Recipient",
            email="notification-recipient@example.com",
        )
        user.set_password("TestPassword123!")

        db.session.add(user)
        db.session.commit()

        notification = Notification(
            recipient_user_id=user.id,
            category=Notification.CATEGORY_SYSTEM,
            notification_type="system_test",
            title="Test notification",
            message="This notification belongs directly to a DSA user.",
        )

        db.session.add(notification)
        db.session.commit()

        self.assertEqual(notification.recipient.id, user.id)
        self.assertEqual(user.notifications.count(), 1)
        self.assertIsNone(
            StudentProfile.query.filter_by(user_id=user.id).first()
        )

    def test_notification_defaults_to_normal_and_unread(self):
        user = User(
            full_name="Unread Recipient",
            email="unread-recipient@example.com",
        )
        user.set_password("TestPassword123!")

        db.session.add(user)
        db.session.commit()

        notification = Notification(
            recipient_user_id=user.id,
            category=Notification.CATEGORY_SIWES,
            notification_type="siwes_test",
            title="SIWES update",
            message="A reusable SIWES notification.",
        )

        db.session.add(notification)
        db.session.commit()

        self.assertEqual(
            notification.priority,
            Notification.PRIORITY_NORMAL,
        )
        self.assertIsNone(notification.read_at)
        self.assertFalse(notification.is_read)

    def test_notification_read_state_is_derived_from_read_at(self):
        user = User(
            full_name="Read State Recipient",
            email="read-state-recipient@example.com",
        )
        user.set_password("TestPassword123!")

        db.session.add(user)
        db.session.commit()

        notification = Notification(
            recipient_user_id=user.id,
            category=Notification.CATEGORY_DIRECTORY,
            notification_type="directory_test",
            title="Directory update",
            message="A directory notification.",
        )

        db.session.add(notification)
        db.session.commit()

        self.assertFalse(notification.is_read)

        notification.read_at = datetime.utcnow()
        db.session.commit()

        self.assertTrue(notification.is_read)

    def test_notification_preserves_action_and_source_metadata(self):
        user = User(
            full_name="Action Recipient",
            email="action-recipient@example.com",
        )
        user.set_password("TestPassword123!")

        db.session.add(user)
        db.session.commit()

        notification = Notification(
            recipient_user_id=user.id,
            category=Notification.CATEGORY_DIRECTORY,
            notification_type="directory_request_response_received",
            title="Directory request response received",
            message="A requester responded to a clarification.",
            priority=Notification.PRIORITY_IMPORTANT,
            action_url="/admin/directory-requests/42",
            source_type="DirectoryRequest",
            source_id=42,
        )

        db.session.add(notification)
        db.session.commit()

        saved = db.session.get(Notification, notification.id)

        self.assertEqual(
            saved.action_url,
            "/admin/directory-requests/42",
        )
        self.assertEqual(saved.source_type, "DirectoryRequest")
        self.assertEqual(saved.source_id, 42)
        self.assertEqual(
            saved.priority,
            Notification.PRIORITY_IMPORTANT,
        )

    def test_user_can_have_multiple_notifications(self):
        user = User(
            full_name="Multiple Notification Recipient",
            email="multiple-notifications@example.com",
        )
        user.set_password("TestPassword123!")

        db.session.add(user)
        db.session.commit()

        first = Notification(
            recipient_user_id=user.id,
            category=Notification.CATEGORY_PLACEMENT,
            notification_type="placement_test",
            title="Placement update",
            message="Your placement activity changed.",
        )

        second = Notification(
            recipient_user_id=user.id,
            category=Notification.CATEGORY_OFFICIAL_NOTICE,
            notification_type="official_notice_test",
            title="Official notice",
            message="A new official notice is available.",
        )

        db.session.add_all([first, second])
        db.session.commit()

        self.assertEqual(user.notifications.count(), 2)

    def test_notification_service_isolates_user_inboxes(self):
        user_a = User(
            full_name="Notification User A",
            email="notification-user-a@example.com",
        )
        user_a.set_password("TestPassword123!")

        user_b = User(
            full_name="Notification User B",
            email="notification-user-b@example.com",
        )
        user_b.set_password("TestPassword123!")

        db.session.add_all([user_a, user_b])
        db.session.commit()

        notification_a = create_notification(
            user_a,
            Notification.CATEGORY_SYSTEM,
            "user_a_test",
            "User A notification",
            "Visible only to User A.",
        )

        notification_b = create_notification(
            user_b,
            Notification.CATEGORY_SYSTEM,
            "user_b_test",
            "User B notification",
            "Visible only to User B.",
        )

        user_a_notifications = get_notifications_for_user(user_a)
        user_b_notifications = get_notifications_for_user(user_b)

        self.assertEqual(
            [item.id for item in user_a_notifications],
            [notification_a.id],
        )
        self.assertEqual(
            [item.id for item in user_b_notifications],
            [notification_b.id],
        )

    def test_notification_service_unread_count_is_recipient_scoped(self):
        user_a = User(
            full_name="Unread User A",
            email="unread-user-a@example.com",
        )
        user_a.set_password("TestPassword123!")

        user_b = User(
            full_name="Unread User B",
            email="unread-user-b@example.com",
        )
        user_b.set_password("TestPassword123!")

        db.session.add_all([user_a, user_b])
        db.session.commit()

        create_notification(
            user_a,
            Notification.CATEGORY_SIWES,
            "user_a_unread",
            "User A unread",
            "Unread for User A.",
        )

        create_notification(
            user_b,
            Notification.CATEGORY_SIWES,
            "user_b_unread_one",
            "User B unread one",
            "First unread for User B.",
        )

        create_notification(
            user_b,
            Notification.CATEGORY_SIWES,
            "user_b_unread_two",
            "User B unread two",
            "Second unread for User B.",
        )

        self.assertEqual(get_unread_count_for_user(user_a), 1)
        self.assertEqual(get_unread_count_for_user(user_b), 2)

    def test_notification_service_cannot_fetch_another_users_notification(self):
        user_a = User(
            full_name="Fetch User A",
            email="fetch-user-a@example.com",
        )
        user_a.set_password("TestPassword123!")

        user_b = User(
            full_name="Fetch User B",
            email="fetch-user-b@example.com",
        )
        user_b.set_password("TestPassword123!")

        db.session.add_all([user_a, user_b])
        db.session.commit()

        notification_b = create_notification(
            user_b,
            Notification.CATEGORY_SYSTEM,
            "private_notification",
            "Private notification",
            "This belongs to User B.",
        )

        self.assertIsNone(
            get_notification_for_user(
                user_a,
                notification_b.id,
            )
        )

    def test_notification_service_cannot_mark_another_users_notification_read(self):
        user_a = User(
            full_name="Read User A",
            email="read-user-a@example.com",
        )
        user_a.set_password("TestPassword123!")

        user_b = User(
            full_name="Read User B",
            email="read-user-b@example.com",
        )
        user_b.set_password("TestPassword123!")

        db.session.add_all([user_a, user_b])
        db.session.commit()

        notification_b = create_notification(
            user_b,
            Notification.CATEGORY_ACCESS_SECURITY,
            "private_access_event",
            "Private access notification",
            "This belongs to User B.",
        )

        result = mark_notification_read(
            user_a,
            notification_b.id,
        )

        db.session.refresh(notification_b)

        self.assertIsNone(result)
        self.assertIsNone(notification_b.read_at)
        self.assertFalse(notification_b.is_read)

    def test_mark_all_notifications_read_does_not_touch_another_user(self):
        user_a = User(
            full_name="Bulk User A",
            email="bulk-user-a@example.com",
        )
        user_a.set_password("TestPassword123!")

        user_b = User(
            full_name="Bulk User B",
            email="bulk-user-b@example.com",
        )
        user_b.set_password("TestPassword123!")

        db.session.add_all([user_a, user_b])
        db.session.commit()

        create_notification(
            user_a,
            Notification.CATEGORY_PLACEMENT,
            "placement_one",
            "Placement one",
            "First User A notification.",
        )

        create_notification(
            user_a,
            Notification.CATEGORY_PLACEMENT,
            "placement_two",
            "Placement two",
            "Second User A notification.",
        )

        notification_b = create_notification(
            user_b,
            Notification.CATEGORY_PLACEMENT,
            "placement_private",
            "User B placement",
            "User B notification.",
        )

        changed = mark_all_notifications_read(user_a)

        db.session.refresh(notification_b)

        self.assertEqual(changed, 2)
        self.assertEqual(get_unread_count_for_user(user_a), 0)
        self.assertEqual(get_unread_count_for_user(user_b), 1)
        self.assertIsNone(notification_b.read_at)

    def test_notification_service_rejects_external_action_url(self):
        user = User(
            full_name="Action URL User",
            email="action-url-user@example.com",
        )
        user.set_password("TestPassword123!")

        db.session.add(user)
        db.session.commit()

        with self.assertRaises(NotificationServiceError):
            create_notification(
                user,
                Notification.CATEGORY_SYSTEM,
                "unsafe_link",
                "Unsafe action",
                "External links must not become notification actions.",
                action_url="https://example.com/phishing",
            )

        with self.assertRaises(NotificationServiceError):
            create_notification(
                user,
                Notification.CATEGORY_SYSTEM,
                "unsafe_protocol_relative_link",
                "Unsafe action",
                "Protocol-relative links must also be rejected.",
                action_url="//example.com/phishing",
            )

    def test_notification_service_validates_category_priority_and_source(self):
        user = User(
            full_name="Validation User",
            email="notification-validation@example.com",
        )
        user.set_password("TestPassword123!")

        db.session.add(user)
        db.session.commit()

        with self.assertRaises(NotificationServiceError):
            create_notification(
                user,
                "Unknown Category",
                "invalid_category",
                "Invalid category",
                "This category must be rejected.",
            )

        with self.assertRaises(NotificationServiceError):
            create_notification(
                user,
                Notification.CATEGORY_SYSTEM,
                "invalid_priority",
                "Invalid priority",
                "This priority must be rejected.",
                priority="Critical",
            )

        with self.assertRaises(NotificationServiceError):
            create_notification(
                user,
                Notification.CATEGORY_DIRECTORY,
                "invalid_source",
                "Invalid source",
                "Source metadata must remain consistent.",
                source_type="DirectoryRequest",
                source_id=None,
            )


if __name__ == '__main__':
    unittest.main()

