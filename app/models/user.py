from datetime import datetime
from bson import ObjectId
from app import get_db

class User:
    """User model"""
    
    collection_name = 'users'
    
    @staticmethod
    def create(email, name, picture, google_id, role='user'):
        """Create a new user"""
        db = get_db()
        user = {
            'email': email,
            'name': name,
            'picture': picture,
            'google_id': google_id,
            'role': role,
            'gmail_refresh_token': None,
            'calendar_tokens': None,
            'drive_tokens': None,
            'last_email_check': None,
            'last_meeting_check': None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        result = db.users.insert_one(user)
        user['_id'] = result.inserted_id
        return user
    
    @staticmethod
    def find_by_id(user_id):
        """Find user by ID"""
        db = get_db()
        return db.users.find_one({'_id': ObjectId(user_id)})
    
    @staticmethod
    def find_by_email(email):
        """Find user by email"""
        db = get_db()
        return db.users.find_one({'email': email})
    
    @staticmethod
    def find_by_google_id(google_id):
        """Find user by Google ID"""
        db = get_db()
        return db.users.find_one({'google_id': google_id})
    
    @staticmethod
    def update(user_id, update_data):
        """Update user"""
        db = get_db()
        update_data['updated_at'] = datetime.utcnow()
        db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': update_data}
        )
        return User.find_by_id(user_id)
    
    @staticmethod
    def update_refresh_token(user_id, refresh_token):
        """Update Gmail refresh token"""
        return User.update(user_id, {'gmail_refresh_token': refresh_token})
    
    @staticmethod
    def get_all(filter_dict=None, page=1, per_page=10):
        """Get all users with pagination"""
        db = get_db()
        query = filter_dict or {}
        
        skip = (page - 1) * per_page
        users = list(db.users.find(query).skip(skip).limit(per_page))
        total = db.users.count_documents(query)
        
        return {
            'users': users,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }
    
    @staticmethod
    def update_role(user_id, role):
        """Update user role"""
        return User.update(user_id, {'role': role})
    
    @staticmethod
    def get_users_with_gmail_tokens():
        """Get all users who have Gmail refresh tokens"""
        db = get_db()
        return list(db.users.find({
            'gmail_refresh_token': {'$ne': None, '$exists': True}
        }))
    
    @staticmethod
    def update_last_email_check(user_id):
        """Update the last email check timestamp"""
        return User.update(user_id, {'last_email_check': datetime.utcnow()})
    
    @staticmethod
    def update_calendar_tokens(user_id, tokens):
        """Update user's Google Calendar tokens"""
        return User.update(user_id, {'calendar_tokens': tokens})
    
    @staticmethod
    def update_drive_tokens(user_id, tokens):
        """Update user's Google Drive tokens"""
        return User.update(user_id, {'drive_tokens': tokens})
    
    @staticmethod
    def update_last_meeting_check(user_id):
        """Update the last meeting check timestamp"""
        return User.update(user_id, {'last_meeting_check': datetime.utcnow()})
    
    @staticmethod
    def get_users_with_calendar_tokens():
        """Get all users who have Google Calendar tokens"""
        db = get_db()
        return list(db.users.find({
            'calendar_tokens': {'$ne': None, '$exists': True}
        }))
    
    @staticmethod
    def serialize(user):
        """Serialize user object"""
        if not user:
            return None
        
        return {
            'id': str(user['_id']),
            'email': user['email'],
            'name': user['name'],
            'picture': user.get('picture'),
            'role': user.get('role', 'user'),
            'has_gmail_connected': bool(user.get('gmail_refresh_token')),
            'has_calendar_connected': bool(user.get('calendar_tokens')),
            'has_drive_connected': bool(user.get('drive_tokens')),
            'created_at': user['created_at'].isoformat() if user.get('created_at') else None
        }
