"""
Organization Model
------------------
Stores potential SIWES/IT industrial training organizations in Nigeria with
explicit verification status, sources, and engineering relevance.
"""
from datetime import datetime
from .db import db

class Organization(db.Model):
    __tablename__ = 'organizations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    
    # Location
    address = db.Column(db.String(250), nullable=True)
    state = db.Column(db.String(60), nullable=False, index=True)
    city = db.Column(db.String(80), nullable=False, index=True)
    
    # Classification & Engineering Alignment
    industry = db.Column(db.String(100), nullable=False) # e.g. Technology, Fintech, Telecom, Government
    relevance_areas = db.Column(db.String(250), nullable=False) # e.g. "Software Development, AI, Networking"
    
    # Contact & Web Information
    website = db.Column(db.String(200), nullable=True)
    contact_email = db.Column(db.String(120), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    
    # Verification & Source Integrity
    # Allowed statuses: 'Verified', 'Online Source', 'Student Submitted'
    verification_status = db.Column(db.String(50), nullable=False, default='Verified')
    source = db.Column(db.String(120), nullable=False, default='Verified Database')
    why_relevant = db.Column(db.Text, nullable=True)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    applications = db.relationship('PlacementApplication', backref='organization', lazy='dynamic', cascade='all, delete-orphan')
    saved_by = db.relationship('SavedOrganization', backref='organization', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Organization {self.name} ({self.state}) - {self.verification_status}>"

    @property
    def relevance_list(self):
        """Returns relevance areas as a clean list of strings."""
        if not self.relevance_areas:
            return []
        return [r.strip() for r in self.relevance_areas.split(',')]

    def to_dict(self):
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
            'verification_status': self.verification_status,
            'source': self.source,
            'why_relevant': self.why_relevant,
            'updated_at': self.updated_at.strftime('%Y-%m-%d') if self.updated_at else None
        }
