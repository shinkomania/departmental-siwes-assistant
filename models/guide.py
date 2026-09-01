"""
SIWES Guide Topic Model
-----------------------
Stores structured, editable guidance topics for the SIWES knowledge base.
"""
from datetime import datetime
from .db import db

class GuideTopic(db.Model):
    __tablename__ = 'guide_topics'

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False, default='General Guidance')
    order_num = db.Column(db.Integer, default=0)
    
    summary = db.Column(db.String(300), nullable=False)
    content = db.Column(db.Text, nullable=False) # In-depth guide content
    icon = db.Column(db.String(50), default='book-open') # icon identifier or emoji
    
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<GuideTopic {self.order_num}: {self.title}>"

    def to_dict(self):
        return {
            'id': self.id,
            'slug': self.slug,
            'title': self.title,
            'category': self.category,
            'order_num': self.order_num,
            'summary': self.summary,
            'content': self.content,
            'icon': self.icon,
            'updated_at': self.updated_at.strftime('%Y-%m-%d') if self.updated_at else None
        }
