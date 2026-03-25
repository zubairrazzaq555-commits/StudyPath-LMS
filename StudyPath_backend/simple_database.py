# -*- coding: utf-8 -*-
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# ============================================
# TABLE 1: USERS (Teachers + Students)
# ============================================
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'teacher' or 'student'
    
    # Student-specific fields
    roll_number = db.Column(db.String(50), nullable=True)
    class_year = db.Column(db.String(20), nullable=True)  # '1st year' or '2nd year'
    section = db.Column(db.String(10), nullable=True)  # 'A', 'B', etc
    college_id = db.Column(db.String(50), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    created_classrooms = db.relationship('Classroom', backref='teacher', lazy=True, foreign_keys='Classroom.teacher_id')
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)

    def __repr__(self):
        return f"<User {self.email} - {self.role}>"


# ============================================
# TABLE 2: CLASSROOMS
# ============================================
class Classroom(db.Model):
    __tablename__ = 'classrooms'
    
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    class_year = db.Column(db.String(20), nullable=False)  # '1st year' or '2nd year'
    section = db.Column(db.String(10), nullable=False)  # 'A', 'B', etc
    subject = db.Column(db.String(100), nullable=False)  # 'Physics', 'Math', etc
    college_id = db.Column(db.String(50), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='classroom', lazy=True, cascade='all, delete-orphan')
    roadmaps    = db.relationship('Roadmap', backref='classroom', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Classroom {self.class_year} {self.section} - {self.subject}>"


# ============================================
# TABLE 3: ENROLLMENTS (Student ↔ Classroom)
# ============================================
class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint: student can't enroll in same classroom twice
    __table_args__ = (db.UniqueConstraint('student_id', 'classroom_id', name='unique_enrollment'),)

    def __repr__(self):
        return f"<Enrollment Student:{self.student_id} → Classroom:{self.classroom_id}>"


# ============================================
# INDEX: Fast auto-enrollment matching
# ============================================
from sqlalchemy import Index
Idx_classroom_match = Index(
    'idx_classroom_match',
    Classroom.class_year,
    Classroom.section,
    Classroom.college_id
)


# ============================================
# TABLE 4: ROADMAP (Teacher creates study plan per classroom)
# ============================================
class Roadmap(db.Model):
    __tablename__ = 'roadmaps'

    id           = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    title        = db.Column(db.String(200), nullable=False)   # e.g. "Physics Chapter 1 Plan"
    description  = db.Column(db.Text, nullable=True)
    start_date   = db.Column(db.Date, nullable=True)
    end_date     = db.Column(db.Date, nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    # One roadmap → many items
    items = db.relationship('RoadmapItem', backref='roadmap', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Roadmap '{self.title}' classroom={self.classroom_id}>"


# ============================================
# TABLE 5: ROADMAP ITEMS (Daily tasks inside a roadmap)
# ============================================
class RoadmapItem(db.Model):
    __tablename__ = 'roadmap_items'

    id             = db.Column(db.Integer, primary_key=True)
    roadmap_id     = db.Column(db.Integer, db.ForeignKey('roadmaps.id'), nullable=False)
    day_number     = db.Column(db.Integer, nullable=False)       # Day 1, Day 2 ...
    topic          = db.Column(db.String(200), nullable=False)
    description    = db.Column(db.Text, nullable=True)
    estimated_time = db.Column(db.String(50), nullable=True)     # e.g. "2 hours"

    def __repr__(self):
        return f"<RoadmapItem Day {self.day_number}: '{self.topic}'>"
