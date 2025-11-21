"""Meeting transcript model"""
from datetime import datetime
from bson import ObjectId
from app import get_db


class MeetingTranscript:
    """Model for storing meeting transcripts from Speech-to-Text API"""
    
    collection_name = 'meeting_transcripts'
    
    @staticmethod
    def create(meeting_id, user_id, transcript_text, transcript_segments=None, 
               language='en', confidence=0.0):
        """
        Create a new meeting transcript
        
        Args:
            meeting_id: Meeting ObjectId or string
            user_id: User ObjectId or string
            transcript_text: Full transcript text
            transcript_segments: List of transcript segments with speaker info
            language: Language code (e.g., 'en-US')
            confidence: Overall confidence score (0.0-1.0)
            
        Returns:
            Created transcript document
        """
        db = get_db()
        transcript = {
            'meeting_id': ObjectId(meeting_id) if isinstance(meeting_id, str) else meeting_id,
            'user_id': ObjectId(user_id) if isinstance(user_id, str) else user_id,
            'transcript_text': transcript_text,
            'transcript_segments': transcript_segments or [],
            'language': language,
            'confidence': confidence,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        result = db.meeting_transcripts.insert_one(transcript)
        transcript['_id'] = result.inserted_id
        return transcript
    
    @staticmethod
    def find_by_meeting_id(meeting_id):
        """Find transcript by meeting ID"""
        db = get_db()
        return db.meeting_transcripts.find_one({
            'meeting_id': ObjectId(meeting_id) if isinstance(meeting_id, str) else meeting_id
        })
    
    @staticmethod
    def find_by_id(transcript_id):
        """Find transcript by ID"""
        db = get_db()
        return db.meeting_transcripts.find_one({'_id': ObjectId(transcript_id)})
    
    @staticmethod
    def delete(transcript_id):
        """Delete a transcript"""
        db = get_db()
        result = db.meeting_transcripts.delete_one({'_id': ObjectId(transcript_id)})
        return result.deleted_count > 0
    
    @staticmethod
    def delete_by_meeting_id(meeting_id):
        """Delete transcript by meeting ID"""
        db = get_db()
        result = db.meeting_transcripts.delete_one({
            'meeting_id': ObjectId(meeting_id) if isinstance(meeting_id, str) else meeting_id
        })
        return result.deleted_count > 0
    
    @staticmethod
    def serialize(transcript):
        """
        Serialize transcript object for API response
        
        Args:
            transcript: Transcript document from database
            
        Returns:
            Serialized transcript dict
        """
        if not transcript:
            return None
        
        return {
            'id': str(transcript['_id']),
            'meeting_id': str(transcript['meeting_id']),
            'user_id': str(transcript['user_id']),
            'transcript_text': transcript['transcript_text'],
            'transcript_segments': transcript.get('transcript_segments', []),
            'language': transcript.get('language', 'en'),
            'confidence': transcript.get('confidence', 0.0),
            'created_at': transcript['created_at'].isoformat() if transcript.get('created_at') else None,
            'updated_at': transcript['updated_at'].isoformat() if transcript.get('updated_at') else None
        }
