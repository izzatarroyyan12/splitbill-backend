# This file makes the routes directory a Python package 

from .auth import auth_bp
from .bill import bill_bp

__all__ = ['auth_bp', 'bill_bp'] 