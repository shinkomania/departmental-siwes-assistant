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
        self.app.config['ADMIN_USERNAME'] = 'admin'
        self.app.config['ADMIN_PASSWORD'] = 'test-password'

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
        self.assertIn(b'Verified', response.data)

    def test_organization_details(self):
        response = self.client.get(f'/placement/{self.org.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'NITDA Test', response.data)
        self.assertIn(b'Application Tracker', response.data)

    def test_student_profile_create_and_dashboard(self):
        post_data = {
            'full_name': 'Musa Danladi',
            'matric_no': 'ENG/2022/9999',
            'department': 'Computer Engineering',
            'faculty': 'Faculty of Engineering',
            'university': 'Ahmadu Bello University',
            'preferred_state': 'Kaduna',
            'preferred_city': 'Zaria',
            'area_of_interest': 'Software Development',
            'preferred_org_type': 'Technology company',
            'skills': 'Python, SQL',
            'bio': 'Test bio'
        }
        response = self.client.post('/profile', data=post_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Musa Danladi', response.data)
        self.assertIn(b'ENG/2022/9999', response.data)
        self.assertIsNotNone(
            StudentProfile.query.filter_by(matric_no='ENG/2022/9999').first()
        )

    def test_bookmark_and_track_application(self):
        student = StudentProfile(
            full_name='Test Student',
            matric_no='ENG/TEST/1',
            department='Computer Engineering',
            faculty='Engineering',
            university='University of Lagos',
            preferred_state='Lagos',
            preferred_city='Yaba',
            area_of_interest='Software Development',
            preferred_org_type='Technology company'
        )
        db.session.add(student)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess['student_id'] = student.id

        save_resp = self.client.post(
            f'/placement/save/{self.org.id}',
            follow_redirects=True
        )
        self.assertEqual(save_resp.status_code, 200)
        self.assertIsNotNone(
            SavedOrganization.query.filter_by(
                student_id=student.id,
                organization_id=self.org.id
            ).first()
        )

        track_resp = self.client.post(
            f'/placement/track/{self.org.id}',
            data={
                'status': 'Application Submitted',
                'notes': 'Sent formal request letter to IT desk',
                'applied_date': '2026-08-31'
            },
            follow_redirects=True
        )
        self.assertEqual(track_resp.status_code, 200)

        app = PlacementApplication.query.filter_by(
            student_id=student.id,
            organization_id=self.org.id
        ).first()
        self.assertIsNotNone(app)
        self.assertEqual(app.status, 'Application Submitted')

    def test_admin_authentication_and_dashboard(self):
        resp_unauth = self.client.get('/admin/', follow_redirects=True)
        self.assertIn(b'Administrator Access', resp_unauth.data)

        login_resp = self.client.post(
            '/admin/login',
            data={'username': 'admin', 'password': 'test-password'},
            follow_redirects=True
        )
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn(b'SIWES Management Console', login_resp.data)

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
