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
            b'Platform overview',
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


if __name__ == '__main__':
    unittest.main()
