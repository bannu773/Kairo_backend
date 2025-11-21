from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_restx import Api
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize extensions
jwt = JWTManager()
mongo_client = None
db = None

def create_app(config_name='default'):
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    from app.config import config
    app.config.from_object(config[config_name])
    
    # Initialize CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config['CORS_ORIGINS'],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Initialize JWT
    jwt.init_app(app)
    
    # Initialize MongoDB
    global mongo_client, db
    mongo_uri = app.config['MONGODB_URI']
    mongo_client = MongoClient(mongo_uri)
    
    # Extract database name from URI or use default
    # For mongodb+srv://user:pass@host/dbname?params format
    if '/' in mongo_uri.split('@')[-1]:
        db_name = mongo_uri.split('/')[-1].split('?')[0]
    else:
        db_name = ''
    
    # If no database name in URI, use default
    if not db_name:
        db_name = app.config.get('MONGODB_DATABASE', 'task_manager')
    
    db = mongo_client[db_name]
    print(f"Connected to MongoDB database: {db_name}")
    
    # Create indexes
    create_indexes()
    
    # Initialize Flask-RESTX API
    api = Api(
        app,
        version='1.0',
        title='Task Manager API',
        description='Task Management System with Gmail & Gemini Integration',
        doc='/api/docs',
        prefix='/api'
    )
    
    # Register namespaces
    from app.routes.auth import api as auth_ns
    from app.routes.tasks import api as tasks_ns
    from app.routes.users import api as users_ns
    from app.routes.health import api as health_ns
    from app.routes.meetings import api as meetings_ns
    
    api.add_namespace(auth_ns, path='/auth')
    api.add_namespace(tasks_ns, path='/tasks')
    api.add_namespace(users_ns, path='/users')
    api.add_namespace(health_ns, path='')
    api.add_namespace(meetings_ns, path='/meetings')
    
    # Initialize email polling service
    from app.services.email_polling_service import email_polling_service
    email_polling_service.init_app(app)
    
    # Initialize meeting polling service
    from app.services.meeting_polling_service import meeting_polling_service
    meeting_polling_service.init_app(app)
    
    # Start email polling service after app creation
    with app.app_context():
        try:
            # Start polling in a separate thread
            import threading
            def delayed_start():
                import time
                time.sleep(2)  # Wait 2 seconds for app to fully start
                email_polling_service.start_polling()
                meeting_polling_service.start_polling()
            
            threading.Thread(target=delayed_start, daemon=True).start()
        except Exception as e:
            print(f"Warning: Could not start polling services: {e}")
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'success': False, 'error': 'Resource not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'success': False, 'error': 'Internal server error'}, 500
    
    return app


def create_indexes():
    """Create database indexes"""
    # User indexes
    db.users.create_index('email', unique=True)
    
    # Task indexes
    db.tasks.create_index('assigned_to')
    db.tasks.create_index('assigned_by')
    db.tasks.create_index('status')
    db.tasks.create_index('priority')
    db.tasks.create_index([('deadline', -1)])
    db.tasks.create_index([('created_at', -1)])
    db.tasks.create_index('email_id')
    db.tasks.create_index('meeting_id')
    db.tasks.create_index('source_type')
    db.tasks.create_index('user_email')  # NEW: Index for user email isolation
    
    # Processed emails indexes (for duplicate prevention)
    # First, try to drop existing index and clean duplicates
    try:
        # Drop the index if it exists
        db.processed_emails.drop_index('email_id_1_user_id_1')
    except:
        pass  # Index doesn't exist, that's fine
    
    # Clean up duplicates before creating unique index
    try:
        pipeline = [
            {'$group': {
                '_id': {'email_id': '$email_id', 'user_id': '$user_id'},
                'count': {'$sum': 1},
                'docs': {'$push': '$_id'}
            }},
            {'$match': {'count': {'$gt': 1}}}
        ]
        duplicates = list(db.processed_emails.aggregate(pipeline))
        for dup in duplicates:
            # Keep first, remove rest
            for doc_id in dup['docs'][1:]:
                db.processed_emails.delete_one({'_id': doc_id})
        if duplicates:
            print(f"Cleaned up {sum(len(d['docs'])-1 for d in duplicates)} duplicate processed_emails")
    except Exception as e:
        print(f"Warning during duplicate cleanup: {e}")
    
    # Now create the unique index
    db.processed_emails.create_index([('email_id', 1), ('user_id', 1)], unique=True)
    db.processed_emails.create_index([('processed_at', -1)])  # For cleanup
    
    # Meeting indexes
    db.meetings.create_index([('calendar_event_id', 1), ('user_id', 1)], unique=True)
    db.meetings.create_index('user_id')
    db.meetings.create_index('processing_status')
    db.meetings.create_index([('start_time', -1)])
    db.meetings.create_index([('created_at', -1)])
    
    # Meeting transcript indexes
    db.meeting_transcripts.create_index('meeting_id', unique=True)
    db.meeting_transcripts.create_index([('created_at', -1)])
    
    # Meeting summary indexes
    db.meeting_summaries.create_index('meeting_id', unique=True)
    db.meeting_summaries.create_index([('created_at', -1)])


def get_db():
    """Get database instance"""
    return db
