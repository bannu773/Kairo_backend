"""Meeting polling and processing service"""
import threading
import time
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from flask import current_app
import logging

from app.models.user import User
from app.models.meeting import Meeting
from app.models.meeting_transcript import MeetingTranscript
from app.models.meeting_summary import MeetingSummary
from app.models.task import Task
from app.services.calendar_service import CalendarService
from app.services.drive_service import DriveService
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class MeetingPollingService:
    """Service for polling Google Calendar for meetings and processing recordings"""
    
    def __init__(self, app=None):
        self.app = app
        self.polling_thread = None
        self.is_running = False
        self.poll_interval = int(os.getenv('MEETING_POLL_INTERVAL', 300))  # 5 minutes default
        self.gemini_service = None
        
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        
    def start_polling(self):
        """Start the meeting polling service"""
        if self.is_running:
            logger.info("Meeting polling service is already running")
            return
            
        self.is_running = True
        self.polling_thread = threading.Thread(target=self._poll_meetings, daemon=True)
        self.polling_thread.start()
        logger.info(f"✅ Meeting polling service started - checking every {self.poll_interval} seconds")
        
    def stop_polling(self):
        """Stop the meeting polling service"""
        self.is_running = False
        if self.polling_thread:
            self.polling_thread.join(timeout=10)
        logger.info("❌ Meeting polling service stopped")
        
    def _poll_meetings(self):
        """Main polling loop"""
        logger.info("🔄 Meeting polling loop started...")
        
        while self.is_running:
            try:
                with self.app.app_context():
                    self._check_all_users_for_meetings()
                    # Note: Processing is handled via manual trigger or separate async job
            except Exception as e:
                logger.error(f"❌ Error in meeting polling: {e}", exc_info=True)
                
            # Wait before next poll
            for _ in range(self.poll_interval):
                if not self.is_running:
                    break
                time.sleep(1)
                
        logger.info("🛑 Meeting polling loop ended")
        
    def _check_all_users_for_meetings(self):
        """Check all users for new meetings"""
        try:
            # Get all users with calendar tokens
            users = User.get_users_with_calendar_tokens()
            
            if not users:
                return
                
            logger.info(f"📅 Checking meetings for {len(users)} users...")
            
            for user in users:
                try:
                    self._check_user_meetings(user)
                except Exception as e:
                    logger.error(f"❌ Error checking meetings for user {user.get('email', 'unknown')}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error getting users with calendar tokens: {e}")
    
    def _check_user_meetings(self, user):
        """Check meetings for a specific user"""
        try:
            # Get Calendar service for user
            calendar_service = CalendarService.get_service_for_user(user)
            if not calendar_service:
                return
                
            # Get the last check time (default to 7 days ago)
            last_check = user.get('last_meeting_check')
            if not last_check:
                last_check = datetime.utcnow() - timedelta(days=7)
            elif isinstance(last_check, str):
                last_check = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
                
            # Get past Meet events that might have recordings
            meetings = calendar_service.get_past_meet_events_with_recordings(days_back=7)
            
            if not meetings:
                User.update_last_meeting_check(str(user['_id']))
                return
                
            logger.info(f"📅 Found {len(meetings)} Meet events for {user.get('email')}")
            
            # Process each meeting
            new_meetings_count = 0
            for meeting_data in meetings:
                try:
                    # Check if meeting already exists
                    existing = Meeting.find_by_calendar_event_id(
                        meeting_data['calendar_event_id'],
                        str(user['_id'])
                    )
                    
                    if existing:
                        continue
                    
                    # Create new meeting record
                    meeting = Meeting.create(
                        calendar_event_id=meeting_data['calendar_event_id'],
                        user_id=str(user['_id']),
                        title=meeting_data['title'],
                        description=meeting_data['description'],
                        start_time=meeting_data['start_time'],
                        end_time=meeting_data['end_time'],
                        attendees=meeting_data['attendees'],
                        meet_link=meeting_data['meet_link']
                    )
                    
                    new_meetings_count += 1
                    logger.info(f"   ✅ Added meeting: {meeting_data['title']}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing meeting: {e}")
                    
            # Update last check time
            User.update_last_meeting_check(str(user['_id']))
            
            if new_meetings_count > 0:
                logger.info(f"✅ Added {new_meetings_count} new meetings for {user.get('email')}")
                
        except Exception as e:
            logger.error(f"❌ Error in _check_user_meetings: {e}", exc_info=True)
    
    def process_meeting(self, meeting):
        """
        Process a single meeting: transcribe, summarize, extract tasks
        
        Args:
            meeting: Meeting document from database
            
        Returns:
            True if successful, False otherwise
        """
        try:
            meeting_id = str(meeting['_id'])
            user_id = str(meeting['user_id'])
            
            logger.info(f"🎬 Processing meeting: {meeting['title']}")
            
            # Initialize Gemini service
            if not self.gemini_service:
                self.gemini_service = GeminiService()
            
            # Update status to processing
            Meeting.update_status(meeting_id, 'processing')
            
            # Get user for Drive credentials
            user = User.find_by_id(user_id)
            if not user:
                raise Exception("User not found")
            
            # Step 1: Search for transcript or Gemini notes in Google Drive
            logger.info(f"  📁 Searching for transcript/notes in Google Drive...")
            drive_service = DriveService.get_service_for_user(user)
            
            if not drive_service:
                logger.error("  ❌ Drive service not available. Cannot process meeting without transcript/notes.")
                Meeting.update_status(meeting_id, 'failed', error_message='Drive service not available')
                return False
            
            # Search for transcript or Gemini notes by meeting title and date
            meeting_date = meeting['start_time']
            if isinstance(meeting_date, str):
                meeting_date = datetime.fromisoformat(meeting_date.replace('Z', '+00:00'))
            
            transcript_file = drive_service.find_meeting_recording(
                meeting_title=meeting['title'],
                meeting_date=meeting_date
            )
            
            if not transcript_file:
                logger.error(f"  ❌ No transcript or Gemini notes found for meeting: {meeting['title']}")
                Meeting.update_status(meeting_id, 'failed', error_message='No transcript or Gemini notes found in Google Drive')
                return False
            
            # Step 2: Get transcript/notes text from Google Doc
            logger.info(f"  📝 Reading content: {transcript_file['name']}")
            transcript_text = drive_service.get_document_text(transcript_file['id'])
            
            if not transcript_text:
                logger.error("  ❌ Failed to read transcript/notes content")
                Meeting.update_status(meeting_id, 'failed', error_message='Failed to read transcript/notes content')
                return False
            
            logger.info(f"  ✅ Content retrieved ({len(transcript_text)} characters)")
            
            # Prepare transcript data (Gemini notes are already formatted nicely)
            transcript_data = {
                'transcript_text': transcript_text,
                'transcript_segments': [],  # Google Docs don't have speaker segments
                'language': 'en-US',  # Default
                'confidence': 1.0  # Human/AI-generated content
            }
            
            # Save transcript
            transcript = MeetingTranscript.create(
                meeting_id=meeting_id,
                user_id=user_id,
                transcript_text=transcript_data['transcript_text'],
                transcript_segments=transcript_data['transcript_segments'],
                language=transcript_data['language'],
                confidence=transcript_data['confidence']
            )
            
            logger.info(f"  ✅ Transcript saved")
            
            # Summarize with Gemini
            logger.info(f"  🤖 Generating summary with AI...")
            summary_data = self.gemini_service.summarize_meeting_transcript(
                transcript_text=transcript_data['transcript_text'],
                meeting_title=meeting['title'],
                attendees=meeting.get('attendees', [])
            )
            
            if not summary_data:
                raise Exception("Failed to generate summary")
            
            # Save summary
            summary = MeetingSummary.create(
                meeting_id=meeting_id,
                user_id=user_id,
                summary=summary_data['summary'],
                key_points=summary_data.get('key_points', []),
                decisions_made=summary_data.get('decisions_made', []),
                action_items=summary_data.get('action_items', []),
                participants_mentioned=summary_data.get('participants_mentioned', []),
                topics_discussed=summary_data.get('topics_discussed', []),
                next_meeting=summary_data.get('next_meeting')
            )
            
            logger.info(f"  ✅ Summary saved")
            
            # Create tasks from action items
            tasks_created = 0
            for idx, action_item in enumerate(summary_data.get('action_items', [])):
                try:
                    task = Task.create(
                        title=action_item['description'][:100],
                        description=action_item.get('context', action_item['description']),
                        priority=action_item.get('priority', 'medium'),
                        deadline=action_item.get('deadline'),
                        assigned_to=user_id,  # Default to meeting owner
                        created_by=user_id,
                        user_email=user.get('email'),  # CRITICAL FIX: Store which user owns this meeting task
                        status='pending',
                        source_type='meeting',
                        meeting_id=meeting_id,
                        meeting_title=meeting['title'],
                        meeting_date=meeting['start_time']
                    )
                    
                    # Update summary with task ID
                    MeetingSummary.update_task_id(meeting_id, idx, str(task['_id']))
                    
                    tasks_created += 1
                    logger.info(f"   ✅ Created task: {action_item['description'][:50]}...")
                    
                except Exception as e:
                    logger.error(f"   ❌ Failed to create task: {e}")
            
            # Update meeting status
            Meeting.update_status(meeting_id, 'completed', processed_at=datetime.utcnow())
            
            logger.info(f"✅ Meeting processed successfully. Created {tasks_created} tasks.")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing meeting: {e}", exc_info=True)
            # Update meeting status to failed
            try:
                Meeting.update_status(
                    str(meeting['_id']), 
                    'failed', 
                    error_message=str(e)
                )
            except:
                pass
            return False


# Global instance
meeting_polling_service = MeetingPollingService()
