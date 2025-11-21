"""Meeting model for Google Meet integration"""
from datetime import datetime
from bson import ObjectId
from app import get_db


class Meeting:
    """Meeting model for storing Google Calendar meetings with recordings"""
    
    collection_name = 'meetings'
    
    @staticmethod
    def create(calendar_event_id, user_id, title, description='', 
               start_time=None, end_time=None, attendees=None, 
               meet_link='', recording_url='', recording_id=''):
        """
        Create a new meeting record
        
        Args:
            calendar_event_id: Google Calendar event ID
            user_id: User ObjectId or string
            title: Meeting title
            description: Meeting description
            start_time: Meeting start datetime
            end_time: Meeting end datetime
            attendees: List of attendee dicts with email, name, response_status
            meet_link: Google Meet link
            recording_url: Google Drive URL for recording
            recording_id: Google Drive file ID
            
        Returns:
            Created meeting document
        """
        db = get_db()
        meeting = {
            'calendar_event_id': calendar_event_id,
            'user_id': ObjectId(user_id) if isinstance(user_id, str) else user_id,
            'title': title,
            'description': description or '',
            'start_time': start_time,
            'end_time': end_time,
            'attendees': attendees or [],
            'meet_link': meet_link,
            'recording_url': recording_url,
            'recording_id': recording_id,
            'processing_status': 'pending',  # pending, processing, completed, failed
            'processed_at': None,
            'error_message': None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        result = db.meetings.insert_one(meeting)
        meeting['_id'] = result.inserted_id
        return meeting
    
    @staticmethod
    def find_by_id(meeting_id):
        """Find meeting by ID"""
        db = get_db()
        return db.meetings.find_one({'_id': ObjectId(meeting_id)})
    
    @staticmethod
    def find_by_calendar_event_id(calendar_event_id, user_id):
        """Find meeting by calendar event ID and user"""
        db = get_db()
        return db.meetings.find_one({
            'calendar_event_id': calendar_event_id,
            'user_id': ObjectId(user_id) if isinstance(user_id, str) else user_id
        })
    
    @staticmethod
    def get_user_meetings(user_id, status=None, page=1, per_page=20):
        """
        Get meetings for a specific user with optional filtering
        
        Args:
            user_id: User ID
            status: Optional processing status filter
            page: Page number
            per_page: Items per page
            
        Returns:
            Dict with meetings list and pagination info
        """
        db = get_db()
        query = {'user_id': ObjectId(user_id) if isinstance(user_id, str) else user_id}
        
        if status:
            query['processing_status'] = status
        
        skip = (page - 1) * per_page
        meetings = list(db.meetings.find(query)
                       .sort('start_time', -1)
                       .skip(skip)
                       .limit(per_page))
        total = db.meetings.count_documents(query)
        
        return {
            'meetings': meetings,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page if total > 0 else 0
            }
        }
    
    @staticmethod
    def update_status(meeting_id, status, processed_at=None, error_message=None):
        """
        Update meeting processing status
        
        Args:
            meeting_id: Meeting ID
            status: New status (pending, processing, completed, failed)
            processed_at: Optional processing completion datetime
            error_message: Optional error message if failed
            
        Returns:
            Updated meeting document
        """
        db = get_db()
        update_data = {
            'processing_status': status,
            'updated_at': datetime.utcnow()
        }
        
        if processed_at:
            update_data['processed_at'] = processed_at
        if error_message:
            update_data['error_message'] = error_message
        
        db.meetings.update_one(
            {'_id': ObjectId(meeting_id)},
            {'$set': update_data}
        )
        return Meeting.find_by_id(meeting_id)
    
    @staticmethod
    def update_recording_info(meeting_id, recording_url, recording_id):
        """Update meeting recording information"""
        db = get_db()
        db.meetings.update_one(
            {'_id': ObjectId(meeting_id)},
            {'$set': {
                'recording_url': recording_url,
                'recording_id': recording_id,
                'updated_at': datetime.utcnow()
            }}
        )
        return Meeting.find_by_id(meeting_id)
    
    @staticmethod
    def get_pending_meetings(limit=10):
        """
        Get meetings pending processing (have recordings but not processed)
        
        Args:
            limit: Maximum number of meetings to return
            
        Returns:
            List of pending meeting documents
        """
        db = get_db()
        return list(db.meetings.find({
            'processing_status': 'pending',
            'recording_id': {'$ne': None, '$ne': ''}
        }).limit(limit))
    
    @staticmethod
    def delete(meeting_id):
        """Delete a meeting"""
        db = get_db()
        result = db.meetings.delete_one({'_id': ObjectId(meeting_id)})
        return result.deleted_count > 0
    
    @staticmethod
    def serialize(meeting):
        """
        Serialize meeting object for API response
        
        Args:
            meeting: Meeting document from database
            
        Returns:
            Serialized meeting dict
        """
        if not meeting:
            return None
        
        return {
            'id': str(meeting['_id']),
            'calendar_event_id': meeting['calendar_event_id'],
            'user_id': str(meeting['user_id']),
            'title': meeting['title'],
            'description': meeting.get('description'),
            'start_time': meeting['start_time'].isoformat() if meeting.get('start_time') else None,
            'end_time': meeting['end_time'].isoformat() if meeting.get('end_time') else None,
            'attendees': meeting.get('attendees', []),
            'meet_link': meeting.get('meet_link'),
            'recording_url': meeting.get('recording_url'),
            'recording_id': meeting.get('recording_id'),
            'processing_status': meeting['processing_status'],
            'processed_at': meeting['processed_at'].isoformat() if meeting.get('processed_at') else None,
            'error_message': meeting.get('error_message'),
            'created_at': meeting['created_at'].isoformat() if meeting.get('created_at') else None,
            'updated_at': meeting['updated_at'].isoformat() if meeting.get('updated_at') else None
        }
