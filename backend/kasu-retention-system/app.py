"""
Kaduna State University Academic Retention System - Main Application
"""

from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy 
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
import os
from dotenv import load_dotenv
from pathlib import Path
from flask_migrate import Migrate

# Handle both package and direct execution imports
try:
    from .models import db, User, Student, Prediction, Intervention
    from .ml_model import predict_dropout_risk, get_intervention_strategy
except ImportError:
    from models import db, User, Student, Prediction, Intervention
    from ml_model import predict_dropout_risk, get_intervention_strategy

# Load environment variables
load_dotenv()

# DATABASE CLEANUP FUNCTION
def cleanup_old_database():
    """Remove the correct database file - retention.db"""
    db_paths = [
        "instance/retention.db",
        "retention.db",
        "app.db",
        "instance/app.db"
    ]
    
    for path in db_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f" Deleted old database: {path}")
            except PermissionError:
                print(f" Could not delete {path} - file may be in use. Continuing...")
            except Exception as e:
                print(f" Error deleting {path}: {e}")

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'kaduna-state-university-retention-2025')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///retention.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)
migrate = Migrate(app, db)

# DATABASE INITIALIZATION
cleanup_old_database()

# Initialize database tables and demo data
def initialize_database():
    with app.app_context():
        db.create_all()
        print(" Database tables created successfully!")
        
        # Create admin user if it doesn't exist
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin', 
                role='admin',
                email='admin@kasu.edu.ng' 
            )
            admin.set_password('admin123')
            db.session.add(admin)
            print(" Admin user created: username='admin', password='admin123'")
        
        # Create demo lecturer if it doesn't exist
        if not User.query.filter_by(role='lecturer').first():
            lecturer = User(
                username='lecturer1',
                email='lecturer@kasu.edu.ng',
                department='Computer Science',
                role='lecturer'
            )
            lecturer.set_password('lecturer123')
            db.session.add(lecturer)
            print(" Demo lecturer created: username='lecturer1', password='lecturer123'")
        
        # Create demo student record if it doesn't exist 
        if not Student.query.filter_by(student_id='KASU001').first():
            demo_student = Student(
                name='John Doe',
                student_id='KASU001',
                course='Computer Science',
                gpa=3.2,
                attendance=85.5,
                failures=1,
                residence='Urban',
                parental_income=450000.0
            )
            db.session.add(demo_student)
            print(" Demo student record created: KASU001")
        
    
        if not Student.query.filter_by(student_id='KASU002').first():
            demo_student2 = Student(
                name='Jane Smith',
                student_id='KASU002',
                course='Engineering',
                gpa=2.8,
                attendance=72.0,
                failures=2,
                residence='Rural',
                parental_income=280000.0
            )
            db.session.add(demo_student2)
            print(" Demo student record created: KASU002")
        
        db.session.commit()
        print(" Database initialization completed!")

# Call initialization
initialize_database()

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Load ML model
try:
    model = joblib.load('model.pkl')
    print(" ML model loaded successfully")
except Exception as e:
    print(f"  ML model not found: {e}. Running in demo mode.")
    model = None

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ROUTES

@app.route('/')
def home():
    """Home page"""
    return render_template('index.html')

