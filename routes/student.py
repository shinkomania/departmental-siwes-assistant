"""
Student Routes Blueprint
------------------------
Handles student profile management and the student command dashboard.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.db import db
from models.student import StudentProfile
from models.application import SavedOrganization, PlacementApplication
from models.organization import Organization

student_bp = Blueprint('student', __name__)

# Standard options for Nigerian engineering students
AREAS_OF_INTEREST = [
    'Software Development',
    'Artificial Intelligence',
    'Machine Learning',
    'Web Development',
    'Mobile Development',
    'Networking & Telecommunications',
    'Cybersecurity',
    'Embedded Systems & IoT',
    'Computer Hardware & Maintenance',
    'Data Science & Analytics',
    'Cloud Computing & DevOps',
    'Other'
]

ORGANIZATION_TYPES = [
    'Technology company',
    'Software company',
    'Telecom company',
    'Bank/Fintech',
    'Government organization',
    'Engineering company',
    'Research organization',
    'Startup',
    'Other'
]

NIGERIAN_STATES = [
    'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa', 'Benue', 'Borno',
    'Cross River', 'Delta', 'Ebonyi', 'Edo', 'Ekiti', 'Enugu', 'FCT Abuja', 'Gombe',
    'Imo', 'Jigawa', 'Kaduna', 'Kano', 'Katsina', 'Kebbi', 'Kogi', 'Kwara', 'Lagos',
    'Nasarawa', 'Niger', 'Ogun', 'Ondo', 'Osun', 'Oyo', 'Plateau', 'Rivers', 'Sokoto',
    'Taraba', 'Yobe', 'Zamfara'
]


@student_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    """
    View and edit the student profile.
    Uses session['student_id'] or creates a new student record.
    """
    student_id = session.get('student_id')
    student = None
    if student_id:
        student = db.session.get(StudentProfile, student_id)

    # If matriculation number passed via query or search
    matric_query = request.args.get('matric')
    if matric_query and not student:
        student = StudentProfile.query.filter_by(matric_no=matric_query.strip()).first()
        if student:
            session['student_id'] = student.id

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        matric_no = request.form.get('matric_no', '').strip()
        department = request.form.get('department', '').strip()
        faculty = request.form.get('faculty', '').strip()
        university = request.form.get('university', '').strip()
        preferred_state = request.form.get('preferred_state', '').strip()
        preferred_city = request.form.get('preferred_city', '').strip()
        area_of_interest = request.form.get('area_of_interest', '').strip()
        skills = request.form.get('skills', '').strip()
        preferred_org_type = request.form.get('preferred_org_type', '').strip()
        bio = request.form.get('bio', '').strip()

        # Basic Form Validation
        if not full_name or not matric_no or not university or not preferred_state or not area_of_interest:
            flash('Please fill in all required profile fields.', 'danger')
            return render_template(
                'profile.html',
                student=student,
                interests=AREAS_OF_INTEREST,
                org_types=ORGANIZATION_TYPES,
                states=NIGERIAN_STATES
            )

        # Check if updating existing or creating new
        if student:
            # Check for duplicate matric number on other accounts
            existing = StudentProfile.query.filter(StudentProfile.matric_no == matric_no, StudentProfile.id != student.id).first()
            if existing:
                flash(f'Matriculation number {matric_no} is already registered by another profile.', 'warning')
                return render_template('profile.html', student=student, interests=AREAS_OF_INTEREST, org_types=ORGANIZATION_TYPES, states=NIGERIAN_STATES)
            
            student.full_name = full_name
            student.matric_no = matric_no
            student.department = department
            student.faculty = faculty
            student.university = university
            student.preferred_state = preferred_state
            student.preferred_city = preferred_city
            student.area_of_interest = area_of_interest
            student.skills = skills
            student.preferred_org_type = preferred_org_type
            student.bio = bio
            flash('Student profile updated successfully!', 'success')
        else:
            # Check if student with this matric number already exists
            existing = StudentProfile.query.filter_by(matric_no=matric_no).first()
            if existing:
                student = existing
                student.full_name = full_name
                student.department = department
                student.faculty = faculty
                student.university = university
                student.preferred_state = preferred_state
                student.preferred_city = preferred_city
                student.area_of_interest = area_of_interest
                student.skills = skills
                student.preferred_org_type = preferred_org_type
                student.bio = bio
                flash('Existing profile matched and updated!', 'success')
            else:
                student = StudentProfile(
                    full_name=full_name,
                    matric_no=matric_no,
                    department=department,
                    faculty=faculty,
                    university=university,
                    preferred_state=preferred_state,
                    preferred_city=preferred_city,
                    area_of_interest=area_of_interest,
                    skills=skills,
                    preferred_org_type=preferred_org_type,
                    bio=bio
                )
                db.session.add(student)
                flash('Profile created successfully! Welcome to Departmental SIWES Assistant.', 'success')

        db.session.commit()
        session['student_id'] = student.id
        return redirect(url_for('student.dashboard'))

    return render_template(
        'profile.html',
        student=student,
        interests=AREAS_OF_INTEREST,
        org_types=ORGANIZATION_TYPES,
        states=NIGERIAN_STATES
    )


@student_bp.route('/dashboard')
def dashboard():
    """
    Student command center.
    Shows profile overview, saved organizations, and active application pipeline.
    """
    student_id = session.get('student_id')
    student = None
    if student_id:
        student = db.session.get(StudentProfile, student_id)

    # If no student profile in session, retrieve the most recent or invite profile creation
    if not student:
        student = StudentProfile.query.order_by(StudentProfile.id.desc()).first()
        if student:
            session['student_id'] = student.id

    if not student:
        flash('Please complete your student profile to access the personalized SIWES dashboard.', 'info')
        return redirect(url_for('student.profile'))

    # Retrieve Saved Organizations
    saved_entries = SavedOrganization.query.filter_by(student_id=student.id).order_by(SavedOrganization.saved_at.desc()).all()
    
    # Retrieve Placement Applications
    applications = PlacementApplication.query.filter_by(student_id=student.id).order_by(PlacementApplication.updated_at.desc()).all()

    # Application Statistics
    status_counts = {
        'Interested': 0,
        'Contacted': 0,
        'Application Submitted': 0,
        'Interview': 0,
        'Accepted': 0,
        'Rejected': 0
    }
    for app in applications:
        if app.status in status_counts:
            status_counts[app.status] += 1

    return render_template(
        'dashboard.html',
        student=student,
        saved_entries=saved_entries,
        applications=applications,
        status_counts=status_counts,
        total_saved=len(saved_entries),
        total_applied=len(applications),
        status_choices=PlacementApplication.STATUS_CHOICES
    )


@student_bp.route('/switch-profile', methods=['POST'])
def switch_profile():
    """Allows student to look up their profile by Matric Number."""
    matric_no = request.form.get('matric_no', '').strip()
    student = StudentProfile.query.filter_by(matric_no=matric_no).first()
    if student:
        session['student_id'] = student.id
        flash(f'Switched to profile: {student.full_name} ({student.matric_no})', 'success')
    else:
        flash(f'No profile found with Matriculation Number: {matric_no}. You can create one now.', 'warning')
        return redirect(url_for('student.profile'))
    return redirect(url_for('student.dashboard'))
