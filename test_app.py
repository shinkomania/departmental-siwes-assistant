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
from services.placement_search import PlacementSearchService
from services.authorization import user_has_permission


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

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _create_authorization_fixture(self):
        institution_a = Institution(
            name='Institution A',
            institution_type='University',
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
            'department_a': department_a,
            'department_a_other': department_a_other,
            'department_b': department_b,
            'programme_a': programme_a,
            'programme_a_other': programme_a_other,
            'programme_b': programme_b,
        }

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
        self.assertEqual(
            organization.verification_status,
            "Student Submitted",
        )
        self.assertEqual(
            organization.source,
            "Student Submission",
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
            b'SIWES Management Console',
            response.data,
        )

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


if __name__ == '__main__':
    unittest.main()
