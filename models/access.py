from datetime import datetime
from .db import db


# Many-to-many relationship between roles and permissions
role_permissions = db.Table(
    'role_permissions',

    db.Column(
        'role_id',
        db.Integer,
        db.ForeignKey('roles.id'),
        primary_key=True
    ),

    db.Column(
        'permission_id',
        db.Integer,
        db.ForeignKey('permissions.id'),
        primary_key=True
    )
)


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False,
        unique=True
    )

    slug = db.Column(
        db.String(100),
        nullable=False,
        unique=True,
        index=True
    )

    description = db.Column(db.Text)

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    permissions = db.relationship(
        'Permission',
        secondary=role_permissions,
        backref=db.backref('roles', lazy='dynamic'),
        lazy='dynamic'
    )


class Permission(db.Model):
    __tablename__ = 'permissions'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(150),
        nullable=False
    )

    slug = db.Column(
        db.String(150),
        nullable=False,
        unique=True,
        index=True
    )

    description = db.Column(db.Text)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class UserRoleAssignment(db.Model):
    __tablename__ = 'user_role_assignments'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )

    role_id = db.Column(
        db.Integer,
        db.ForeignKey('roles.id'),
        nullable=False
    )

    institution_id = db.Column(
        db.Integer,
        db.ForeignKey('institutions.id'),
        nullable=True
    )

    department_id = db.Column(
        db.Integer,
        db.ForeignKey('departments.id'),
        nullable=True
    )

    programme_id = db.Column(
        db.Integer,
        db.ForeignKey('programmes.id'),
        nullable=True
    )

    status = db.Column(
        db.String(50),
        nullable=False,
        default='Pending'
    )

    academic_session = db.Column(
        db.String(100),
        nullable=True
    )

    approved_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=True
    )

    approved_at = db.Column(
        db.DateTime,
        nullable=True
    )

    expires_at = db.Column(
        db.DateTime,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    user = db.relationship(
        'User',
        foreign_keys=[user_id],
        backref=db.backref('role_assignments', lazy='dynamic')
    )

    approved_by = db.relationship(
        'User',
        foreign_keys=[approved_by_user_id]
    )

    role = db.relationship(
        'Role',
        backref=db.backref('assignments', lazy='dynamic')
    )

    institution = db.relationship('Institution')
    department = db.relationship('Department')
    programme = db.relationship('Programme')