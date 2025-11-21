from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models.user import User

api = Namespace('users', description='User operations')

# Models for Swagger documentation
user_model = api.model('User', {
    'id': fields.String(description='User ID'),
    'email': fields.String(description='User email'),
    'name': fields.String(description='User name'),
    'picture': fields.String(description='Profile picture URL'),
    'role': fields.String(description='User role'),
    'created_at': fields.DateTime(description='Account creation date')
})

role_update = api.model('RoleUpdate', {
    'role': fields.String(required=True, description='New role', enum=['user', 'manager', 'admin'])
})


@api.route('')
class UserList(Resource):
    @api.doc('get_users', security='Bearer')
    @api.param('role', 'Filter by role')
    @api.param('page', 'Page number', type=int, default=1)
    @api.param('per_page', 'Items per page', type=int, default=10)
    @api.response(200, 'Success')
    @api.response(401, 'Unauthorized')
    @api.response(403, 'Forbidden')
    @jwt_required()
    def get(self):
        """Get all users (manager/admin only)"""
        try:
            user_id = get_jwt_identity()
            current_user = User.find_by_id(user_id)
            
            # Check if user is manager or admin
            if current_user.get('role') not in ['manager', 'admin']:
                return {'success': False, 'error': 'Insufficient permissions'}, 403
            
            # Get query parameters
            role = request.args.get('role')
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 10))
            
            # Build filter
            filter_dict = {}
            if role:
                filter_dict['role'] = role
            
            # Get users
            result = User.get_all(filter_dict, page, per_page)
            
            # Serialize users
            users = [User.serialize(user) for user in result['users']]
            
            return {
                'success': True,
                'data': {
                    'users': users,
                    'pagination': result['pagination']
                }
            }, 200
            
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@api.route('/<string:user_id>')
class UserDetail(Resource):
    @api.doc('get_user', security='Bearer')
    @api.response(200, 'Success', user_model)
    @api.response(404, 'User not found')
    @api.response(401, 'Unauthorized')
    @jwt_required()
    def get(self, user_id):
        """Get a specific user"""
        try:
            current_user_id = get_jwt_identity()
            current_user = User.find_by_id(current_user_id)
            
            # Check if user is accessing their own profile or is manager/admin
            if user_id != current_user_id and current_user.get('role') not in ['manager', 'admin']:
                return {'success': False, 'error': 'Insufficient permissions'}, 403
            
            user = User.find_by_id(user_id)
            
            if not user:
                return {'success': False, 'error': 'User not found'}, 404
            
            # Get task statistics
            from app.models.task import Task
            from bson import ObjectId
            from app import get_db
            
            db = get_db()
            tasks_assigned = db.tasks.count_documents({'assigned_to': ObjectId(user_id)})
            tasks_completed = db.tasks.count_documents({
                'assigned_to': ObjectId(user_id),
                'status': 'completed'
            })
            
            user_data = User.serialize(user)
            user_data['tasks_assigned'] = tasks_assigned
            user_data['tasks_completed'] = tasks_completed
            
            return {
                'success': True,
                'data': user_data
            }, 200
            
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@api.route('/<string:user_id>/role')
class UserRole(Resource):
    @api.doc('update_user_role', security='Bearer')
    @api.expect(role_update)
    @api.response(200, 'Role updated')
    @api.response(404, 'User not found')
    @api.response(401, 'Unauthorized')
    @api.response(403, 'Forbidden')
    @jwt_required()
    def put(self, user_id):
        """Update user role (admin only)"""
        try:
            current_user_id = get_jwt_identity()
            current_user = User.find_by_id(current_user_id)
            
            # Check if user is admin
            if current_user.get('role') != 'admin':
                return {'success': False, 'error': 'Admin access required'}, 403
            
            user = User.find_by_id(user_id)
            
            if not user:
                return {'success': False, 'error': 'User not found'}, 404
            
            data = request.get_json()
            new_role = data.get('role')
            
            if new_role not in ['user', 'manager', 'admin']:
                return {'success': False, 'error': 'Invalid role'}, 400
            
            # Update role
            updated_user = User.update_role(user_id, new_role)
            
            return {
                'success': True,
                'data': User.serialize(updated_user)
            }, 200
            
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500
