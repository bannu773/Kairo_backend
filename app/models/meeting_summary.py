"""Meeting summary model"""
from datetime import datetime
from bson import ObjectId
from app import get_db


class MeetingSummary:
    """Model for storing AI-generated meeting summaries"""
    
    collection_name = 'meeting_summaries'
    
    @staticmethod
    def create(meeting_id, user_id, summary, key_points=None, 
               decisions_made=None, action_items=None, 
               participants_mentioned=None, topics_discussed=None, next_meeting=None):
        """
        Create a new meeting summary
        
        Args:
            meeting_id: Meeting ObjectId or string
            user_id: User ObjectId or string
            summary: Summary text
            key_points: List of key points
            decisions_made: List of decisions
            action_items: List of action item dicts
            participants_mentioned: List of participant names/emails
            topics_discussed: List of topics
            next_meeting: Dict with next meeting info
            
        Returns:
            Created summary document
        """
        db = get_db()
        summary_doc = {
            'meeting_id': ObjectId(meeting_id) if isinstance(meeting_id, str) else meeting_id,
            'user_id': ObjectId(user_id) if isinstance(user_id, str) else user_id,
            'summary': summary,
            'key_points': key_points or [],
            'decisions_made': decisions_made or [],
            'action_items': action_items or [],
            'participants_mentioned': participants_mentioned or [],
            'topics_discussed': topics_discussed or [],
            'next_meeting': next_meeting,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        result = db.meeting_summaries.insert_one(summary_doc)
        summary_doc['_id'] = result.inserted_id
        return summary_doc
    
    @staticmethod
    def find_by_meeting_id(meeting_id):
        """Find summary by meeting ID"""
        db = get_db()
        return db.meeting_summaries.find_one({
            'meeting_id': ObjectId(meeting_id) if isinstance(meeting_id, str) else meeting_id
        })
    
    @staticmethod
    def find_by_id(summary_id):
        """Find summary by ID"""
        db = get_db()
        return db.meeting_summaries.find_one({'_id': ObjectId(summary_id)})
    
    @staticmethod
    def update_task_id(meeting_id, action_item_index, task_id):
        """
        Update task ID for an action item
        
        Args:
            meeting_id: Meeting ID
            action_item_index: Index of action item in array
            task_id: Task ObjectId or string
        """
        db = get_db()
        db.meeting_summaries.update_one(
            {'meeting_id': ObjectId(meeting_id) if isinstance(meeting_id, str) else meeting_id},
            {'$set': {
                f'action_items.{action_item_index}.task_id': ObjectId(task_id) if isinstance(task_id, str) else task_id,
                'updated_at': datetime.utcnow()
            }}
        )
    
    @staticmethod
    def delete(summary_id):
        """Delete a summary"""
        db = get_db()
        result = db.meeting_summaries.delete_one({'_id': ObjectId(summary_id)})
        return result.deleted_count > 0
    
    @staticmethod
    def delete_by_meeting_id(meeting_id):
        """Delete summary by meeting ID"""
        db = get_db()
        result = db.meeting_summaries.delete_one({
            'meeting_id': ObjectId(meeting_id) if isinstance(meeting_id, str) else meeting_id
        })
        return result.deleted_count > 0
    
    @staticmethod
    def serialize(summary):
        """
        Serialize summary object for API response
        
        Args:
            summary: Summary document from database
            
        Returns:
            Serialized summary dict
        """
        if not summary:
            return None
        
        # Serialize action items with task_id converted to string
        action_items = []
        for item in summary.get('action_items', []):
            serialized_item = {**item}
            if 'task_id' in serialized_item and serialized_item['task_id']:
                serialized_item['task_id'] = str(serialized_item['task_id'])
            if 'deadline' in serialized_item and serialized_item['deadline']:
                if isinstance(serialized_item['deadline'], datetime):
                    serialized_item['deadline'] = serialized_item['deadline'].isoformat()
            action_items.append(serialized_item)
        
        return {
            'id': str(summary['_id']),
            'meeting_id': str(summary['meeting_id']),
            'user_id': str(summary['user_id']),
            'summary': summary['summary'],
            'key_points': summary.get('key_points', []),
            'decisions_made': summary.get('decisions_made', []),
            'action_items': action_items,
            'participants_mentioned': summary.get('participants_mentioned', []),
            'topics_discussed': summary.get('topics_discussed', []),
            'next_meeting': summary.get('next_meeting'),
            'created_at': summary['created_at'].isoformat() if summary.get('created_at') else None,
            'updated_at': summary['updated_at'].isoformat() if summary.get('updated_at') else None
        }
