from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Create db instance
db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='advisor')  # 'admin', 'advisor', 'lecturer', 'student'
    email = db.Column(db.String(120))
    department = db.Column(db.String(50))  # For lecturers
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    course = db.Column(db.String(50), nullable=False)
    gpa = db.Column(db.Float, nullable=False)
    attendance = db.Column(db.Float, nullable=False)
    failures = db.Column(db.Integer, nullable=False)
    residence = db.Column(db.String(50), default='Urban')
    parental_income = db.Column(db.Float, default=0.0)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Link to user account
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', backref='student_profile', foreign_keys=[user_id])
    
    predictions = db.relationship('Prediction', backref='student', lazy=True, cascade='all, delete-orphan')
    interventions = db.relationship('Intervention', backref='student', lazy=True, cascade='all, delete-orphan')

class Prediction(db.Model):
    __tablename__ = 'predictions'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    risk_score = db.Column(db.Float, nullable=False)
    prediction_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    features_used = db.Column(db.Text)

class Intervention(db.Model):
    __tablename__ = 'interventions'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    intervention_type = db.Column(db.String(50), nullable=False)
    scheduled_date = db.Column(db.DateTime, nullable=False)
    completed_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='scheduled')
    created_date = db.Column(db.DateTime, default=datetime.utcnow)