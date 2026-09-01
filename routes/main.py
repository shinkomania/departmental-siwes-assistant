"""
Main Routes Blueprint
---------------------
Serves the homepage, SIWES knowledge guide, and about pages.
"""
from flask import Blueprint, render_template, request, abort
from models.guide import GuideTopic
from models.organization import Organization
from models.student import StudentProfile

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Homepage showing key SIWES steps, statistics, and featured guide topics."""
    # Fetch top guide topics
    featured_guides = GuideTopic.query.filter_by(is_published=True).order_by(GuideTopic.order_num.asc()).limit(6).all()
    
    # Counts for quick statistics
    verified_orgs_count = Organization.query.filter_by(is_active=True, verification_status='Verified').count()
    guide_topics_count = GuideTopic.query.filter_by(is_published=True).count()
    
    return render_template(
        'index.html',
        featured_guides=featured_guides,
        verified_orgs_count=verified_orgs_count,
        guide_topics_count=guide_topics_count
    )


@main_bp.route('/siwes-guide')
def siwes_guide():
    """
    Comprehensive SIWES knowledge base.
    Displays all guide topics grouped by category or filtered by active topic.
    """
    category_filter = request.args.get('category', 'all')
    active_slug = request.args.get('topic')

    query = GuideTopic.query.filter_by(is_published=True)
    if category_filter != 'all':
        query = query.filter(GuideTopic.category == category_filter)
    
    all_topics = query.order_by(GuideTopic.order_num.asc()).all()
    
    # Determine which topic to display in full
    selected_topic = None
    if active_slug:
        selected_topic = GuideTopic.query.filter_by(slug=active_slug, is_published=True).first()
    elif all_topics:
        selected_topic = all_topics[0]

    # Get distinct categories for sidebar navigation
    categories = [row[0] for row in GuideTopic.query.with_entities(GuideTopic.category).distinct().all()]

    return render_template(
        'siwes_guide.html',
        topics=all_topics,
        selected_topic=selected_topic,
        categories=categories,
        active_category=category_filter
    )


@main_bp.route('/siwes-guide/<slug>')
def guide_detail(slug):
    """Direct route to a specific SIWES guide topic."""
    topic = GuideTopic.query.filter_by(slug=slug, is_published=True).first_or_404()
    categories = [row[0] for row in GuideTopic.query.with_entities(GuideTopic.category).distinct().all()]
    all_topics = GuideTopic.query.filter_by(is_published=True).order_by(GuideTopic.order_num.asc()).all()

    return render_template(
        'siwes_guide.html',
        topics=all_topics,
        selected_topic=topic,
        categories=categories,
        active_category='all'
    )


@main_bp.route('/about')
def about():
    """About page for Departmental SIWES Assistant."""
    return render_template('about.html')
