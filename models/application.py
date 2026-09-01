"""
Placement Application and Bookmark Models
------------------------------------------
Allows students to track their SIWES application pipeline and save organizations.
"""
from datetime import datetime
from .db import db

class SavedOrganization(db.Model):
    __tablename__ = 'saved_organizations'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id', ondelete='CASCADE'), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('student_id', 'organization_id', name='uq_student_saved_org'),
    )

    def __repr__(self):
        return f"<SavedOrg Student:{self.student_id} Org:{self.organization_id}>"


class PlacementApplication(db.Model):
    __tablename__ = 'placement_applications'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id', ondelete='CASCADE'), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    
    # Status options: Interested, Contacted, Application Submitted, Interview, Accepted, Rejected
    status = db.Column(db.String(50), nullable=False, default='Interested')
    notes = db.Column(db.Text, nullable=True) # e.g. "Submitted SIWES letter to HR, waiting for response."
    
    applied_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('student_id', 'organization_id', name='uq_student_org_app'),
    )

    # Valid status list for validation
    STATUS_CHOICES = [
        'Interested',
        'Contacted',
        'Application Submitted',
        'Interview',
        'Accepted',
        'Rejected'
    ]

    def __repr__(self):
        return f"<Application Student:{self.student_id} Org:{self.organization_id} Status:{self.status}>"

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'organization_id': self.organization_id,
            'organization_name': self.organization.name if self.organization else 'Unknown',
            'status': self.status,
            'notes': self.notes,
            'applied_date': self.applied_date.strftime('%Y-%m-%d') if self.applied_date else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None
        }
