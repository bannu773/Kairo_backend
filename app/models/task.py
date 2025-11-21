from datetime import datetime
from bson import ObjectId
from app import get_db
from app.models.user import User

class Task:
    """Task model"""
    
    collection_name = 'tasks'
    
    @staticmethod
    def create(title, description, priority='medium', deadline=None, assigned_to=None, 
               created_by=None, status='pending', email_id=None, sender_email=None, labels=None,
               source_type='manual', meeting_id=None, meeting_title=None, meeting_date=None, user_email=None):
        """Create a new task"""
        db = get_db()
        task = {
            'title': title,
            'description': description or '',
            'priority': priority,
            'status': status,
            'deadline': deadline,
            'assigned_to': ObjectId(assigned_to) if assigned_to else None,
            'created_by': ObjectId(created_by) if created_by else None,
            'email_id': email_id,
            'sender_email': sender_email,
            'user_email': user_email,  # NEW: Store the user's email who owns this task
            'labels': labels or [],
            'source_type': source_type,  # 'manual', 'email', or 'meeting'
            'meeting_id': ObjectId(meeting_id) if meeting_id else None,
            'meeting_title': meeting_title,
            'meeting_date': meeting_date,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        result = db.tasks.insert_one(task)
        task['_id'] = result.inserted_id
        return task
    
    @staticmethod
    def find_by_id(task_id):
        """Find task by ID"""
        db = get_db()
        return db.tasks.find_one({'_id': ObjectId(task_id)})
    
    @staticmethod
    def get_all(filter_dict=None, page=1, per_page=10):
        """Get all tasks with pagination"""
        db = get_db()
        query = filter_dict or {}
        
        skip = (page - 1) * per_page
        tasks = list(db.tasks.find(query).sort('created_at', -1).skip(skip).limit(per_page))
        total = db.tasks.count_documents(query)
        
        return {
            'tasks': tasks,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }
    
    @staticmethod
    def get_user_tasks(user_id, status=None, priority=None, source_type=None, page=1, per_page=10):
        """Get tasks for a specific user"""
        from app.models.user import User
        
        # Get user email for additional filtering
        user = User.find_by_id(user_id)
        user_email = user.get('email') if user else None
        
        # Build base query - filter by assigned_to AND user_email for proper isolation
        query = {'assigned_to': ObjectId(user_id)}
        
        # Add user_email filter if available (this ensures proper user isolation)
        if user_email:
            query['$or'] = [
                {'user_email': user_email},  # Tasks where user_email matches
                {'user_email': {'$exists': False}}  # Old tasks without user_email (backward compatibility)
            ]
        
        # Add optional filters
        if status:
            query['status'] = status
        if priority:
            query['priority'] = priority
        if source_type:
            query['source_type'] = source_type
        
        return Task.get_all(query, page, per_page)
    
    @staticmethod
    def update(task_id, update_data):
        """Update task"""
        db = get_db()
        update_data['updated_at'] = datetime.utcnow()
        db.tasks.update_one(
            {'_id': ObjectId(task_id)},
            {'$set': update_data}
        )
        return Task.find_by_id(task_id)
    
    @staticmethod
    def delete(task_id):
        """Delete task"""
        db = get_db()
        result = db.tasks.delete_one({'_id': ObjectId(task_id)})
        return result.deleted_count > 0
    
    @staticmethod
    def find_by_email_id(message_id):
        """Find task created from specific email"""
        db = get_db()
        return db.tasks.find_one({'email_id': message_id})
    
    @staticmethod
    def serialize(task, include_users=True):
        """Serialize task object"""
        if not task:
            return None
        
        # Helper function to convert datetime to ISO format
        def to_isoformat(date_value):
            if not date_value:
                return None
            if isinstance(date_value, datetime):
                return date_value.isoformat()
            if isinstance(date_value, str):
                return date_value
            return None
        
        serialized = {
            'id': str(task['_id']),
            'title': task['title'],
            'description': task.get('description'),
            'priority': task['priority'],
            'status': task['status'],
            'deadline': to_isoformat(task.get('deadline')),
            'created_at': to_isoformat(task.get('created_at')),
            'updated_at': to_isoformat(task.get('updated_at'))
        }
        
        if include_users:
            # Get assigned_to user
            if task.get('assigned_to'):
                assigned_to = User.find_by_id(task['assigned_to'])
                serialized['assigned_to'] = User.serialize(assigned_to)
            
            # Get created_by user
            if task.get('created_by'):
                created_by = User.find_by_id(task['created_by'])
                serialized['created_by'] = User.serialize(created_by)
        else:
            serialized['assigned_to'] = str(task.get('assigned_to'))
            serialized['created_by'] = str(task.get('created_by'))
        
        # Email data
        if task.get('email_id'):
            serialized['email_id'] = task['email_id']
            serialized['sender_email'] = task.get('sender_email')
        
        # User email (for isolation)
        if task.get('user_email'):
            serialized['user_email'] = task['user_email']
        
        # Meeting data
        if task.get('meeting_id'):
            serialized['meeting_id'] = str(task['meeting_id'])
            serialized['meeting_title'] = task.get('meeting_title')
            if task.get('meeting_date'):
                serialized['meeting_date'] = to_isoformat(task['meeting_date'])
        
        # Source type
        serialized['source_type'] = task.get('source_type', 'manual')
            
        # Labels
        if task.get('labels'):
            serialized['labels'] = task['labels']
        
        return serialized
