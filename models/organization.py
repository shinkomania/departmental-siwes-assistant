"""
Organization Model
------------------
Stores SIWES/industrial-training organizations without presenting DSA as a
certifying authority.

Important design rule:
- "Listed by a source" is not the same as "currently accepting SIWES students".
- "Currently accepting students" is not the same as "accepts this programme".
- DSA therefore stores provenance, review state, listing state, and intake state
  as separate facts.

The legacy verification_status/source/why_relevant columns are retained
temporarily so existing routes, templates, and seed data do not break while
the rest of the application is migrated to the new provenance model.
"""
from datetime import datetime

from .db import db


class Organization(db.Model):
    __tablename__ = 'organizations'

    SOURCE_TYPES = (
        'ITF Employer Directory',
        'ITF Employer Request',
        'Institution Placement Record',
        'Organization Official Source',
        'Government/Public Registry',
        'Community Contribution',
        'Other',
    )

    REVIEW_STATUSES = (
        'Pending',
        'Reviewed',
        'Needs Review',
        'Rejected',
    )

    LISTING_STATUSES = (
        'Active',
        'Inactive',
        'Unknown',
    )

    ACCEPTANCE_STATUSES = (
        'Currently Accepting',
        'Previously Accepted',
        'Potential Placement',
        'Unknown',
    )

    id = db.Column(db.Integer, primary_key=True)

    # Core identity
    name = db.Column(db.String(150), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)

    # Location
    address = db.Column(db.String(250), nullable=True)
    state = db.Column(db.String(60), nullable=False, index=True)
    city = db.Column(db.String(80), nullable=False, index=True)

    # General sector/industry classification.
    industry = db.Column(db.String(100), nullable=False, index=True)

    # Legacy/transitional broad relevance text. Structured placement-field
    # evidence will replace this later.
    relevance_areas = db.Column(db.String(250), nullable=False)

    # Contact & web information
    website = db.Column(db.String(200), nullable=True)
    contact_email = db.Column(db.String(120), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)

    # Provenance
    source_type = db.Column(
        db.String(60),
        nullable=False,
        default='Other',
        index=True,
    )
    source_name = db.Column(db.String(180), nullable=True)
    source_url = db.Column(db.String(500), nullable=True)
    source_reference = db.Column(db.String(180), nullable=True)
    source_last_checked = db.Column(db.DateTime, nullable=True)
    provenance_notes = db.Column(db.Text, nullable=True)

    # DSA internal review state — not an employer certification badge.
    review_status = db.Column(
        db.String(30),
        nullable=False,
        default='Pending',
        index=True,
    )
    reviewed_at = db.Column(db.DateTime, nullable=True)

    # Listing state is separate from current SIWES intake.
    listing_status = db.Column(
        db.String(20),
        nullable=False,
        default='Unknown',
        index=True,
    )

    # Current SIWES intake state must be supported by intake-specific evidence.
    acceptance_status = db.Column(
        db.String(30),
        nullable=False,
        default='Unknown',
        index=True,
    )
    acceptance_source_name = db.Column(db.String(180), nullable=True)
    acceptance_source_url = db.Column(db.String(500), nullable=True)
    acceptance_last_checked = db.Column(db.DateTime, nullable=True)
    acceptance_notes = db.Column(db.Text, nullable=True)

    # Preserve the original nullable behaviour of these legacy lifecycle columns
    # until a later migration explicitly changes it.
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Legacy compatibility fields. Do not use for new UI badges.
    verification_status = db.Column(
        db.String(50),
        nullable=False,
        default='Verified',
    )
    source = db.Column(
        db.String(120),
        nullable=False,
        default='Verified Database',
    )
    why_relevant = db.Column(db.Text, nullable=True)

    # Relationships
    applications = db.relationship(
        'PlacementApplication',
        backref='organization',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )
    saved_by = db.relationship(
        'SavedOrganization',
        backref='organization',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return (
            f"<Organization {self.name} ({self.state}) "
            f"source={self.source_type!r} review={self.review_status!r}>"
        )

    @property
    def relevance_list(self):
        """Return transitional relevance areas as a clean list."""
        if not self.relevance_areas:
            return []
        return [
            item.strip()
            for item in self.relevance_areas.split(',')
            if item.strip()
        ]

    @property
    def source_display(self):
        """Human-friendly provenance label for the UI."""
        return self.source_name or self.source_type or 'Source not recorded'

    @property
    def has_current_intake_evidence(self):
        """
        True only when the record explicitly says the organization is currently
        accepting students and DSA has an intake evidence source.
        """
        return (
            self.acceptance_status == 'Currently Accepting'
            and bool(self.acceptance_source_name or self.acceptance_source_url)
        )

    def to_dict(self):
        """
        Public-safe dictionary representation.

        Deprecated verification badge fields are deliberately omitted so new
        API/UI code naturally moves toward provenance-based presentation.
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'address': self.address,
            'state': self.state,
            'city': self.city,
            'industry': self.industry,
            'relevance_areas': self.relevance_list,
            'website': self.website,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'source_type': self.source_type,
            'source_name': self.source_name,
            'source_url': self.source_url,
            'source_reference': self.source_reference,
            'source_last_checked': (
                self.source_last_checked.strftime('%Y-%m-%d')
                if self.source_last_checked else None
            ),
            'review_status': self.review_status,
            'reviewed_at': (
                self.reviewed_at.strftime('%Y-%m-%d')
                if self.reviewed_at else None
            ),
            'listing_status': self.listing_status,
            'acceptance_status': self.acceptance_status,
            'acceptance_source_name': self.acceptance_source_name,
            'acceptance_source_url': self.acceptance_source_url,
            'acceptance_last_checked': (
                self.acceptance_last_checked.strftime('%Y-%m-%d')
                if self.acceptance_last_checked else None
            ),
            'is_active': self.is_active,
            'updated_at': (
                self.updated_at.strftime('%Y-%m-%d')
                if self.updated_at else None
            ),
        }
