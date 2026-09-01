"""
Placement Routes Blueprint
--------------------------
Handles SIWES placement search, search results, organization details,
bookmarking, application tracking, and student organization submissions.
"""
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models.db import db
from models.organization import Organization
from models.student import StudentProfile
from models.application import SavedOrganization, PlacementApplication
from services.placement_search import PlacementSearchService
from routes.student import AREAS_OF_INTEREST, ORGANIZATION_TYPES, NIGERIAN_STATES

placement_bp = Blueprint('placement', __name__)

search_service = PlacementSearchService()


@placement_bp.route('/placement')
def search_form():
    """Placement search query form."""
    # Pre-populate filters if student has an active profile
    student_id = session.get('student_id')
    student = db.session.get(StudentProfile, student_id) if student_id else None

    default_state = student.preferred_state if student else ''
    default_city = student.preferred_city if student else ''
    default_interest = student.area_of_interest if student else ''
    default_org_type = student.preferred_org_type if student else ''

    return render_template(
        'placement.html',
        states=NIGERIAN_STATES,
        interests=AREAS_OF_INTEREST,
        org_types=ORGANIZATION_TYPES,
        default_state=default_state,
        default_city=default_city,
        default_interest=default_interest,
        default_org_type=default_org_type
    )


@placement_bp.route('/placement/results')
def search_results():
    """Executes search and displays placement result cards."""
    state = request.args.get('state', '').strip()
    city = request.args.get('city', '').strip()
    interest = request.args.get('interest', '').strip()
    org_type = request.args.get('org_type', '').strip()
    keywords = request.args.get('keywords', '').strip()

    search_data = search_service.search(
        state=state,
        city=city,
        interest=interest,
        org_type=org_type,
        keywords=keywords
    )

    # Get student's saved org IDs to show bookmarked state
    student_id = session.get('student_id')
    saved_org_ids = set()
    if student_id:
        saved_entries = SavedOrganization.query.filter_by(student_id=student_id).all()
        saved_org_ids = {entry.organization_id for entry in saved_entries}

    return render_template(
        'results.html',
        results=search_data['database_results'],
        web_results=search_data['web_results'],
        live_search_status=search_data['live_search_status'],
        total_count=search_data['total_count'],
        query_params=search_data['query_params'],
        saved_org_ids=saved_org_ids,
        states=NIGERIAN_STATES,
        interests=AREAS_OF_INTEREST,
        org_types=ORGANIZATION_TYPES
    )


@placement_bp.route('/placement/<int:org_id>')
def organization_detail(org_id):
    """Detailed view for a specific organization."""
    org = Organization.query.get_or_404(org_id)
    
    student_id = session.get('student_id')
    is_saved = False
    application = None
    
    if student_id:
        is_saved = SavedOrganization.query.filter_by(student_id=student_id, organization_id=org.id).first() is not None
        application = PlacementApplication.query.filter_by(student_id=student_id, organization_id=org.id).first()

    return render_template(
        'organization.html',
        org=org,
        is_saved=is_saved,
        application=application,
        status_choices=PlacementApplication.STATUS_CHOICES
    )


@placement_bp.route('/placement/save/<int:org_id>', methods=['POST'])
def toggle_save(org_id):
    """Save or remove an organization from student's bookmarks."""
    student_id = session.get('student_id')
    if not student_id:
        flash('Please create or switch to your student profile first to save organizations.', 'warning')
        return redirect(url_for('student.profile'))

    org = Organization.query.get_or_404(org_id)
    existing = SavedOrganization.query.filter_by(student_id=student_id, organization_id=org.id).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash(f'Removed {org.name} from your saved organizations.', 'info')
    else:
        new_save = SavedOrganization(student_id=student_id, organization_id=org.id)
        db.session.add(new_save)
        db.session.commit()
        flash(f'Saved {org.name} to your dashboard!', 'success')

    redirect_to = request.referrer or url_for('placement.organization_detail', org_id=org.id)
    return redirect(redirect_to)


@placement_bp.route('/placement/track/<int:org_id>', methods=['POST'])
def track_application(org_id):
    """Create or update a placement application tracking record."""
    student_id = session.get('student_id')
    if not student_id:
        flash('Please create or switch to your student profile first to track applications.', 'warning')
        return redirect(url_for('student.profile'))

    org = Organization.query.get_or_404(org_id)
    status = request.form.get('status', 'Interested').strip()
    notes = request.form.get('notes', '').strip()
    applied_date_str = request.form.get('applied_date', '').strip()

    if status not in PlacementApplication.STATUS_CHOICES:
        status = 'Interested'

    applied_date = None
    if applied_date_str:
        try:
            applied_date = datetime.strptime(applied_date_str, '%Y-%m-%d').date()
        except ValueError:
            applied_date = date.today()

    app = PlacementApplication.query.filter_by(student_id=student_id, organization_id=org.id).first()
    if app:
        app.status = status
        app.notes = notes
        if applied_date:
            app.applied_date = applied_date
        flash(f'Application status for {org.name} updated to: {status}', 'success')
    else:
        app = PlacementApplication(
            student_id=student_id,
            organization_id=org.id,
            status=status,
            notes=notes,
            applied_date=applied_date or date.today()
        )
        db.session.add(app)
        flash(f'Added {org.name} to your application tracker as "{status}"!', 'success')

    db.session.commit()
    return redirect(url_for('student.dashboard'))


@placement_bp.route('/placement/submit-org', methods=['GET', 'POST'])
def submit_organization():
    """Allows students to submit an organization they discovered for community verification."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        address = request.form.get('address', '').strip()
        state = request.form.get('state', '').strip()
        city = request.form.get('city', '').strip()
        industry = request.form.get('industry', '').strip()
        relevance_areas = request.form.get('relevance_areas', '').strip()
        website = request.form.get('website', '').strip()
        contact_email = request.form.get('contact_email', '').strip()
        contact_phone = request.form.get('contact_phone', '').strip()
        why_relevant = request.form.get('why_relevant', '').strip()

        if not name or not state or not city or not industry:
            flash('Please provide organization name, state, city, and industry.', 'danger')
            return render_template('submit_org.html', states=NIGERIAN_STATES, interests=AREAS_OF_INTEREST, org_types=ORGANIZATION_TYPES)

        # Store with explicit "Student Submitted" status
        new_org = Organization(
            name=name,
            description=description or f"Technology/Engineering organization in {city}, {state}.",
            address=address,
            state=state,
            city=city,
            industry=industry,
            relevance_areas=relevance_areas or industry,
            website=website,
            contact_email=contact_email,
            contact_phone=contact_phone,
            verification_status='Student Submitted',
            source='Student Submission',
            why_relevant=why_relevant or f"Recommended by student for {relevance_areas} industrial training.",
            is_active=True
        )
        db.session.add(new_org)
        db.session.commit()
        flash(f'Thank you! "{name}" has been added with "Student Submitted" status and is visible to other students.', 'success')
        return redirect(url_for('placement.organization_detail', org_id=new_org.id))

    return render_template(
        'submit_org.html',
        states=NIGERIAN_STATES,
        interests=AREAS_OF_INTEREST,
        org_types=ORGANIZATION_TYPES
    )
