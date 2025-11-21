from datetime import datetime
from bson import ObjectId
from app import get_db

class ProcessedEmail:
    """Model to track processed emails to prevent duplicates"""
    
    collection_name = 'processed_emails'
    
    @staticmethod
    def mark_as_processed(email_id, user_id, tasks_created=0):
        """Mark an email as processed"""
        db = get_db()
        processed_email = {
            'email_id': email_id,
            'user_id': ObjectId(user_id),
            'tasks_created': tasks_created,
            'processed_at': datetime.utcnow()
        }
        db.processed_emails.insert_one(processed_email)
        return processed_email
    
    @staticmethod
    def is_processed(email_id, user_id):
        """Check if an email has already been processed"""
        db = get_db()
        return db.processed_emails.find_one({
            'email_id': email_id,
            'user_id': ObjectId(user_id)
        }) is not None
    
    @staticmethod
    def get_processed_count(user_id):
        """Get count of processed emails for a user"""
        db = get_db()
        return db.processed_emails.count_documents({
            'user_id': ObjectId(user_id)
        })
    
    @staticmethod
    def cleanup_old_entries(days=30):
        """Remove old processed email records (older than specified days)"""
        db = get_db()
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = db.processed_emails.delete_many({
            'processed_at': {'$lt': cutoff_date}
        })
        return result.deleted_count
