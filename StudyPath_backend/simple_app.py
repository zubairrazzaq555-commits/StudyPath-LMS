# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from simple_database import db, User, Classroom, Enrollment

# ============================================
# APP SETUP
# ============================================
template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'studypath_app', 'app_templates')
app = Flask(__name__, template_folder=template_dir)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///simple_lms.db'
app.config['SECRET_KEY'] = 'simple_lms_secret_key'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ============================================
# HELPER FUNCTION: AUTO-ENROLL STUDENT
# ============================================
def auto_enroll_student(student_id):
    """
    Jab student login kare, uski class/section/college se
    matching classrooms dhundho aur enroll karo.

    SQL (equivalent):
        SELECT * FROM classrooms
        WHERE class_year = student.class_year
          AND section    = student.section
          AND college_id = student.college_id;

    NOTE (future): Agar 1000+ students ho to loop ki jagah
    bulk insert use karna better hoga:
        db.session.bulk_save_objects([...])
    """
    student = User.query.get(student_id)
    if not student or student.role != 'student':
        return 0

    # Edge case: profile incomplete ho to enroll mat karo
    if not all([student.class_year, student.section, student.college_id]):
        return 0

    # Step 1: Matching classrooms dhundho
    matching_classrooms = Classroom.query.filter_by(
        class_year=student.class_year,
        section=student.section,
        college_id=student.college_id
    ).all()

    # Step 2: Har classroom ke liye enroll karo (duplicate skip)
    enrolled_count = 0
    for classroom in matching_classrooms:
        already_enrolled = Enrollment.query.filter_by(
            student_id=student.id,
            classroom_id=classroom.id
        ).first()

        if not already_enrolled:
            db.session.add(Enrollment(
                student_id=student.id,
                classroom_id=classroom.id
            ))
            enrolled_count += 1

    db.session.commit()
    return enrolled_count


