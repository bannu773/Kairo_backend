import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # MongoDB
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/task_manager')
    MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'task_manager')
    
    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/api/auth/callback')
    
    # Gemini API
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # URLs
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')
    
    # Gmail API
    GMAIL_SCOPES = os.getenv('GMAIL_SCOPES', 
        'openid,'
        'https://www.googleapis.com/auth/userinfo.email,'
        'https://www.googleapis.com/auth/userinfo.profile,'
        'https://www.googleapis.com/auth/gmail.readonly'
    ).split(',')
    
    # Google Calendar API
    CALENDAR_SCOPES = [
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar.events.readonly'
    ]
    
    # Google Drive API
    DRIVE_SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.metadata.readonly'
    ]
    
    # Combined Google Scopes
    ALL_GOOGLE_SCOPES = (
        GMAIL_SCOPES + 
        CALENDAR_SCOPES + 
        DRIVE_SCOPES
    )
    
    # Google Cloud credentials for Speech-to-Text
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    # Meeting processing settings
    MEETING_POLL_INTERVAL = int(os.getenv('MEETING_POLL_INTERVAL', 300))  # 5 minutes
    MAX_MEETINGS_PER_POLL = int(os.getenv('MAX_MEETINGS_PER_POLL', 5))
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 86400)))
    
    # Email Sync
    EMAIL_SYNC_INTERVAL = int(os.getenv('EMAIL_SYNC_INTERVAL', 300))
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # Flask-RESTX
    RESTX_MASK_SWAGGER = False
    ERROR_404_HELP = False


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
