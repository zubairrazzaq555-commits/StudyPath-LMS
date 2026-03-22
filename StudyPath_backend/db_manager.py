# -*- coding: utf-8 -*-
import os
from flask_sqlalchemy import SQLAlchemy

# Hum yahan db object nahi banayenge, sirf functions likhenge 
# jo app context ke andar chalenge.

def save_score_to_db(db, QuizScore, user_id, topic, score, total):
    """Bache ka quiz score save karne ke liye"""
    try:
        new_score = QuizScore(
            user_id=user_id,
            topic=topic,
            score=score,
            total=total
        )
        db.session.add(new_score)
        db.session.commit()
        return True
    except Exception as e:
        print(f"Database Error: {e}")
        db.session.rollback()
        return False

def get_student_stats(QuizScore, user_id):
    """Bache ki saari performance history nikalne ke liye"""
    return QuizScore.query.filter_by(user_id=user_id).order_by(QuizScore.date.desc()).all()

def update_user_profile(db, User, user_id, data):
    """User ki details update karne ke liye"""
    user = User.query.get(user_id)
    if user:
        user.grade = data.get('grade', user.grade)
        user.college = data.get('college', user.college)
        user.group = data.get('group', user.group)
        db.session.commit()
        return True
    return False