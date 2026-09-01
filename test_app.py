"""
Automated Test Suite for Departmental SIWES Assistant (DSA)
------------------------------------------------------------
Tests database models, route endpoints, placement search,
student profile persistence, and admin authentication.
"""
import unittest
from app import create_app
from models.db import db
from models.student import StudentProfile
from models.organization import Organization
from models.guide import GuideTopic
from models.application import SavedOrganization, PlacementApplication
from services.placement_search import PlacementSearchService

class DSATestCase(unittest.TestCase):
    def setUp(self):
        """Set up test client with testing configuration."""
        self.app = create_app('testing')
        self.app.config['ADMIN_USERNAME'] = 'admin'
        self.app.config['ADMIN_PASSWORD'] = 'test-password'

        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Seed minimal test data
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
        db.session.add(self.guide)
        db.session.add(self.org)
        db.session.commit()

    def tearDown(self):
        """Clean up database."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_home_page(self):
        """Test homepage loads successfully."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Departmental', response.data)
        self.assertIn(b'SIWES Assistant', response.data)

    def test_siwes_guide_page(self):
        """Test SIWES Guide page loads and renders topic."""
        response = self.client.get('/siwes-guide')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Guide Topic', response.data)

    def test_siwes_guide_detail_page(self):
        """Test direct guide slug route."""
        response = self.client.get('/siwes-guide/test-guide')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test content here', response.data)

    def test_placement_search_form(self):
        """Test placement search page loads."""
        response = self.client.get('/placement')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Find SIWES Placement', response.data)

    def test_placement_search_results(self):
        """Test search query returns matching organization."""
        response = self.client.get('/placement/results?state=Abuja&interest=Software')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'NITDA Test', response.data)
        self.assertIn(b'Verified', response.data)

    def test_organization_details(self):
        """Test organization detail page loads."""
        response = self.client.get(f'/placement/{self.org.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'NITDA Test', response.data)
        self.assertIn(b'Application Tracker', response.data)

    def test_student_profile_create_and_dashboard(self):
        """Test student profile creation and dashboard access."""
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

        # Check DB
        student = StudentProfile.query.filter_by(matric_no='ENG/2022/9999').first()
        self.assertIsNotNone(student)

    def test_bookmark_and_track_application(self):
        """Test bookmarking an organization and updating application status."""
        # Create student
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

        # Set session
        with self.client.session_transaction() as sess:
            sess['student_id'] = student.id

        # Bookmark org
        save_resp = self.client.post(f'/placement/save/{self.org.id}', follow_redirects=True)
        self.assertEqual(save_resp.status_code, 200)
        self.assertIsNotNone(SavedOrganization.query.filter_by(student_id=student.id, organization_id=self.org.id).first())

        # Track application
        track_data = {
            'status': 'Application Submitted',
            'notes': 'Sent formal request letter to IT desk',
            'applied_date': '2026-08-31'
        }
        track_resp = self.client.post(f'/placement/track/{self.org.id}', data=track_data, follow_redirects=True)
        self.assertEqual(track_resp.status_code, 200)

        app = PlacementApplication.query.filter_by(student_id=student.id, organization_id=self.org.id).first()
        self.assertIsNotNone(app)
        self.assertEqual(app.status, 'Application Submitted')

    def test_admin_authentication_and_dashboard(self):
        """Test admin login protection and dashboard access."""
        # Unauthenticated access should redirect to login
        resp_unauth = self.client.get('/admin/', follow_redirects=True)
        self.assertIn(b'Administrator Access', resp_unauth.data)

        # Login with credentials
        login_resp = self.client.post('/admin/login', data={'username': 'admin', 'password': 'test-password'}, follow_redirects=True)
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn(b'SIWES Management Console', login_resp.data)

if __name__ == '__main__':
    unittest.main()
