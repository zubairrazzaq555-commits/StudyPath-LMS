# -*- coding: utf-8 -*-
import os
import json
import warnings
from datetime import datetime

from groq import Groq
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

# --- DATABASE MODELS IMPORT ---
try:
    from database import db, User, QuizScore, Classroom, Roadmap, ClassroomEnrollment, Note, Quiz
except ImportError:
    print("[!] Error: database.py nahi mili! Models load nahi ho sakay.")
    db = None
    User = None
    QuizScore = None
    Classroom = None
    Roadmap = None
    ClassroomEnrollment = None
    Note = None
    Quiz = None

# 1. Load Environment Variables
load_dotenv()

# 2. Path Configuration
base_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(base_dir)
template_base = os.path.join(project_root, "studypath_app", "app_templates")
static_base = os.path.join(project_root, "studypath_app", "static")

# Create template paths as fallback if main path doesn't exist
if not os.path.exists(template_base):
    template_base = os.path.join(base_dir, "app_templates")
    static_base = os.path.join(base_dir, "static")

app = Flask(__name__, 
            template_folder=template_base, 
            static_folder=static_base)

# 3. Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'database.db')
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "sir_ahmed_786")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 4. Initialize Database
if db:
    db.init_app(app)

# 5. Login Manager Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Please login to access this page."

@login_manager.user_loader
def load_user(user_id):
    if User:
        return User.query.get(int(user_id))
    return None

# 6. Groq Setup (Llama-3)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = None

if GROQ_API_KEY:
    try:
        client = Groq(api_key=GROQ_API_KEY)
        print("[OK] Groq API initialized (Llama-3 Power)")
    except Exception as e:
        print(f"[!] Groq API initialization failed: {e}")
else:
    print("[!] No GROQ_API_KEY found - AI will not work")

# 7. Import AI Engine (Fix for Groq + ChromaDB)
try:
    from engine import get_ai_response as engine_ai_response, generate_roadmap, generate_quiz
    print("[OK] AI Engine loaded successfully")
except ImportError as e:
    print(f"[!] Error loading engine: {e}")
    engine_ai_response = None
    generate_roadmap = None
    generate_quiz = None

# 8. AI Helper Function (Updated with Groq + Local Indexing)
def get_ai_response(prompt, subject=None):
    """Get AI response using Groq + Local Indexing"""
    if not client:
        return "System Error: Groq API key missing! Please contact teacher."
    
    # Use engine if available
    if engine_ai_response:
        try:
            return engine_ai_response(prompt, subject)
        except Exception as e:
            print(f"Engine error: {e}, falling back to direct Groq")
    
    # Fallback to direct Groq without context
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are StudyPath AI, a helpful tutor for Sindh Board students."},
                {"role": "user", "content": prompt},
            ],
            model="llama3-8b-8192",
            temperature=0.5,
            max_tokens=1024,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Groq AI Error: {e}")
        return "Beta, AI service temporarily unavailable. Please try again in a few minutes."

# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.route('/')
def home():
    """Root route - hamesha login page dikhao"""
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login with role-based redirection"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        selected_role = request.form.get('role', 'student')
        
        print(f"--- Login Attempt ---")
        print(f"Email entered: {email}")
        print(f"Selected role: {selected_role}")
        
        if not User:
            flash("Database error: User model not loaded", "danger")
            return render_template('login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            print(f"User found in DB: {user.full_name} (Role: {user.role})")
            
            # Check if selected role matches user's actual role
            if user.role != selected_role:
                flash(f"This email is registered as a {user.role}, not a {selected_role}. Please select the correct role.", "warning")
                return render_template('login.html')
            
            if user.password == password:
                print("[OK] Password matched!")
                login_user(user)
                flash(f"Welcome back, {user.full_name}!", "success")
                
                # Role-based redirect
                if user.role == 'teacher':
                    return redirect(url_for('teacher_dashboard'))
                return redirect(url_for('student_index'))
            else:
                print("[X] Password mismatch!")
                flash("Invalid password. Please try again.", "danger")
        else:
            print("[X] User not found in database!")
            flash("This email is not registered. Please create an account first.", "warning")
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle user registration with role selection"""
        
    if request.method == 'POST':
        if not User:
            flash("Database error: Cannot create account", "danger")
            return redirect(url_for('signup'))
        
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        grade = request.form.get('grade', 11)
        group = request.form.get('group', 'Pre-Engineering')
        role = request.form.get('role', 'student')
        
        if not all([full_name, email, password]):
            flash("All fields are required!", "danger")
            return redirect(url_for('signup'))
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already exists! Please login.", "danger")
            return redirect(url_for('login'))
        
        try:
            new_user = User(
                full_name=full_name,
                email=email,
                password=password,
                grade=int(grade),
                group=group,
                role=role,
                active_subjects='Chemistry, Physics, Mathematics'
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            print(f"[OK] New user created: {full_name} (Role: {role})")
            flash(f"Account created successfully! Please login as {role}.", "success")
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating user: {e}")
            flash("Error creating account. Please try again.", "danger")
            
    return render_template('create_account.html')

@app.route('/logout')
@login_required
def logout():
    """Log out current user"""
    logout_user()
    flash("Logged out successfully!", "success")
    return redirect(url_for('login'))

# ==========================================
# STUDENT ROUTES
# ==========================================

@app.route('/index')
@login_required
def student_index():
    """Student dashboard/home page"""
    if current_user.role == 'teacher':
        flash("Teachers cannot access student dashboard.", "warning")
        return redirect(url_for('teacher_dashboard'))
    
    user_group = current_user.group or "Pre-Engineering"
    user_year = current_user.grade or 11
    
    subject_mapping = {
        "Pre-Medical": {
            11: ["Biology", "Physics", "Chemistry", "English", "Urdu"],
            12: ["Biology", "Physics", "Chemistry", "English", "Urdu"]
        },
        "Pre-Engineering": {
            11: ["Mathematics", "Physics", "Chemistry", "English", "Urdu"],
            12: ["Mathematics", "Physics", "Chemistry", "English", "Urdu"]
        },
        "Computer Science": {
            11: ["Computer Science", "Mathematics", "Physics", "English", "Urdu"],
            12: ["Computer Science", "Mathematics", "Physics", "English", "Urdu"]
        }
    }
    
    my_books = subject_mapping.get(user_group, {}).get(user_year, ["English", "Urdu", "Mathematics"])
    
    return render_template('student_templates/index.html', 
                         user=current_user, 
                         books=my_books,
                         active_page='student_index')

@app.route('/classroom/<subject>')
@login_required
def classroom_dashboard(subject):
    """Student classroom view for specific subject"""
    if current_user.role == 'teacher':
        flash("Teachers cannot access student classrooms.", "warning")
        return redirect(url_for('teacher_dashboard'))
    
    return render_template('student_templates/classroom_dashboard.html', 
                         subject=subject, 
                         user=current_user,
                         active_page='classroom_dashboard')

@app.route('/ai-tutor/<subject>')
@login_required
def ai_tutor(subject):
    """AI tutor interface for students"""
    if current_user.role == 'teacher':
        flash("Teachers cannot access student AI tutor.", "warning")
        return redirect(url_for('teacher_dashboard'))
    
    return render_template('student_templates/AI_tutor.html', 
                         subject=subject, 
                         user=current_user,
                         active_page='ai_tutor')

@app.route('/analysis')
@login_required
def analysis():
    """Student performance analysis"""
    if current_user.role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    
    scores = []
    if QuizScore:
        scores = QuizScore.query.filter_by(user_id=current_user.id).all()
    
    return render_template('student_templates/student_analysis.html', 
                         scores=scores, 
                         user=current_user,
                         active_page='analysis')

@app.route('/inbox')
@login_required
def inbox():
    """Student inbox/messages"""
    if current_user.role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    return render_template('student_templates/inbox.html', 
                         user=current_user,
                         active_page='inbox')

@app.route('/profile')
@login_required
def profile():
    """Student profile page"""
    if current_user.role == 'teacher':
        return redirect(url_for('teacher_profile'))
    return render_template('student_templates/profile.html', 
                         user=current_user,
                         group=current_user.group or 'Pre-Engineering',
                         year=current_user.grade or 11,
                         active_page='profile')

@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    try:
        data = request.form
        current_user.full_name = data.get('full_name', current_user.full_name)
        current_user.email = data.get('email', current_user.email)
        current_user.roll_number = data.get('roll_number', current_user.roll_number)
        current_user.college = data.get('college', current_user.college)
        
        if current_user.role == 'student':
            current_user.grade = int(data.get('grade', current_user.grade))
            current_user.group = data.get('group', current_user.group)
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating profile: {str(e)}', 'danger')
    
    if current_user.role == 'teacher':
        return redirect(url_for('teacher_profile'))
    return redirect(url_for('profile'))

@app.route('/settings')
@login_required
def settings():
    """Student settings page"""
    if current_user.role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    return render_template('student_templates/settings.html', 
                         user=current_user,
                         active_page='settings')

@app.route('/quiz/<subject>')
@login_required
def quiz(subject):
    """Student quiz page for specific subject"""
    if current_user.role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    return render_template('student_templates/quiz.html', 
                         subject=subject,
                         user=current_user,
                         active_page='quiz')

@app.route('/quiz-result/<subject>')
@login_required
def quiz_result(subject):
    """Student quiz result page"""
    if current_user.role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    return render_template('student_templates/quiz_result.html', 
                         subject=subject,
                         user=current_user,
                         active_page='quiz_result')

# ==========================================
# TEACHER ROUTES (FIXED WITH active_page)
# ==========================================

@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    """Teacher main dashboard"""
    if current_user.role != 'teacher':
        flash("Access denied. Teacher area only.", "danger")
        return redirect(url_for('student_index'))
    
    return render_template('teacher_templates/dashboard.html', 
                         user=current_user, 
                         active_page='teacher_dashboard')

@app.route('/teacher/classrooms')
@login_required
def teacher_classrooms():
    """Teacher classrooms management"""
    if current_user.role != 'teacher':
        return redirect(url_for('student_index'))
    
    return render_template('teacher_templates/classrooms.html', 
                         user=current_user,
                         active_page='teacher_classrooms')

@app.route('/teacher/curriculum')
@login_required
def teacher_curriculum():
    """Teacher curriculum management"""
    if current_user.role != 'teacher':
        return redirect(url_for('student_index'))
    
    return render_template('teacher_templates/curriculum.html', 
                         user=current_user,
                         active_page='teacher_curriculum')

@app.route('/teacher/report')
@login_required
def teacher_report():
    """Teacher reports and analytics"""
    if current_user.role != 'teacher':
        return redirect(url_for('student_index'))
    
    return render_template('teacher_templates/report.html', 
                         user=current_user,
                         active_page='teacher_report')

@app.route('/teacher/profile')
@login_required
def teacher_profile():
    """Teacher profile page"""
    if current_user.role != 'teacher':
        return redirect(url_for('student_index'))
    
    return render_template('teacher_templates/teacher_profile.html', 
                         user=current_user,
                         active_page='teacher_profile')

@app.route('/teacher/knowledge-dashboard')
@login_required
def teacher_knowledge_dashboard():
    """Teacher knowledge base dashboard"""
    if current_user.role != 'teacher':
        return redirect(url_for('student_index'))
    
    return render_template('teacher_templates/knowledge_classroom_dashboard.html', 
                         user=current_user,
                         active_page='teacher_knowledge_dashboard')

@app.route('/teacher/quiz-factory')
@login_required
def teacher_quiz_factory():
    """Teacher quiz creation interface"""
    if current_user.role != 'teacher':
        return redirect(url_for('student_index'))
    
    return render_template('teacher_templates/quiz_classroom.html', 
                         user=current_user,
                         active_page='teacher_quiz_factory')

@app.route('/teacher/roadmap')
@login_required
def teacher_roadmap():
    """Teacher curriculum roadmap"""
    if current_user.role != 'teacher':
        return redirect(url_for('student_index'))
    
    # Get subject from query parameter
    subject = request.args.get('subject', 'Physics')
    
    # Get all roadmaps created by this teacher for this subject
    roadmaps = []
    if Roadmap:
        roadmaps = Roadmap.query.filter_by(created_by=current_user.id, subject=subject).order_by(Roadmap.created_at.desc()).all()
    
    return render_template('teacher_templates/roadmap_classroom.html', 
                         user=current_user,
                         roadmaps=roadmaps,
                         subject=subject,
                         active_page='teacher_roadmap')

@app.route('/create-roadmap', methods=['POST'])
@login_required
def create_roadmap():
    """Generate AI roadmap for entire subject with timeline"""
    if current_user.role != 'teacher':
        return jsonify({"error": "Only teachers can create roadmaps"}), 403
    
    try:
        data = request.json
        subject = data.get('subject')
        grade = data.get('grade', '11')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not subject or not start_date or not end_date:
            return jsonify({"error": "Subject, grade and dates required"}), 400
        
        print(f"Creating roadmap for: {grade}th {subject} ({start_date} to {end_date})")
        
        # Delete any existing roadmaps for this subject by this teacher
        if Roadmap:
            existing_roadmaps = Roadmap.query.filter_by(subject=subject, created_by=current_user.id).all()
            for rm in existing_roadmaps:
                db.session.delete(rm)
            db.session.commit()
            print(f"Deleted {len(existing_roadmaps)} old roadmaps")
        
        # Try to generate full course roadmap using AI
        roadmap_data = None
        try:
            if generate_roadmap:
                print("Attempting AI generation for full course...")
                # Pass grade with subject to get correct indexed data
                roadmap_data = generate_roadmap(f"Complete {grade}th class {subject} course syllabus", f"{grade}th {subject}")
                print("AI generation successful!")
        except Exception as ai_error:
            print(f"AI generation failed: {ai_error}")
            roadmap_data = None
        
        # If AI failed, use fallback with actual Sindh Board chapters
        if not roadmap_data:
            print("Using fallback with actual chapters")
            
            # Sindh Board 11th/12th Physics chapters
            physics_11_chapters = [
                "Physical Quantities and Measurement",
                "Kinematics",
                "Dynamics",
                "Work and Energy",
                "Circular Motion",
                "Fluid Dynamics",
                "Oscillations",
                "Waves",
                "Physical Optics",
                "Optical Instruments",
                "Heat and Thermodynamics",
                "Electrostatics",
                "Current Electricity",
                "Electromagnetism"
            ]
            
            physics_12_chapters = [
                "Electrostatics",
                "Current Electricity",
                "Electromagnetism",
                "Electromagnetic Induction",
                "Alternating Current",
                "Physics of Solids",
                "Electronics",
                "Dawn of Modern Physics",
                "Atomic Spectra",
                "Nuclear Physics"
            ]
            
            # Select chapters based on grade
            if grade == '11':
                chapters = physics_11_chapters
            else:
                chapters = physics_12_chapters
            
            # Calculate duration per chapter
            from datetime import datetime
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            total_days = (end - start).days
            days_per_chapter = total_days // len(chapters)
            
            # Create modules from chapters
            modules = []
            for i, chapter in enumerate(chapters, 1):
                modules.append({
                    "module_number": i,
                    "title": chapter,
                    "topics": ["Theory", "Numerical Problems", "Practice Questions"],
                    "duration": f"{days_per_chapter} days",
                    "difficulty": "Medium" if i <= len(chapters)//2 else "Hard"
                })
            
            roadmap_data = {
                "title": f"{grade}th Class {subject} Complete Course",
                "start_date": start_date,
                "end_date": end_date,
                "total_chapters": len(chapters),
                "duration": f"{total_days} days",
                "modules": modules,
                "assessments": ["Weekly Tests", "Monthly Exams", "Mid-term", "Final Board Exam"],
                "resources": ["Sindh Board Textbook", "Reference Books", "Past Papers"]
            }
        
        # Save to database
        if Roadmap and db:
            print("Saving to database...")
            new_roadmap = Roadmap(
                subject=subject,
                topic=f"{subject} Complete Course",
                content=json.dumps(roadmap_data),
                created_by=current_user.id,
                classroom_id=None
            )
            db.session.add(new_roadmap)
            db.session.commit()
            print(f"Roadmap saved with ID: {new_roadmap.id}")
            
            return jsonify({
                "status": "success",
                "message": "Course roadmap created successfully",
                "roadmap": roadmap_data,
                "id": new_roadmap.id
            })
        else:
            return jsonify({"error": "Database not available"}), 500
            
    except Exception as e:
        print(f"CRITICAL Error creating roadmap: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/get-roadmaps/<subject>')
@login_required
def get_roadmaps(subject):
    """Get all roadmaps for a subject (for students)"""
    try:
        if not Roadmap:
            return jsonify({"roadmaps": []})
        
        roadmaps = Roadmap.query.filter_by(subject=subject).order_by(Roadmap.created_at.desc()).all()
        
        roadmap_list = []
        for rm in roadmaps:
            roadmap_list.append({
                "id": rm.id,
                "topic": rm.topic,
                "subject": rm.subject,
                "content": json.loads(rm.content),
                "created_at": rm.created_at.strftime("%Y-%m-%d")
            })
        
        return jsonify({"roadmaps": roadmap_list})
        
    except Exception as e:
        print(f"Error fetching roadmaps: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/roadmap/<int:roadmap_id>')
@login_required
def roadmap_detail(roadmap_id):
    """View detailed roadmap with timeline"""
    if not Roadmap:
        flash("Roadmap system not available", "danger")
        return redirect(url_for('student_index'))
    
    roadmap = Roadmap.query.get_or_404(roadmap_id)
    roadmap_data = json.loads(roadmap.content)
    
    return render_template('roadmap_detail.html',
                         roadmap=roadmap,
                         roadmap_data=roadmap_data,
                         user=current_user,
                         active_page='roadmap_detail')

@app.route('/teacher/student-progress')
@login_required
def teacher_student_progress():
    """Teacher view of student progress"""
    if current_user.role != 'teacher':
        return redirect(url_for('student_index'))
    
    return render_template('teacher_templates/student_progress_classroom.html', 
                         user=current_user,
                         active_page='teacher_student_progress')

# ==========================================
# SHARED API ROUTES
# ==========================================

@app.route('/ask-ai', methods=['POST'])
@login_required
def ask_ai():
    """AI Tutor API endpoint - works for both students and teachers"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        user_message = data.get("message")
        subject = data.get("subject", "General")
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        
        role_prefix = "Teacher" if current_user.role == 'teacher' else "Student"
        prompt = f"[{role_prefix}] {user_message}"
        
        response_text = get_ai_response(prompt, subject=subject)
        
        return jsonify({
            "response": response_text,
            "role": current_user.role,
            "subject": subject
        })
        
    except Exception as e:
        print(f"Error in ask_ai: {e}")
        return jsonify({"response": "Sorry, I encountered an error. Please try again."}), 500

@app.route('/save-score', methods=['POST'])
@login_required
def save_score():
    """Save quiz score - primarily for students"""
    if not QuizScore or not db:
        return jsonify({"status": "error", "message": "Database not available"}), 500
    
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        new_score = QuizScore(
            user_id=current_user.id,
            topic=data.get('topic', 'General'),
            score=data.get('score', 0),
            total=data.get('total', 10),
            date=datetime.utcnow()
        )
        
        db.session.add(new_score)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Score saved successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error saving score: {e}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

# ==========================================
# UTILITY ROUTES
# ==========================================

@app.route('/forgot-password')
def forgot_password():
    """Password recovery page"""
    return render_template('forgot_password.html')

@app.route('/reset-password')
def reset_password():
    """Password reset page"""
    return render_template('reset_password.html')

@app.route('/verify-otp')
def verify_otp():
    """OTP verification page"""
    return render_template('verify_otp.html')

@app.route('/about')
def about_platform():
    """About page"""
    return render_template('about.html') if os.path.exists(os.path.join(template_base, 'about.html')) else "StudyPath AI - Developed for Sindh Board Students."

# ==========================================
# ERROR HANDLERS
# ==========================================

@app.errorhandler(404)
def page_not_found(e):
    """Custom 404 page"""
    if current_user.is_authenticated:
        if current_user.role == 'teacher':
            return render_template('teacher_templates/dashboard.html', user=current_user, active_page='teacher_dashboard'), 404
        return render_template('student_templates/index.html', user=current_user, active_page='student_index'), 404
    return render_template('login.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Custom 500 page"""
    print(f"Server Error: {e}")
    if current_user.is_authenticated:
        flash("An internal server error occurred. Please try again.", "danger")
        if current_user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        return redirect(url_for('student_index'))
    return "Server temporarily unavailable. Please try again later.", 500

@app.errorhandler(403)
def forbidden(e):
    """Custom 403 page"""
    flash("You don't have permission to access this page.", "danger")
    if current_user.is_authenticated:
        if current_user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        return redirect(url_for('student_index'))
    return redirect(url_for('login'))

# ==========================================
# MAIN ENTRY POINT
# ==========================================

if __name__ == '__main__':
    with app.app_context():
        if db:
            db.create_all()
            print("[OK] Database tables verified/created")
            
            if User:
                # Create default teacher if not exists
                existing_teacher = User.query.filter_by(role='teacher').first()
                if not existing_teacher:
                    try:
                        default_teacher = User(
                            full_name="Sir Ahmed",
                            email="teacher@studypath.com",
                            password="teacher123",
                            grade=11,
                            group="Administration",
                            role="teacher",
                            active_subjects="All"
                        )
                        db.session.add(default_teacher)
                        db.session.commit()
                        print("[OK] Default teacher created (email: teacher@studypath.com, password: teacher123)")
                    except Exception as e:
                        print(f"Note: Could not create default teacher: {e}")
# ... existing code ...

    print(f"[OK] StudyPath Server Starting...")
    print(f"[OK] Template folder: {template_base}")
    print(f"[OK] Static folder: {static_base}")
    print(f"[OK] Running on http://127.0.0.1:5000")
    
    app.run(debug=True, port=5000, use_reloader=False)