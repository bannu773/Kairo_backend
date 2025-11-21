from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from bson import ObjectId

from app.models.task import Task
from app.models.user import User
from app.models.processed_email import ProcessedEmail
from app.models.meeting import Meeting
from app.services.gmail_service import GmailService
from app.services.gemini_service import GeminiService

api = Namespace('tasks', description='Task operations')

# Models for Swagger documentation
task_input = api.model('TaskInput', {
    'title': fields.String(required=True, description='Task title'),
    'description': fields.String(description='Task description'),
    'priority': fields.String(description='Priority: low, medium, high', enum=['low', 'medium', 'high']),
    'deadline': fields.DateTime(description='Task deadline'),
    'assigned_to_email': fields.String(description='Email of user to assign task to')
})

task_update = api.model('TaskUpdate', {
    'title': fields.String(description='Task title'),
    'description': fields.String(description='Task description'),
    'priority': fields.String(description='Priority: low, medium, high', enum=['low', 'medium', 'high']),
    'status': fields.String(description='Status: pending, in_progress, completed', 
                           enum=['pending', 'in_progress', 'completed']),
    'deadline': fields.DateTime(description='Task deadline')
})

user_info = api.model('UserInfo', {
    'id': fields.String(description='User ID'),
    'email': fields.String(description='User email'),
    'name': fields.String(description='User name')
})

email_info = api.model('EmailInfo', {
    'message_id': fields.String(description='Email message ID'),
    'subject': fields.String(description='Email subject'),
    'date': fields.String(description='Email date')
})

task_model = api.model('Task', {
    'id': fields.String(description='Task ID'),
    'title': fields.String(description='Task title'),
    'description': fields.String(description='Task description'),
    'priority': fields.String(description='Task priority'),
    'status': fields.String(description='Task status'),
    'deadline': fields.DateTime(description='Task deadline'),
    'assigned_to': fields.Nested(user_info),
    'assigned_by': fields.Nested(user_info),
    'created_from_email': fields.Nested(email_info),
    'created_at': fields.DateTime(description='Creation timestamp'),
    'updated_at': fields.DateTime(description='Last update timestamp')
})


