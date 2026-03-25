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
    # Fresh DB read - session cache bypass karo
    db.session.expire_all()
    student = db.session.get(User, student_id)

    # --- Guard checks ---
    if not student:
        print(f"[AUTO-ENROLL] ERROR: student_id={student_id} not found")
        return 0
    if student.role != 'student':
        print(f"[AUTO-ENROLL] SKIP: id={student_id} role='{student.role}'")
        return 0

    print(f"[AUTO-ENROLL] Student: id={student.id} name='{student.full_name}'")
    print(f"[AUTO-ENROLL]   class_year='{student.class_year}' section='{student.section}' college_id='{student.college_id}'")

    # --- Profile completeness ---
    if not all([student.class_year, student.section, student.college_id]):
        print(f"[AUTO-ENROLL] SKIP: profile incomplete")
        return 0

    # --- Normalize for case-insensitive match ---
    s_year     = student.class_year.strip().lower()
    s_section  = student.section.strip().lower()
    s_college  = student.college_id.strip().lower()

    print(f"[AUTO-ENROLL] Normalized: year='{s_year}' section='{s_section}' college='{s_college}'")

    # --- Fetch fresh classrooms from DB ---
    all_classrooms = db.session.query(Classroom).all()
    print(f"[AUTO-ENROLL] Total classrooms in DB: {len(all_classrooms)}")
    for c in all_classrooms:
        print(f"[AUTO-ENROLL]   id={c.id} year='{c.class_year}' sec='{c.section}' college='{c.college_id}' subject='{c.subject}'")

    # --- Python-level case-insensitive filter ---
    matching = [
        c for c in all_classrooms
        if c.class_year.strip().lower() == s_year
        and c.section.strip().lower()   == s_section
        and c.college_id.strip().lower() == s_college
    ]

    print(f"[AUTO-ENROLL] Matching classrooms: {len(matching)}")
    if not matching:
        print(f"[AUTO-ENROLL] NO MATCH - teacher values vs student values upar dekho")
        return 0

    # --- Insert enrollments, skip duplicates ---
    enrolled_count = 0
    for classroom in matching:
        exists = db.session.query(Enrollment).filter_by(
            student_id=student.id,
            classroom_id=classroom.id
        ).first()

        if exists:
            print(f"[AUTO-ENROLL]   SKIP (duplicate): classroom_id={classroom.id}")
        else:
            db.session.add(Enrollment(
                student_id=student.id,
                classroom_id=classroom.id
            ))
            enrolled_count += 1
            print(f"[AUTO-ENROLL]   ENROLLED: student={student.id} -> classroom={classroom.id}")

    try:
        db.session.commit()
        print(f"[AUTO-ENROLL] COMMITTED: {enrolled_count} new enrollment(s)")
    except Exception as e:
        db.session.rollback()
        print(f"[AUTO-ENROLL] COMMIT ERROR: {e}")
        return 0

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
                print(f"[LOGIN] Student: id={user.id} email='{user.email}'")
                # Session expire karo taake fresh data mile
                db.session.expire_all()
                enrolled_count = auto_enroll_student(user.id)
                print(f"[LOGIN] auto_enroll result: {enrolled_count} new enrollments")
                if enrolled_count > 0:
                    flash(f'Welcome! {enrolled_count} new classroom(s) mein enroll ho gaye.', 'success')
                else:
                    flash('Welcome back!', 'success')
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
    classrooms = Classroom.query.filter_by(teacher_id=current_user.id).all()
    return render_template('teacher_templates/report.html', classrooms=classrooms, active_page='teacher_report', user=current_user)


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