# ============================================
# ROUTES: AUTHENTICATION
# ============================================
@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.password == password:
            login_user(user)
            if user.role == 'student':
                enrolled_count = auto_enroll_student(user.id)
                if enrolled_count > 0:
                    flash(f'Logged in! {enrolled_count} new classrooms mein enroll ho gaye.', 'success')
                else:
                    flash('Logged in! (Profile incomplete hone ki wajah se auto-enroll nahi hua)', 'warning')
                return redirect(url_for('student_index'))
            else:
                flash('Welcome back, Teacher!', 'success')
                return redirect(url_for('teacher_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        role = request.form.get('role', 'student')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('signup'))
        
        user = User(email=email, password=password, full_name=full_name, role=role)
        
        if role == 'student':
            user.roll_number = request.form.get('roll_number')
            user.class_year = request.form.get('class_year')
            user.section = request.form.get('section')
            user.college_id = request.form.get('college_id')
        
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ============================================
# ROUTES: TEACHER
# ============================================
@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        flash('Access denied. Teacher area only.', 'danger')
        return redirect(url_for('login'))
    classrooms = Classroom.query.filter_by(teacher_id=current_user.id).all()
    return render_template('teacher_templates/dashboard.html', classrooms=classrooms, active_page='teacher_dashboard', user=current_user)


@app.route('/teacher/classrooms')
@login_required
def teacher_classrooms():
    if current_user.role != 'teacher':
        flash('Access denied. Teacher area only.', 'danger')
        return redirect(url_for('login'))
    classrooms = Classroom.query.filter_by(teacher_id=current_user.id).all()
    return render_template('teacher_templates/classrooms.html', classrooms=classrooms, active_page='teacher_classrooms', user=current_user)


@app.route('/teacher/curriculum')
@login_required
def teacher_curriculum():
    if current_user.role != 'teacher':
        flash('Access denied. Teacher area only.', 'danger')
        return redirect(url_for('login'))
    return render_template('teacher_templates/curriculum.html', active_page='teacher_curriculum', user=current_user)


@app.route('/teacher/report')
@login_required
def teacher_report():
    if current_user.role != 'teacher':
        flash('Access denied. Teacher area only.', 'danger')
        return redirect(url_for('login'))
    return render_template('teacher_templates/report.html', active_page='teacher_report', user=current_user)


@app.route('/teacher/profile')
@login_required
def teacher_profile():
    if current_user.role != 'teacher':
        flash('Access denied. Teacher area only.', 'danger')
        return redirect(url_for('login'))
    return render_template('teacher_templates/teacher_profile.html', active_page='teacher_profile', user=current_user)


@app.route('/teacher/roadmap', defaults={'subject': 'Physics'})
@app.route('/teacher/roadmap/<subject>')
@login_required
def teacher_roadmap(subject):
    if current_user.role != 'teacher':
        flash('Access denied. Teacher area only.', 'danger')
        return redirect(url_for('login'))
    return render_template('teacher_templates/roadmap_classroom.html', subject=subject, active_page='teacher_dashboard', user=current_user)


@app.route('/teacher/student-progress')
@login_required
def teacher_student_progress():
    if current_user.role != 'teacher':
        flash('Access denied. Teacher area only.', 'danger')
        return redirect(url_for('login'))
    return render_template('teacher_templates/student_progress_classroom.html', active_page='teacher_student_progress', user=current_user)


@app.route('/teacher/knowledge-dashboard')
@login_required
def teacher_knowledge_dashboard():
    if current_user.role != 'teacher':
        flash('Access denied. Teacher area only.', 'danger')
        return redirect(url_for('login'))
    return render_template('teacher_templates/knowledge_classroom_dashboard.html', active_page='teacher_knowledge_dashboard', user=current_user)


@app.route('/teacher/quiz-factory')
@login_required
def teacher_quiz_factory():
    if current_user.role != 'teacher':
        flash('Access denied. Teacher area only.', 'danger')
        return redirect(url_for('login'))
    return render_template('teacher_templates/quiz_classroom.html', active_page='teacher_quiz_factory', user=current_user)


@app.route('/teacher/create-classroom', methods=['POST'])
@login_required
def create_classroom():
    if current_user.role != 'teacher':
        return jsonify({'error': 'Only teachers can create classrooms'}), 403
    
    data = request.form
    classroom = Classroom(
        teacher_id=current_user.id,
        class_year=data.get('class_year'),
        section=data.get('section'),
        subject=data.get('subject'),
        college_id=data.get('college_id')
    )
    
    db.session.add(classroom)
    db.session.commit()
    
    matching_students = User.query.filter_by(
        role='student',
        class_year=classroom.class_year,
        section=classroom.section,
        college_id=classroom.college_id
    ).all()
    
    for student in matching_students:
        # Duplicate check (agar student pehle se enrolled ho)
        already_enrolled = Enrollment.query.filter_by(
            student_id=student.id,
            classroom_id=classroom.id
        ).first()
        if not already_enrolled:
            db.session.add(Enrollment(student_id=student.id, classroom_id=classroom.id))

    db.session.commit()
    flash(f'Classroom created! {len(matching_students)} students auto-enrolled.', 'success')
    return redirect(url_for('teacher_dashboard'))


# ============================================
# ROUTES: STUDENT
# ============================================
@app.route('/student/index')
@login_required
def student_index():
    if current_user.role != 'student':
        return redirect(url_for('teacher_dashboard'))
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    classrooms = [e.classroom for e in enrollments]
    return render_template('student_templates/index.html', classrooms=classrooms, active_page='student_index', user=current_user)


@app.route('/student/analysis')
@login_required
def analysis():
    if current_user.role != 'student':
        return redirect(url_for('teacher_dashboard'))
    return render_template('student_templates/student_analysis.html', active_page='analysis', user=current_user)


@app.route('/student/inbox')
@login_required
def inbox():
    if current_user.role != 'student':
        return redirect(url_for('teacher_dashboard'))
    return render_template('student_templates/inbox.html', active_page='inbox', user=current_user)


@app.route('/student/profile')
@login_required
def profile():
    if current_user.role != 'student':
        return redirect(url_for('teacher_dashboard'))
    return render_template('student_templates/profile.html', active_page='profile', user=current_user)


@app.route('/student/classroom/<subject>')
@login_required
def classroom_dashboard(subject):
    if current_user.role != 'student':
        return redirect(url_for('teacher_dashboard'))
    return render_template('student_templates/classroom_dashboard.html', subject=subject, active_page='student_index', user=current_user)


@app.route('/ai-tutor/<subject>')
@login_required
def ai_tutor(subject):
    if current_user.role != 'student':
        return redirect(url_for('teacher_dashboard'))
    return render_template('student_templates/AI_tutor.html', subject=subject, active_page='ai_tutor', user=current_user)


# ============================================
# UTILITY ROUTES
# ============================================
@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    try:
        data = request.form
        current_user.full_name = data.get('full_name', current_user.full_name)
        current_user.email = data.get('email', current_user.email)
        
        if current_user.role == 'student':
            current_user.roll_number = data.get('roll_number', current_user.roll_number)
            current_user.class_year = data.get('class_year', current_user.class_year)
            current_user.section = data.get('section', current_user.section)
            current_user.college_id = data.get('college_id', current_user.college_id)
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating profile: {str(e)}', 'danger')
    
    if current_user.role == 'teacher':
        return redirect(url_for('teacher_profile'))
    return redirect(url_for('profile'))


@app.route('/forgot-password')
def forgot_password():
    return render_template('forgot_password.html')


@app.route('/reset-password')
def reset_password():
    return render_template('reset_password.html')


@app.route('/verify-otp')
def verify_otp():
    return render_template('verify_otp.html')


@app.route('/create-account')
def create_account():
    return render_template('create_account.html')


# ============================================
# API ROUTES
# ============================================
@app.route('/api/my-classrooms')
@login_required
def api_my_classrooms():
    if current_user.role == 'teacher':
        classrooms = Classroom.query.filter_by(teacher_id=current_user.id).all()
    else:
        enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
        classrooms = [e.classroom for e in enrollments]
    
    return jsonify({
        'classrooms': [{'id': c.id, 'subject': c.subject, 'class_year': c.class_year, 'section': c.section, 'college_id': c.college_id} for c in classrooms]
    })


# ============================================
# MAIN
# ============================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        if not User.query.filter_by(email='zubairahmad234ph@gmail.com').first():
            teacher = User(email='zubairahmad234ph@gmail.com', password='teacher123', full_name='Zubair Ahmad', role='teacher')
            db.session.add(teacher)
            print("✅ Teacher: zubairahmad234ph@gmail.com / teacher123")
        
        if not User.query.filter_by(email='zubairazam555@gmail.com').first():
            student = User(email='zubairazam555@gmail.com', password='student123', full_name='Zubair Azam', role='student', roll_number='2024-CS-001', class_year='1st year', section='A', college_id='SMIU001')
            db.session.add(student)
            print("✅ Student: zubairazam555@gmail.com / student123")
        
        db.session.commit()
    
    print("\n🎯 TEST ACCOUNTS:")
    print("📚 Teacher: zubairahmad234ph@gmail.com / teacher123")
    print("🎓 Student: zubairazam555@gmail.com / student123")
    print("\n🚀 Server: http://127.0.0.1:5000\n")
    app.run(debug=True, port=5000)
