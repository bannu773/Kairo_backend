from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.models.user import User


def admin_required(fn):
    """Decorator to require admin role"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.find_by_id(user_id)
        
        if not user or user.get('role') != 'admin':
            return jsonify({
                'success': False,
                'error': 'Admin access required'
            }), 403
        
        return fn(*args, **kwargs)
    
    return wrapper


def manager_required(fn):
    """Decorator to require manager or admin role"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.find_by_id(user_id)
        
        if not user or user.get('role') not in ['manager', 'admin']:
            return jsonify({
                'success': False,
                'error': 'Manager or admin access required'
            }), 403
        
        return fn(*args, **kwargs)
    
    return wrapper