@app.route('/debug')
def debug_info():
    """Debug page to check database status"""
    users = User.query.all()
    students = Student.query.all()
    
    user_info = "USERS:\n" + "\n".join([f"- {u.username} (role: {u.role}, email: {u.email})" for u in users])
    student_info = "STUDENTS:\n" + "\n".join([f"- {s.name} (ID: {s.student_id}, User ID: {s.user_id})" for s in students])
    
    return f"<pre>{user_info}\n\n{student_info}</pre>"

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for both advisors and students"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            
            # Redirect based on user role
            if user.role == 'student':
                return redirect(url_for('student_dashboard'))
            elif user.role == 'lecturer':
                return redirect(url_for('lecturer_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page - for admin/advisor only"""
    if current_user.role == 'student':
        return redirect(url_for('student_dashboard'))
    elif current_user.role == 'lecturer':
        return redirect(url_for('lecturer_dashboard'))
    
    total_students = Student.query.count()
    high_risk = Prediction.query.filter(Prediction.risk_score > 0.7).count()
    total_interventions = Intervention.query.count()
    
    recent_predictions = Prediction.query.order_by(
        Prediction.prediction_date.desc()
    ).limit(5).all()
    
    return render_template('dashboard.html',
                         total_students=total_students,
                         high_risk=high_risk,
                         total_interventions=total_interventions,
                         recent_predictions=recent_predictions)

@app.route('/assess', methods=['GET', 'POST'])
@login_required
def assess():
    """Student assessment page - admin/advisor only"""
    if current_user.role == 'student':
        flash('Access denied. Advisors only.', 'error')
        return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        try:
            student_data = {
                'name': request.form['name'],
                'student_id': request.form['student_id'],
                'course': request.form['course'],
                'gpa': float(request.form['gpa']),
                'attendance': float(request.form['attendance']),
                'failures': int(request.form['failures']),
                'residence': request.form.get('residence', 'Urban'),
                'parental_income': float(request.form.get('parental_income', 300000)),
                'age': int(request.form.get('age', 20))
            }
            
            # Predicting the  risk score
            risk_score = predict_dropout_risk(student_data, ml_model=model)
            
            # Save to database
            student = Student(
                name=student_data['name'],
                student_id=student_data['student_id'],
                course=student_data['course'],
                gpa=student_data['gpa'],
                attendance=student_data['attendance'],
                failures=student_data['failures'],
                residence=student_data['residence'],
                parental_income=student_data['parental_income']
            )
            
            prediction = Prediction(
                student=student,
                risk_score=risk_score,
                prediction_date=datetime.now()
            )
            
            db.session.add(student)
            db.session.add(prediction)
            db.session.commit()
            
            flash(f'Assessment completed. Risk score: {risk_score:.1%}', 'success')
            return redirect(url_for('assessment_result', student_id=student.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error during assessment: {str(e)}', 'error')
    
    return render_template('assess.html')

@app.route('/assessment_result/<int:student_id>')
@login_required
def assessment_result(student_id):
    """Show assessment results"""
    student = Student.query.get_or_404(student_id)
    prediction = Prediction.query.filter_by(student_id=student_id).order_by(
        Prediction.prediction_date.desc()).first()
    
    return render_template('assessment_result.html',
                         student=student,
                         prediction=prediction)

@app.route('/students')
@login_required
def students():
    """Students management page - admin/advisor only"""
    if current_user.role == 'student':
        flash('Access denied. Advisors only.', 'error')
        return redirect(url_for('student_dashboard'))
    
    all_students = Student.query.all()
    return render_template('students.html', students=all_students)

@app.route('/analytics')
@login_required
def analytics():
    """Analytics page"""
    if current_user.role == 'student':
        flash('Access denied. Advisors only.', 'error')
        return redirect(url_for('student_dashboard'))
    
    # Get risk distribution with proper error handling
    try:
        risk_distribution = {
            'low': Prediction.query.filter(Prediction.risk_score < 0.4).count(),
            'medium': Prediction.query.filter(Prediction.risk_score.between(0.4, 0.7)).count(),
            'high': Prediction.query.filter(Prediction.risk_score > 0.7).count()
        }
        
        # Getting course analysis
        course_analysis = db.session.query(
            Student.course,
            db.func.avg(Prediction.risk_score).label('avg_risk'),
            db.func.count(Student.id).label('student_count')
        ).join(Prediction, Student.id == Prediction.student_id).group_by(Student.course).all()
        
    except Exception as e:
        print(f"Analytics error: {e}")
        risk_distribution = {'low': 0, 'medium': 0, 'high': 0}
        course_analysis = []
    
    return render_template('analytics.html',
                         risk_distribution=risk_distribution,
                         course_analysis=course_analysis)

@app.route('/debug_predictions')
@login_required
def debug_predictions():
    """Debug page to check prediction data"""
    if current_user.role == 'student':
        flash('Access denied. Advisors only.', 'error')
        return redirect(url_for('student_dashboard'))
    
    predictions = Prediction.query.all()
    risk_distribution = {
        'low': Prediction.query.filter(Prediction.risk_score < 0.4).count(),
        'medium': Prediction.query.filter(Prediction.risk_score.between(0.4, 0.7)).count(),
        'high': Prediction.query.filter(Prediction.risk_score > 0.7).count()
    }
    
    result = f"Total Predictions: {len(predictions)}\n\n"
    result += "Risk Distribution:\n"
    result += f"Low: {risk_distribution['low']}\n"
    result += f"Medium: {risk_distribution['medium']}\n"
    result += f"High: {risk_distribution['high']}\n\n"
    
    result += "Recent Predictions:\n"
    for pred in predictions[:10]:
        student_name = pred.student.name if pred.student else "Unknown Student"
        result += f"- {student_name}: {pred.risk_score} ({pred.prediction_date})\n"
    
    return f"<pre>{result}</pre>"

@app.route('/generate_test_data')
@login_required
def generate_test_data():
    """Generate test prediction data for analytics"""
    if current_user.role == 'student':
        flash('Access denied.', 'error')
        return redirect(url_for('student_dashboard'))
    
    try:
        students = Student.query.all()
        
        if not students:
            flash('No students found. Please add students first.', 'error')
            return redirect(url_for('assess'))
        
        for student in students:
            # Delete existing predictions for this student
            Prediction.query.filter_by(student_id=student.id).delete()
            
            # Create new prediction with random risk score
            risk_score = round(np.random.uniform(0.1, 0.9), 2)
            prediction = Prediction(
                student_id=student.id,
                risk_score=risk_score,
                prediction_date=datetime.now()
            )
            db.session.add(prediction)
        
        db.session.commit()
        flash(f'Generated test predictions for {len(students)} students.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error generating test data: {str(e)}', 'error')
    
    return redirect(url_for('analytics'))

@app.route('/student_register', methods=['GET', 'POST'])
def student_register():
    """Student registration page"""
    if request.method == 'POST':
        try:
            student_id = request.form['student_id'].strip().upper()
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            
            # Check if passwords match
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('student_register.html')
            
            # Check if student exists in database
            student = Student.query.filter_by(student_id=student_id).first()
            if not student:
                flash(f'Student ID "{student_id}" not found. Please check your ID or contact administrator.', 'error')
                return render_template('student_register.html')
            
            # Check if student already has an account
            if student.user_id:
                flash('Account already exists for this student ID. Please login instead.', 'error')
                return render_template('student_register.html')
            
            # Create user account with student role
            username = f"{student_id}"
            
            # Check if username already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists. Please contact administrator.', 'error')
                return render_template('student_register.html')
            
            user = User(username=username, role='student', email=f"{student_id}@kasu.edu.ng")
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()  # Commit to get the user ID
            
            # Link student to user account
            student.user_id = user.id
            db.session.commit()
            
            flash(f'Account created successfully! Please login with username: {username}', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error during registration: {str(e)}', 'error')
            print(f"Registration error: {e}")
    
    # Show available student IDs for registration
    available_students = Student.query.filter(Student.user_id == None).all()
    return render_template('student_register.html', available_students=available_students)

@app.route('/lecturer_register', methods=['GET', 'POST'])
def lecturer_register():
    """Lecturer registration page"""
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            email = request.form.get('email', '')
            department = request.form.get('department', 'General')
            
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('lecturer_register.html')
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'error')
                return render_template('lecturer_register.html')
            
            lecturer = User(
                username=username,
                email=email,
                department=department,
                role='lecturer'
            )
            lecturer.set_password(password)
            
            db.session.add(lecturer)
            db.session.commit()
            
            flash('Lecturer account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error during registration: {str(e)}', 'error')
    
    return render_template('lecturer_register.html')

@app.route('/lecturer_dashboard')
@login_required
def lecturer_dashboard():
    """Lecturer dashboard page"""
    if current_user.role != 'lecturer':
        flash('Access denied. Lecturers only.', 'error')
        return redirect(url_for('dashboard'))
    
    department_students = Student.query.all()
    
    high_risk_students = []
    for student in department_students:
        latest_prediction = Prediction.query.filter_by(
            student_id=student.id
        ).order_by(Prediction.prediction_date.desc()).first()
        
        if latest_prediction and latest_prediction.risk_score > 0.5:
            high_risk_students.append({
                'student': student,
                'risk_score': latest_prediction.risk_score
            })
    
    return render_template('lecturer_dashboard.html',
                         lecturer=current_user,
                         total_students=len(department_students),
                         high_risk_students=high_risk_students)

@app.route('/lecturer_students')
@login_required
def lecturer_students():
    """Lecturer's view of students"""
    if current_user.role != 'lecturer':
        flash('Access denied. Lecturers only.', 'error')
        return redirect(url_for('students'))
    
    department_students = Student.query.all()
    
    return render_template('lecturer_students.html',
                         students=department_students,
                         lecturer=current_user)

@app.route('/student_dashboard')
@login_required
def student_dashboard():
    """Student dashboard page"""
    if current_user.role != 'student':
        flash('Access denied. Students only.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get student profile
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash('Student profile not found. Please contact administrator.', 'error')
        return redirect(url_for('logout'))
    
    # Get latest prediction
    prediction = Prediction.query.filter_by(student_id=student.id).order_by(
        Prediction.prediction_date.desc()).first()
    
    # Get interventions
    interventions = Intervention.query.filter_by(student_id=student.id).order_by(
        Intervention.created_date.desc()).all()
    
    return render_template('student_dashboard.html',
                         student=student,
                         prediction=prediction,
                         interventions=interventions)

@app.context_processor
def inject_template_helpers():
    """Make helper functions and user role available to all templates"""
    return dict(
        current_user_role=current_user.role if current_user.is_authenticated else None,
        get_intervention_strategy=get_intervention_strategy
    )

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    print(" Starting Kaduna State University Academic Retention System...")
    # Disable debug and reloader for production
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)