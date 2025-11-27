"""
Nigerian University Academic Retention System - Backend Package
"""
# This file makes the backend directory a Python package

# You can optionally import key components to make them easily accessible
from .app import app
from .models import db, User, Student, Prediction, Intervention
from .ml_model import predict_dropout_risk, get_intervention_strategy

# Package metadata
__version__ = "1.0.0"
__author__ = "Nicholas Bobbai Ezekiel"
__description__ = "Backend for Nigerian University Academic Retention System"