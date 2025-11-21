"""Google Calendar API service"""
import os
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)


class CalendarService:
    """Service for interacting with Google Calendar API"""
    
    def __init__(self, credentials_dict):
        """
        Initialize Calendar service with credentials
        
        Args:
            credentials_dict: Dictionary containing access_token and refresh_token
        """
        scopes = [
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/calendar.events.readonly'
        ]
        
        self.credentials = Credentials(
            token=credentials_dict.get('access_token'),
            refresh_token=credentials_dict.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.getenv('GOOGLE_CLIENT_ID'),
            client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
            scopes=scopes
        )
        
        try:
            self.service = build('calendar', 'v3', credentials=self.credentials)
        except Exception as e:
            logger.error(f"Failed to build Calendar service: {e}")
            raise
    
    def get_upcoming_events(self, max_results=50, calendar_id='primary'):
        """
        Get upcoming calendar events
        
        Args:
            max_results: Maximum number of events to fetch
            calendar_id: Calendar ID (default 'primary')
            
        Returns:
            List of event dictionaries
        """
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
            
        except HttpError as error:
            logger.error(f'Calendar API error: {error}')
            return []
    
    def get_events_since(self, since_date, calendar_id='primary'):
        """
        Get events since a specific date
        
        Args:
            since_date: datetime object
            calendar_id: Calendar ID
            
        Returns:
            List of event dictionaries
        """
        try:
            time_min = since_date.isoformat() + 'Z'
            now = datetime.utcnow().isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=now,
                maxResults=100,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
            
        except HttpError as error:
            logger.error(f'Calendar API error: {error}')
            return []
    
    def get_past_meet_events_with_recordings(self, days_back=7):
        """
        Get past Meet events that might have recordings
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            List of parsed event dictionaries
        """
        try:
            time_min = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + 'Z'
            time_max = datetime.utcnow().isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=100,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            meet_events = []
            
            for event in events:
                if self._has_meet_link(event):
                    parsed_event = self._parse_event(event)
                    if parsed_event:
                        meet_events.append(parsed_event)
            
            return meet_events
            
        except HttpError as error:
            logger.error(f'Calendar API error: {error}')
            return []
    
    def _has_meet_link(self, event):
        """Check if event has a Google Meet link"""
        # Check conferenceData
        if 'conferenceData' in event:
            conf_data = event['conferenceData']
            if conf_data.get('conferenceSolution', {}).get('name') == 'Google Meet':
                return True
        
        # Check hangoutLink
        if 'hangoutLink' in event:
            return True
        
        # Check in description or location
        description = event.get('description', '').lower()
        location = event.get('location', '').lower()
        
        return 'meet.google.com' in description or 'meet.google.com' in location
    
    def _get_meet_link(self, event):
        """Extract Meet link from event"""
        # From conferenceData
        if 'conferenceData' in event:
            entry_points = event['conferenceData'].get('entryPoints', [])
            for entry in entry_points:
                if entry.get('entryPointType') == 'video':
                    return entry.get('uri')
        
        # From hangoutLink
        if 'hangoutLink' in event:
            return event['hangoutLink']
        
        # From description
        description = event.get('description', '')
        if 'meet.google.com' in description:
            import re
            match = re.search(r'https://meet\.google\.com/[a-z-]+', description)
            if match:
                return match.group(0)
        
        return None
    
    def _parse_event(self, event):
        """
        Parse calendar event to extract relevant information
        
        Args:
            event: Raw event from Calendar API
            
        Returns:
            Dictionary with parsed event data or None
        """
        try:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            # Parse attendees
            attendees = []
            for attendee in event.get('attendees', []):
                attendees.append({
                    'email': attendee.get('email'),
                    'name': attendee.get('displayName', ''),
                    'response_status': attendee.get('responseStatus', 'needsAction')
                })
            
            return {
                'calendar_event_id': event['id'],
                'title': event.get('summary', 'No Title'),
                'description': event.get('description', ''),
                'start_time': datetime.fromisoformat(start.replace('Z', '+00:00')),
                'end_time': datetime.fromisoformat(end.replace('Z', '+00:00')),
                'attendees': attendees,
                'meet_link': self._get_meet_link(event),
                'organizer': event.get('organizer', {})
            }
        except Exception as e:
            logger.error(f"Error parsing event: {e}")
            return None
    
    @staticmethod
    def get_service_for_user(user):
        """
        Create Calendar service instance for a user
        
        Args:
            user: User document from database
            
        Returns:
            CalendarService instance or None
        """
        if not user.get('calendar_tokens'):
            return None
        
        try:
            return CalendarService(user['calendar_tokens'])
        except Exception as e:
            logger.error(f"Failed to create Calendar service for user: {e}")
            return None
