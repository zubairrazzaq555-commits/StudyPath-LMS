# -*- coding: utf-8 -*-
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# db object hum app.py mein initialize karenge
db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    
    # --- Role Column (Student ya Teacher) ---
    role = db.Column(db.String(20), nullable=False, default='student')
    
    grade = db.Column(db.Integer, default=11)
    group = db.Column(db.String(50), default='Pre-Engineering')
    roll_number = db.Column(db.String(50), unique=True, nullable=True)
    college = db.Column(db.String(150), nullable=True)
    
    # Subjects tracking
    active_subjects = db.Column(db.String(255), default='Chemistry')
    
    # Relationship to quiz scores
    scores = db.relationship('QuizScore', backref='student', lazy=True)

    def get_active_subjects(self):
        """Return a list of subjects from comma-separated string."""
        try:
            if not self.active_subjects:
                return ["Chemistry"]
            parts = [p.strip() for p in self.active_subjects.split(',') if p.strip()]
            return parts if parts else ["Chemistry"]
        except Exception:
            return ["Chemistry"]

    def __repr__(self):
        return f"<User {self.email} - {self.role}>"


class QuizScore(db.Model):
    __tablename__ = 'quiz_score'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<QuizScore {self.topic}: {self.score}/{self.total}>"

class Classroom(db.Model):
    __tablename__ = 'classrooms'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.String(20), unique=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    subject = db.Column(db.String(100))
    class_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    enrollments = db.relationship('ClassroomEnrollment', backref='classroom', lazy=True)
    roadmaps = db.relationship('Roadmap', backref='classroom', lazy=True)
    notes = db.relationship('Note', backref='classroom', lazy=True)

    def __repr__(self):
        return f"<Classroom {self.class_name} - {self.subject}>"


class ClassroomEnrollment(db.Model):
    __tablename__ = 'classroom_enrollments'
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Enrollment: Student {self.student_id} in Classroom {self.classroom_id}>"


class Roadmap(db.Model):
    __tablename__ = 'roadmaps'
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=True)
    subject = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Roadmap {self.topic} - {self.subject}>"


class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Note {self.title}>"


class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    questions = db.Column(db.Text, nullable=False)  # JSON format
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Quiz {self.topic} - {self.subject}>"