@app.route('/create-classroom', methods=['POST'])
@login_required
def create_classroom():
    if current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json(silent=True) or request.form

    class_year = (data.get('class_year') or '').strip()
    section    = (data.get('section')    or '').strip()
    subject    = (data.get('subject')    or '').strip()

    # college_id: teacher ke profile se lo — form input ignore karo
    # Yeh fix karta hai mismatch bug: teacher 'sd3456' type kare, student 'SMIU001' ho
    college_id = (current_user.college_id or '').strip()

    print(f"[CREATE-CLASSROOM] teacher_id={current_user.id} | class_year='{class_year}' section='{section}' subject='{subject}' college_id='{college_id}'")

    if not all([class_year, section, subject]):
        return jsonify({'error': 'class_year, section aur subject required hain'}), 400

    if not college_id:
        return jsonify({'error': 'Aapke teacher profile mein college_id set nahi hai. Pehle profile update karein.'}), 400

    try:
        classroom = Classroom(
            teacher_id=current_user.id,
            class_year=class_year,
            section=section,
            subject=subject,
            college_id=college_id
        )
        db.session.add(classroom)
        db.session.commit()
        print(f"[CREATE-CLASSROOM] Saved: id={classroom.id} college_id='{college_id}'")

        # Matching students: case-insensitive
        db.session.expire_all()
        all_students = db.session.query(User).filter_by(role='student').all()
        matching_students = [
            s for s in all_students
            if (s.class_year  or '').strip().lower() == class_year.lower()
            and (s.section    or '').strip().lower() == section.lower()
            and (s.college_id or '').strip().lower() == college_id.lower()
        ]
        print(f"[CREATE-CLASSROOM] Matching students: {len(matching_students)}")
        for s in matching_students:
            auto_enroll_student(s.id)

    except Exception as e:
        db.session.rollback()
        print(f"[CREATE-CLASSROOM] DB ERROR: {e}")
        return jsonify({'error': 'Something went wrong'}), 500

    return jsonify({'message': 'Classroom created successfully', 'classroom_id': classroom.id, 'college_id': college_id}), 201


# ============================================
# ROUTES: STUDENT
# ============================================
@app.route('/student/index')
@login_required
def student_index():
    if current_user.role != 'student':
        return redirect(url_for('teacher_dashboard'))
    # expire_all: session cache clear karo, fresh DB read
    db.session.expire_all()
    enrollments = db.session.query(Enrollment).filter_by(student_id=current_user.id).all()
    print(f"[STUDENT-INDEX] student_id={current_user.id} | enrollments found: {len(enrollments)}")
    classroom_ids = [e.classroom_id for e in enrollments]
    print(f"[STUDENT-INDEX] classroom_ids: {classroom_ids}")
    classrooms = db.session.query(Classroom).filter(Classroom.id.in_(classroom_ids)).all()
    print(f"[STUDENT-INDEX] classrooms returned: {[c.subject for c in classrooms]}")
    return render_template('student_templates/index.html', classrooms=classrooms, active_page='student_index', user=current_user)


@app.route('/student/analysis')
@login_required
def analysis():
    if current_user.role != 'student':
        return redirect(url_for('teacher_dashboard'))
    db.session.expire_all()
    enrollments = db.session.query(Enrollment).filter_by(student_id=current_user.id).all()
    classroom_ids = [e.classroom_id for e in enrollments]
    classrooms = db.session.query(Classroom).filter(Classroom.id.in_(classroom_ids)).all()
    return render_template('student_templates/student_analysis.html', classrooms=classrooms, active_page='analysis', user=current_user)


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
@app.route('/my-classrooms', methods=['GET'])
@login_required
def my_classrooms():
    if current_user.role != 'student':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        db.session.expire_all()
        enrollments = db.session.query(Enrollment).filter_by(student_id=current_user.id).all()
        print(f"[MY-CLASSROOMS] student_id={current_user.id} | enrollments: {len(enrollments)}")

        classroom_ids = [e.classroom_id for e in enrollments]
        classrooms = db.session.query(Classroom).filter(Classroom.id.in_(classroom_ids)).all()
        print(f"[MY-CLASSROOMS] classrooms returned: {len(classrooms)}")

        result = [
            {
                'classroom_id': c.id,
                'subject':      c.subject,
                'class_year':   c.class_year,
                'section':      c.section,
                'teacher_id':   c.teacher_id,
            }
            for c in classrooms
        ]
        return jsonify(result), 200

    except Exception as e:
        print(f"[MY-CLASSROOMS] ERROR: {e}")
        return jsonify({'error': 'Something went wrong'}), 500


@app.route('/teacher-classrooms', methods=['GET'])
@login_required
def teacher_classrooms_api():
    # 1. Sirf teacher access kar sakta hai
    if current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        # 2. SQL:
        #   SELECT id, subject, class_year, section
        #   FROM classrooms
        #   WHERE teacher_id = ?
        classrooms = Classroom.query.filter_by(teacher_id=current_user.id).all()

        # 3. Koi classroom nahi to empty array
        result = [
            {
                'classroom_id': c.id,
                'subject':      c.subject,
                'class_year':   c.class_year,
                'section':      c.section,
            }
            for c in classrooms
        ]

        return jsonify(result), 200

    except Exception:
        return jsonify({'error': 'Something went wrong'}), 500


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