@api.route('')
class TaskList(Resource):
    @api.doc('get_tasks', security='Bearer')
    @api.param('status', 'Filter by status')
    @api.param('priority', 'Filter by priority')
    @api.param('source_type', 'Filter by source type')
    @api.param('page', 'Page number', type=int, default=1)
    @api.param('per_page', 'Items per page', type=int, default=10)
    @api.response(200, 'Success')
    @api.response(401, 'Unauthorized')
    @jwt_required()
    def get(self):
        """Get all tasks for current user"""
        try:
            user_id = get_jwt_identity()
            
            # Get query parameters
            status = request.args.get('status')
            priority = request.args.get('priority')
            source_type = request.args.get('source_type')
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 10))
            
            # Get tasks
            result = Task.get_user_tasks(
                user_id=user_id,
                status=status,
                priority=priority,
                source_type=source_type,
                page=page,
                per_page=per_page
            )
            
            # Serialize tasks
            tasks = [Task.serialize(task) for task in result['tasks']]
            
            return {
                'success': True,
                'data': {
                    'tasks': tasks,
                    'pagination': result['pagination']
                }
            }, 200
            
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500
    
    @api.doc('create_task', security='Bearer')
    @api.expect(task_input)
    @api.response(201, 'Task created')
    @api.response(401, 'Unauthorized')
    @jwt_required()
    def post(self):
        """Create a new task manually"""
        try:
            user_id = get_jwt_identity()
            user = User.find_by_id(user_id)
            data = request.get_json()
            
            # Validate required fields
            if not data.get('title'):
                return {'success': False, 'error': 'Title is required'}, 400
            
            # Get assigned user
            assigned_to_email = data.get('assigned_to_email')
            if assigned_to_email:
                assigned_to = User.find_by_email(assigned_to_email)
                if not assigned_to:
                    return {'success': False, 'error': 'Assigned user not found'}, 404
                assigned_to_id = str(assigned_to['_id'])
            else:
                assigned_to_id = user_id
            
            # Parse deadline
            deadline = None
            if data.get('deadline'):
                try:
                    deadline = datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
                except ValueError:
                    return {'success': False, 'error': 'Invalid deadline format'}, 400
            
            # Create task
            task = Task.create(
                title=data['title'],
                description=data.get('description', ''),
                priority=data.get('priority', 'medium'),
                deadline=deadline,
                assigned_to=assigned_to_id,
                created_by=user_id,
                user_email=user.get('email'),  # Store creator's email for isolation
                source_type='manual'  # Mark as manually created task
            )
            
            return {
                'success': True,
                'data': Task.serialize(task)
            }, 201
            
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@api.route('/<string:task_id>')
class TaskDetail(Resource):
    @api.doc('get_task', security='Bearer')
    @api.response(200, 'Success', task_model)
    @api.response(404, 'Task not found')
    @api.response(401, 'Unauthorized')
    @jwt_required()
    def get(self, task_id):
        """Get a specific task"""
        try:
            user_id = get_jwt_identity()
            task = Task.find_by_id(task_id)
            
            if not task:
                return {'success': False, 'error': 'Task not found'}, 404
            
            # Check if user has access to this task
            if str(task['assigned_to']) != user_id and str(task.get('assigned_by')) != user_id:
                return {'success': False, 'error': 'Access denied'}, 403
            
            return {
                'success': True,
                'data': Task.serialize(task)
            }, 200
            
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500
    
    @api.doc('update_task', security='Bearer')
    @api.expect(task_update)
    @api.response(200, 'Task updated')
    @api.response(404, 'Task not found')
    @api.response(401, 'Unauthorized')
    @jwt_required()
    def put(self, task_id):
        """Update a task"""
        try:
            user_id = get_jwt_identity()
            task = Task.find_by_id(task_id)
            
            if not task:
                return {'success': False, 'error': 'Task not found'}, 404
            
            # Check if user has access to this task
            if str(task['assigned_to']) != user_id and str(task.get('assigned_by')) != user_id:
                return {'success': False, 'error': 'Access denied'}, 403
            
            data = request.get_json()
            update_data = {}
            
            # Update allowed fields
            if 'title' in data:
                update_data['title'] = data['title']
            if 'description' in data:
                update_data['description'] = data['description']
            if 'priority' in data:
                update_data['priority'] = data['priority']
            if 'status' in data:
                update_data['status'] = data['status']
            if 'deadline' in data:
                try:
                    update_data['deadline'] = datetime.fromisoformat(
                        data['deadline'].replace('Z', '+00:00')
                    )
                except ValueError:
                    return {'success': False, 'error': 'Invalid deadline format'}, 400
            
            # Update task
            updated_task = Task.update(task_id, update_data)
            
            return {
                'success': True,
                'data': Task.serialize(updated_task)
            }, 200
            
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500
    
    @api.doc('delete_task', security='Bearer')
    @api.response(200, 'Task deleted')
    @api.response(404, 'Task not found')
    @api.response(401, 'Unauthorized')
    @jwt_required()
    def delete(self, task_id):
        """Delete a task"""
        try:
            user_id = get_jwt_identity()
            task = Task.find_by_id(task_id)
            
            if not task:
                return {'success': False, 'error': 'Task not found'}, 404
            
            
            Task.delete(task_id)
            
            return {
                'success': True,
                'message': 'Task deleted successfully'
            }, 200
            
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@api.route('/sync')
class TaskSync(Resource):
    @api.doc('sync_emails', security='Bearer')
    @api.response(200, 'Sync completed')
    @api.response(401, 'Unauthorized')
    @jwt_required()
    def post(self):
        """Manually trigger email synchronization"""
        try:
            user_id = get_jwt_identity()
            user = User.find_by_id(user_id)
            
            if not user:
                return {'success': False, 'error': 'User not found'}, 404
            
            # Check if user has Gmail token
            if not user.get('gmail_refresh_token'):
                return {
                    'success': False,
                    'error': 'Gmail not connected. Please login again.'
                }, 400
            
            # Initialize services
            gmail_service = GmailService.get_service_for_user(user)
            gemini_service = GeminiService()
            
            if not gmail_service:
                return {
                    'success': False,
                    'error': 'Failed to initialize Gmail service'
                }, 500
            
            # Get recent emails (last 24 hours)
            from datetime import datetime, timedelta
            since_date = datetime.utcnow() - timedelta(hours=24)
            emails = gmail_service.get_emails_since(since_date)
            
            processed_count = 0
            created_count = 0
            errors = []
            skipped_count = 0
            
            for email_msg in emails:
                try:
                    # Parse email
                    email_data = gmail_service.parse_email(email_msg)
                    email_id = email_data['message_id']
                    
                    # Skip emails from the user themselves
                    sender_email = gmail_service.extract_sender_email(email_data['from'])
                    if sender_email.lower() == user.get('email', '').lower():
                        continue
                    
                    # Check if email already processed using ProcessedEmail model
                    if ProcessedEmail.is_processed(email_id, user_id):
                        skipped_count += 1
                        continue
                    
                    processed_count += 1
                    
                    # Extract task using Gemini
                    task_info = gemini_service.extract_task_from_email(
                        email_subject=email_data['subject'],
                        email_body=email_data['body']
                    )
                    
                    if task_info and task_info.get('has_task', False):
                        # Check if multiple tasks were extracted
                        tasks_to_create = task_info.get('tasks', [])
                        if not tasks_to_create:
                            # Fallback to single task format for backward compatibility
                            tasks_to_create = [{
                                'title': task_info.get('title', email_data['subject']),
                                'description': task_info.get('description', ''),
                                'priority': task_info.get('priority', 'medium'),
                                'deadline': task_info.get('deadline')
                            }]
                        
                        # Create all extracted tasks
                        tasks_created_for_this_email = 0
                        for task_data in tasks_to_create:
                            try:
                                Task.create(
                                    title=task_data.get('title', email_data['subject']),
                                    description=task_data.get('description', ''),
                                    priority=task_data.get('priority', 'medium'),
                                    deadline=task_data.get('deadline'),
                                    assigned_to=user_id,
                                    created_by=user_id,  # Self-assigned from email
                                    email_id=email_data['message_id'],
                                    sender_email=sender_email,
                                    user_email=user.get('email'),  # CRITICAL FIX: Store which user received this email
                                    labels=task_info.get('labels', []),
                                    source_type='email'  # Mark as email-sourced task
                                )
                                
                                created_count += 1
                                tasks_created_for_this_email += 1
                                print(f"✅ Created task: {task_data.get('title', email_data['subject'])[:50]}...")
                            except Exception as task_error:
                                print(f"❌ Failed to create task: {task_error}")
                                errors.append(f"Failed to create task: {str(task_error)}")
                        
                        # Mark email as processed
                        ProcessedEmail.mark_as_processed(email_id, user_id, tasks_created=tasks_created_for_this_email)
                    else:
                        # Mark as processed even if no tasks were found
                        ProcessedEmail.mark_as_processed(email_id, user_id, tasks_created=0)
                
                except Exception as e:
                    error_msg = f"Error processing email: {str(e)}"
                    print(error_msg)
                    errors.append(error_msg)
            
            return {
                'success': True,
                'data': {
                    'processed_emails': processed_count,
                    'skipped_emails': skipped_count,
                    'new_tasks_created': created_count,
                    'errors': len(errors),
                    'error_details': errors[:5] if errors else []  # Show first 5 errors
                },
                'message': f'Processed {processed_count} new emails, skipped {skipped_count} already processed, created {created_count} tasks'
            }, 200
            
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@api.route('/polling/status')
class PollingStatus(Resource):
    @api.doc('polling_status', security='Bearer')
    @api.response(200, 'Polling status')
    @jwt_required()
    def get(self):
        """Get email polling service status"""
        try:
            from app.services.email_polling_service import email_polling_service
            
            return {
                'success': True,
                'data': {
                    'is_running': email_polling_service.is_running,
                    'poll_interval': email_polling_service.poll_interval,
                    'message': 'Email polling is automatically checking for new emails every 30 seconds' if email_polling_service.is_running else 'Email polling is not running'
                }
            }, 200
            
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@api.route('/from-meeting/<string:meeting_id>')
class TasksFromMeeting(Resource):
    @api.doc('tasks_from_meeting', security='Bearer')
    @api.response(200, 'Success')
    @api.response(404, 'Meeting not found')
    @api.response(401, 'Unauthorized')
    @jwt_required()
    def get(self, meeting_id):
        """Get all tasks created from a specific meeting"""
        try:
            user_id = get_jwt_identity()
            meeting = Meeting.find_by_id(meeting_id)
            
            if not meeting:
                return {'success': False, 'error': 'Meeting not found'}, 404
            
            # Check if user has access to this meeting
            if str(meeting['user_id']) != user_id:
                return {'success': False, 'error': 'Access denied'}, 403
            
            # Get tasks from this meeting
            from app import get_db
            db = get_db()
            
            tasks = list(db.tasks.find({
                'meeting_id': meeting_id,
                'assigned_to': ObjectId(user_id)
            }).sort('created_at', -1))
            
            return {
                'success': True,
                'data': {
                    'meeting': Meeting.serialize(meeting),
                    'tasks': [Task.serialize(task) for task in tasks],
                    'total': len(tasks)
                }
            }, 200
            
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500
