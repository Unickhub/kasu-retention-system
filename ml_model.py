import pandas as pd
import numpy as np

def predict_dropout_risk(student_data, ml_model=None):
    """Predict dropout risk for a student"""
    if ml_model is None:
        # Return a random risk score for demo mode
        return round(np.random.uniform(0.1, 0.9), 2)
    
    try:
        # Map your form fields to the expected feature names
        features = {
            'Age': student_data.get('age', 20),
            'Gender': 1,  # Default to male (1)
            'Course_Chosen': _map_course_to_number(student_data.get('course', 'Computer Science')),
            'Residence_Location': 1 if student_data.get('residence', 'Urban') == 'Rural' else 0,
            'Semester_Average_Grade': student_data['gpa'] * 25, 
            'Parental_Income_Level': student_data.get('parental_income', 300000) / 50000,
            'Attendance': student_data['attendance'],
            'Marital_Status': 0, 
            'Course_Failures': student_data['failures'],
            'Financial_Stress': student_data.get('parental_income', 300000) / 200000,
            'Attendance_Compliance': 1 if student_data['attendance'] >= 75 else 0,
            'Rural_Disadvantage': 1 if student_data.get('residence', 'Urban') == 'Rural' else 0
        }
        
        # Ensuring the features are in the exact order the model expects
        expected_features = [
            'Age', 'Gender', 'Course_Chosen', 'Residence_Location', 
            'Semester_Average_Grade', 'Parental_Income_Level', 'Attendance', 
            'Marital_Status', 'Course_Failures', 'Financial_Stress', 
            'Attendance_Compliance', 'Rural_Disadvantage'
        ]
        
        # Creating a DataFrame with features in correct order
        X = pd.DataFrame([features])[expected_features]
        
        # Predict using the model
        try:
            
            risk_score = ml_model.predict_proba(X)[0, 1]
        except AttributeError:
            
            risk_score = ml_model.predict(X)[0]
            risk_score = max(0, min(1, risk_score))  # Ensure between 0-1
        
        return round(risk_score, 2)
        
    except Exception as e:
        print(f"Prediction error: {e}")
        return 0.5  

def _map_course_to_number(course_name):
    """Map course names to numerical values that the model expects"""
    course_mapping = {
        'Computer Science': 1,
        'Engineering': 2, 
        'Medicine': 3,
        'Law': 4,
        'Business Administration': 5,
        'Business': 5,
        'Education': 6,
        'Agriculture': 7
    }
    return course_mapping.get(course_name, 1) 

def get_intervention_strategy(risk_score):
    """Get intervention strategy based on risk score"""
    if risk_score > 0.7:
        return " CRITICAL: Immediate counseling, financial aid assessment, parental notification"
    elif risk_score > 0.4:
        return " MODERATE: Academic counseling, tutoring, attendance monitoring"
    else:
        return " LOW: Regular check-ins, progress monitoring"