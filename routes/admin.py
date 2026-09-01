"""
Admin Routes Blueprint
----------------------
Provides a secure administrative interface to manage organizations,
verify student submissions, edit SIWES guide topics, and inspect student placement metrics.
"""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from models.db import db
from models.organization import Organization
from models.guide import GuideTopic
from models.student import StudentProfile
from models.application import PlacementApplication
from routes.student import AREAS_OF_INTEREST, ORGANIZATION_TYPES, NIGERIAN_STATES

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to enforce admin authentication on admin views."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Please log in with administrator credentials to access this area.', 'warning')
            return redirect(url_for('admin.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Simple and secure session-based admin login."""
    if session.get('is_admin'):
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        admin_user = current_app.config.get('ADMIN_USERNAME', 'admin')
        admin_pass = current_app.config.get('ADMIN_PASSWORD')
        if username == admin_user and password == admin_pass:
            session['is_admin'] = True
            flash('Welcome to the SIWES Assistant Administration Panel.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin.dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    """Logs out admin user."""
    session.pop('is_admin', None)
    flash('Logged out of admin panel.', 'info')
    return redirect(url_for('main.index'))


@admin_bp.route('/')
@admin_required
def dashboard():
    """Admin dashboard with analytics and high-level controls."""
    total_orgs = Organization.query.count()
    verified_orgs = Organization.query.filter_by(verification_status='Verified').count()
    pending_submissions = Organization.query.filter_by(verification_status='Student Submitted').count()
    total_students = StudentProfile.query.count()
    total_applications = PlacementApplication.query.count()
    guide_topics_count = GuideTopic.query.count()

    recent_submissions = Organization.query.filter_by(verification_status='Student Submitted').order_by(Organization.created_at.desc()).limit(5).all()
    recent_applications = PlacementApplication.query.order_by(PlacementApplication.updated_at.desc()).limit(8).all()

    return render_template(
        'admin/dashboard.html',
        total_orgs=total_orgs,
        verified_orgs=verified_orgs,
        pending_submissions=pending_submissions,
        total_students=total_students,
        total_applications=total_applications,
        guide_topics_count=guide_topics_count,
        recent_submissions=recent_submissions,
        recent_applications=recent_applications
    )


@admin_bp.route('/organizations')
@admin_required
def organizations():
    """List all organizations with management and verification controls."""
    status_filter = request.args.get('status', 'all')
    query = Organization.query

    if status_filter != 'all':
        query = query.filter_by(verification_status=status_filter)

    orgs = query.order_by(Organization.created_at.desc()).all()
    return render_template(
        'admin/organizations.html',
        organizations=orgs,
        active_status=status_filter
    )


@admin_bp.route('/organizations/new', methods=['GET', 'POST'])
@admin_required
def new_organization():
    """Create a new verified organization."""
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
        verification_status = request.form.get('verification_status', 'Verified').strip()
        source = request.form.get('source', 'Departmental Verified').strip()
        why_relevant = request.form.get('why_relevant', '').strip()

        org = Organization(
            name=name,
            description=description,
            address=address,
            state=state,
            city=city,
            industry=industry,
            relevance_areas=relevance_areas,
            website=website,
            contact_email=contact_email,
            contact_phone=contact_phone,
            verification_status=verification_status,
            source=source,
            why_relevant=why_relevant,
            is_active=True
        )
        db.session.add(org)
        db.session.commit()
        flash(f'Organization "{name}" added successfully!', 'success')
        return redirect(url_for('admin.organizations'))

    return render_template(
        'admin/org_form.html',
        org=None,
        states=NIGERIAN_STATES,
        interests=AREAS_OF_INTEREST,
        org_types=ORGANIZATION_TYPES
    )


@admin_bp.route('/organizations/edit/<int:org_id>', methods=['GET', 'POST'])
@admin_required
def edit_organization(org_id):
    """Edit an existing organization."""
    org = Organization.query.get_or_404(org_id)

    if request.method == 'POST':
        org.name = request.form.get('name', '').strip()
        org.description = request.form.get('description', '').strip()
        org.address = request.form.get('address', '').strip()
        org.state = request.form.get('state', '').strip()
        org.city = request.form.get('city', '').strip()
        org.industry = request.form.get('industry', '').strip()
        org.relevance_areas = request.form.get('relevance_areas', '').strip()
        org.website = request.form.get('website', '').strip()
        org.contact_email = request.form.get('contact_email', '').strip()
        org.contact_phone = request.form.get('contact_phone', '').strip()
        org.verification_status = request.form.get('verification_status', org.verification_status).strip()
        org.source = request.form.get('source', org.source).strip()
        org.why_relevant = request.form.get('why_relevant', '').strip()
        org.is_active = True if request.form.get('is_active') == 'on' else False

        db.session.commit()
        flash(f'Updated details for "{org.name}".', 'success')
        return redirect(url_for('admin.organizations'))

    return render_template(
        'admin/org_form.html',
        org=org,
        states=NIGERIAN_STATES,
        interests=AREAS_OF_INTEREST,
        org_types=ORGANIZATION_TYPES
    )


@admin_bp.route('/organizations/verify/<int:org_id>', methods=['POST'])
@admin_required
def verify_organization(org_id):
    """Quickly approve and verify a student submitted organization."""
    org = Organization.query.get_or_404(org_id)
    org.verification_status = 'Verified'
    org.source = 'Admin Verified Submission'
    db.session.commit()
    flash(f'Marked "{org.name}" as Verified.', 'success')
    return redirect(url_for('admin.organizations'))


@admin_bp.route('/organizations/delete/<int:org_id>', methods=['POST'])
@admin_required
def delete_organization(org_id):
    """Delete an organization."""
    org = Organization.query.get_or_404(org_id)
    name = org.name
    db.session.delete(org)
    db.session.commit()
    flash(f'Deleted organization "{name}".', 'info')
    return redirect(url_for('admin.organizations'))


@admin_bp.route('/guides')
@admin_required
def guides():
    """List all SIWES Guide topics with edit links."""
    topics = GuideTopic.query.order_by(GuideTopic.order_num.asc()).all()
    return render_template('admin/guides.html', topics=topics)


@admin_bp.route('/guides/new', methods=['GET', 'POST'])
@admin_required
def new_guide():
    """Create a new guide topic."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        slug = request.form.get('slug', '').strip().lower().replace(' ', '-')
        category = request.form.get('category', 'General Guidance').strip()
        summary = request.form.get('summary', '').strip()
        content = request.form.get('content', '').strip()
        order_num = int(request.form.get('order_num', 0))
        icon = request.form.get('icon', 'book-open').strip()

        topic = GuideTopic(
            slug=slug,
            title=title,
            category=category,
            summary=summary,
            content=content,
            order_num=order_num,
            icon=icon,
            is_published=True
        )
        db.session.add(topic)
        db.session.commit()
        flash(f'Guide topic "{title}" created successfully!', 'success')
        return redirect(url_for('admin.guides'))

    return render_template('admin/guide_form.html', topic=None)


@admin_bp.route('/guides/edit/<int:topic_id>', methods=['GET', 'POST'])
@admin_required
def edit_guide(topic_id):
    """Edit an existing guide topic."""
    topic = GuideTopic.query.get_or_404(topic_id)

    if request.method == 'POST':
        topic.title = request.form.get('title', '').strip()
        topic.slug = request.form.get('slug', '').strip().lower().replace(' ', '-')
        topic.category = request.form.get('category', topic.category).strip()
        topic.summary = request.form.get('summary', '').strip()
        topic.content = request.form.get('content', '').strip()
        topic.order_num = int(request.form.get('order_num', topic.order_num))
        topic.icon = request.form.get('icon', topic.icon).strip()
        topic.is_published = True if request.form.get('is_published') == 'on' else False

        db.session.commit()
        flash(f'Updated guide topic "{topic.title}".', 'success')
        return redirect(url_for('admin.guides'))

    return render_template('admin/guide_form.html', topic=topic)
