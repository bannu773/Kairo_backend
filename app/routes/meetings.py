"""Meeting API routes"""
from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from bson import ObjectId
import logging

from app.models.meeting import Meeting
from app.models.meeting_transcript import MeetingTranscript
from app.models.meeting_summary import MeetingSummary
from app.models.user import User
from app.models.task import Task
from app.services.calendar_service import CalendarService
from app.services.meeting_polling_service import meeting_polling_service
from app import get_db

logger = logging.getLogger(__name__)

api = Namespace('meetings', description='Meeting operations')

# Swagger models
attendee_model = api.model('Attendee', {
    'email': fields.String(description='Attendee email'),
    'name': fields.String(description='Attendee name'),
    'response_status': fields.String(description='Response status')
})

meeting_model = api.model('Meeting', {
    'id': fields.String(description='Meeting ID'),
    'calendar_event_id': fields.String(description='Calendar event ID'),
    'title': fields.String(description='Meeting title'),
    'description': fields.String(description='Meeting description'),
    'start_time': fields.DateTime(description='Start time'),
    'end_time': fields.DateTime(description='End time'),
    'attendees': fields.List(fields.Nested(attendee_model)),
    'meet_link': fields.String(description='Google Meet link'),
    'recording_url': fields.String(description='Recording URL'),
    'processing_status': fields.String(description='Processing status'),
    'processed_at': fields.DateTime(description='Processing completion time'),
    'created_at': fields.DateTime(description='Creation timestamp')
})

action_item_model = api.model('ActionItem', {
    'description': fields.String(description='Action item description'),
    'assigned_to': fields.String(description='Assigned person'),
    'priority': fields.String(description='Priority'),
    'deadline': fields.String(description='Deadline'),
    'task_id': fields.String(description='Created task ID')
})

summary_model = api.model('MeetingSummary', {
    'id': fields.String(description='Summary ID'),
    'meeting_id': fields.String(description='Meeting ID'),
    'summary': fields.String(description='Meeting summary'),
    'key_points': fields.List(fields.String, description='Key points'),
    'decisions_made': fields.List(fields.String, description='Decisions made'),
    'action_items': fields.List(fields.Nested(action_item_model)),
    'topics_discussed': fields.List(fields.String, description='Topics discussed'),
    'participants_mentioned': fields.List(fields.String, description='Participants mentioned')
})


