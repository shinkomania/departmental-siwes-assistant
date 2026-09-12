"""
Student Profile Model
---------------------
Stores SIWES student demographic, academic, and placement preference data.
"""
from datetime import datetime
from .db import db

class StudentProfile(db.Model):
    __tablename__ = 'student_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
    db.Integer,
    db.ForeignKey('users.id'),
    nullable=True,
    unique=True
)
    programme_id = db.Column(
    db.Integer,
    db.ForeignKey('programmes.id'),
    nullable=True
)
    level = db.Column(db.String(50), nullable=True)

    siwes_session = db.Column(db.String(100), nullable=True)
    full_name = db.Column(db.String(120), nullable=False)
    matric_no = db.Column(db.String(50), unique=True, nullable=False, index=True)
    department = db.Column(db.String(120), nullable=False, default='Computer Engineering')
    faculty = db.Column(db.String(120), nullable=False, default='Faculty of Engineering')
    university = db.Column(db.String(150), nullable=False)
    
    # Location preferences
    preferred_state = db.Column(db.String(60), nullable=False)
    preferred_city = db.Column(db.String(80), nullable=False)
    
    # Career & Placement preferences
    area_of_interest = db.Column(db.String(100), nullable=False)
    skills = db.Column(db.Text, nullable=True) # Comma-separated or descriptive skills
    preferred_org_type = db.Column(db.String(100), nullable=False)
    
    # Bio / Summary for placement requests
    bio = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    saved_organizations = db.relationship('SavedOrganization', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    applications = db.relationship('PlacementApplication', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    user = db.relationship(
    'User',
    backref=db.backref('student_profile', uselist=False)
)
    programme = db.relationship(
    'Programme',
    backref=db.backref('student_profiles', lazy=True)
)
    def __repr__(self):
        return f"<StudentProfile {self.matric_no} - {self.full_name}>"

    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'matric_no': self.matric_no,
            'department': self.department,
            'faculty': self.faculty,
            'university': self.university,
            'preferred_state': self.preferred_state,
            'preferred_city': self.preferred_city,
            'area_of_interest': self.area_of_interest,
            'skills': [s.strip() for s in self.skills.split(',')] if self.skills else [],
            'preferred_org_type': self.preferred_org_type,
            'bio': self.bio,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
        }