@api.route('')
class MeetingList(Resource):
    @api.doc('get_meetings', security='Bearer')
    @api.param('status', 'Filter by processing status')
    @api.param('page', 'Page number', type=int, default=1)
    @api.param('per_page', 'Items per page', type=int, default=20)
    @jwt_required()
    def get(self):
        """Get all meetings for current user"""
        try:
            user_id = get_jwt_identity()
            
            # Get query parameters
            status = request.args.get('status')
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 20))
            
            # Get meetings
            result = Meeting.get_user_meetings(
                user_id=user_id,
                status=status,
                page=page,
                per_page=per_page
            )
            
            # Serialize meetings
            meetings = [Meeting.serialize(meeting) for meeting in result['meetings']]
            
            return {
                'success': True,
                'data': {
                    'meetings': meetings,
                    'pagination': result['pagination']
                }
            }, 200
            
        except Exception as e:
            logger.error(f"Error getting meetings: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}, 500


@api.route('/<string:meeting_id>')
class MeetingDetail(Resource):
    @api.doc('get_meeting', security='Bearer')
    @jwt_required()
    def get(self, meeting_id):
        """Get a specific meeting"""
        try:
            user_id = get_jwt_identity()
            meeting = Meeting.find_by_id(meeting_id)
            
            if not meeting:
                return {'success': False, 'error': 'Meeting not found'}, 404
            
            # Check if user has access
            if str(meeting['user_id']) != user_id:
                return {'success': False, 'error': 'Access denied'}, 403
            
            return {
                'success': True,
                'data': Meeting.serialize(meeting)
            }, 200
            
        except Exception as e:
            logger.error(f"Error getting meeting: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}, 500


@api.route('/<string:meeting_id>/transcript')
class MeetingTranscriptResource(Resource):
    @api.doc('get_transcript', security='Bearer')
    @jwt_required()
    def get(self, meeting_id):
        """Get meeting transcript"""
        try:
            user_id = get_jwt_identity()
            meeting = Meeting.find_by_id(meeting_id)
            
            if not meeting:
                return {'success': False, 'error': 'Meeting not found'}, 404
            
            if str(meeting['user_id']) != user_id:
                return {'success': False, 'error': 'Access denied'}, 403
            
            # Get transcript
            transcript = MeetingTranscript.find_by_meeting_id(meeting_id)
            
            if not transcript:
                return {'success': False, 'error': 'Transcript not available yet'}, 404
            
            return {
                'success': True,
                'data': MeetingTranscript.serialize(transcript)
            }, 200
            
        except Exception as e:
            logger.error(f"Error getting transcript: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}, 500


@api.route('/<string:meeting_id>/summary')
class MeetingSummaryResource(Resource):
    @api.doc('get_summary', security='Bearer')
    @jwt_required()
    def get(self, meeting_id):
        """Get meeting summary"""
        try:
            user_id = get_jwt_identity()
            meeting = Meeting.find_by_id(meeting_id)
            
            if not meeting:
                return {'success': False, 'error': 'Meeting not found'}, 404
            
            if str(meeting['user_id']) != user_id:
                return {'success': False, 'error': 'Access denied'}, 403
            
            # Get summary
            summary = MeetingSummary.find_by_meeting_id(meeting_id)
            
            if not summary:
                return {'success': False, 'error': 'Summary not available yet'}, 404
            
            return {
                'success': True,
                'data': MeetingSummary.serialize(summary)
            }, 200
            
        except Exception as e:
            logger.error(f"Error getting summary: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}, 500


@api.route('/sync')
class MeetingSync(Resource):
    @api.doc('sync_meetings', security='Bearer')
    @jwt_required()
    def post(self):
        """Manually trigger meeting synchronization"""
        try:
            user_id = get_jwt_identity()
            user = User.find_by_id(user_id)
            
            if not user:
                return {'success': False, 'error': 'User not found'}, 404
            
            # Check if user has Calendar token
            if not user.get('calendar_tokens'):
                return {
                    'success': False,
                    'error': 'Google Calendar not connected. Please reconnect your Google account with Calendar permissions.'
                }, 400
            
            # Initialize service
            calendar_service = CalendarService.get_service_for_user(user)
            
            if not calendar_service:
                return {
                    'success': False,
                    'error': 'Failed to initialize Calendar service'
                }, 500
            
            # Get recent Meet events
            meetings = calendar_service.get_past_meet_events_with_recordings(days_back=14)
            
            processed_count = 0
            new_count = 0
            
            for meeting_data in meetings:
                try:
                    # Check if meeting already exists
                    existing = Meeting.find_by_calendar_event_id(
                        meeting_data['calendar_event_id'],
                        user_id
                    )
                    
                    if existing:
                        processed_count += 1
                        continue
                    
                    # Create new meeting record
                    Meeting.create(
                        calendar_event_id=meeting_data['calendar_event_id'],
                        user_id=user_id,
                        title=meeting_data['title'],
                        description=meeting_data['description'],
                        start_time=meeting_data['start_time'],
                        end_time=meeting_data['end_time'],
                        attendees=meeting_data['attendees'],
                        meet_link=meeting_data['meet_link']
                    )
                    
                    new_count += 1
                    
                except Exception as e:
                    logger.error(f"Error syncing meeting: {e}")
            
            return {
                'success': True,
                'data': {
                    'new_meetings': new_count,
                    'existing_meetings': processed_count
                },
                'message': f'Synced {new_count} new meetings'
            }, 200
            
        except Exception as e:
            logger.error(f"Error syncing meetings: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}, 500


@api.route('/<string:meeting_id>/process')
class MeetingProcess(Resource):
    @api.doc('process_meeting', security='Bearer')
    @jwt_required()
    def post(self, meeting_id):
        """Manually trigger processing for a specific meeting"""
        try:
            user_id = get_jwt_identity()
            meeting = Meeting.find_by_id(meeting_id)
            
            if not meeting:
                return {'success': False, 'error': 'Meeting not found'}, 404
            
            if str(meeting['user_id']) != user_id:
                return {'success': False, 'error': 'Access denied'}, 403
            
            if meeting.get('processing_status') == 'processing':
                return {
                    'success': False,
                    'error': 'Meeting is already being processed'
                }, 400
            
            # Process in background thread
            import threading
            
            def process_in_background():
                with meeting_polling_service.app.app_context():
                    try:
                        meeting_polling_service.process_meeting(meeting)
                    except Exception as e:
                        logger.error(f"Error processing meeting in background: {e}", exc_info=True)
            
            thread = threading.Thread(target=process_in_background, daemon=True)
            thread.start()
            
            # Update status immediately
            Meeting.update_status(meeting_id, 'processing')
            
            return {
                'success': True,
                'message': 'Meeting processing started. This may take a few minutes.'
            }, 202  # Accepted
            
        except Exception as e:
            logger.error(f"Error triggering meeting process: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}, 500


@api.route('/polling/status')
class MeetingPollingStatus(Resource):
    @api.doc('meeting_polling_status', security='Bearer')
    @jwt_required()
    def get(self):
        """Get meeting polling service status"""
        try:
            return {
                'success': True,
                'data': {
                    'is_running': meeting_polling_service.is_running,
                    'poll_interval': meeting_polling_service.poll_interval,
                    'message': 'Meeting polling is active' if meeting_polling_service.is_running else 'Meeting polling is not running'
                }
            }, 200
            
        except Exception as e:
            logger.error(f"Error getting polling status: {e}")
            return {'success': False, 'error': str(e)}, 500


@api.route('/stats')
class MeetingStats(Resource):
    @api.doc('meeting_stats', security='Bearer')
    @jwt_required()
    def get(self):
        """Get meeting statistics for current user"""
        try:
            user_id = get_jwt_identity()
            db = get_db()
            
            total = db.meetings.count_documents({'user_id': ObjectId(user_id)})
            completed = db.meetings.count_documents({
                'user_id': ObjectId(user_id),
                'processing_status': 'completed'
            })
            pending = db.meetings.count_documents({
                'user_id': ObjectId(user_id),
                'processing_status': 'pending'
            })
            processing = db.meetings.count_documents({
                'user_id': ObjectId(user_id),
                'processing_status': 'processing'
            })
            failed = db.meetings.count_documents({
                'user_id': ObjectId(user_id),
                'processing_status': 'failed'
            })
            
            return {
                'success': True,
                'data': {
                    'total': total,
                    'completed': completed,
                    'pending': pending,
                    'processing': processing,
                    'failed': failed
                }
            }, 200
            
        except Exception as e:
            logger.error(f"Error getting meeting stats: {e}")
            return {'success': False, 'error': str(e)}, 500
