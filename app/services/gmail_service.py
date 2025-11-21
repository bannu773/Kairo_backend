import os
import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta

class GmailService:
    """Service for interacting with Gmail API"""
    
    def __init__(self, credentials_dict):
        """
        Initialize Gmail service with credentials
        
        Args:
            credentials_dict: Dictionary containing access_token and refresh_token
        """
        # Fix scopes to match what we set in config
        scopes = [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/gmail.readonly'
        ]
        
        self.credentials = Credentials(
            token=credentials_dict.get('access_token'),
            refresh_token=credentials_dict.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.getenv('GOOGLE_CLIENT_ID'),
            client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
            scopes=scopes
        )
        self.service = build('gmail', 'v1', credentials=self.credentials)
    
    def get_recent_emails(self, max_results=10, query=''):
        """
        Get recent emails from inbox
        
        Args:
            max_results: Maximum number of emails to fetch
            query: Gmail search query (e.g., 'is:unread', 'from:manager@example.com')
        
        Returns:
            List of email messages
        """
        try:
            # Get list of messages
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query
            ).execute()
            
            messages = results.get('messages', [])
            
            # Get full message details
            detailed_messages = []
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                detailed_messages.append(msg)
            
            return detailed_messages
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []
    
    def get_emails_since(self, since_date):
        """
        Get emails received after a specific date
        
        Args:
            since_date: datetime object
        
        Returns:
            List of email messages
        """
        # Convert date to Gmail query format
        query = f'after:{since_date.strftime("%Y/%m/%d")}'
        return self.get_recent_emails(max_results=50, query=query)
    
    def get_unread_emails(self, max_results=10):
        """
        Get unread emails
        
        Returns:
            List of unread email messages
        """
        return self.get_recent_emails(max_results=max_results, query='is:unread')
    
    def parse_email(self, message):
        """
        Parse email message to extract relevant information
        
        Args:
            message: Gmail API message object
        
        Returns:
            Dictionary with email details
        """
        headers = message['payload']['headers']
        
        # Extract headers
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        from_email = next((h['value'] for h in headers if h['name'] == 'From'), '')
        date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        
        # Extract email body
        body = self._get_email_body(message['payload'])
        
        return {
            'message_id': message['id'],
            'subject': subject,
            'from': from_email,
            'date': date_str,
            'body': body,
            'thread_id': message.get('threadId')
        }
    
    def _get_email_body(self, payload):
        """Extract email body from payload"""
        body = ''
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html' and not body:
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
        elif 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(
                payload['body']['data']
            ).decode('utf-8')
        
        return body
    
    def mark_as_read(self, message_id):
        """Mark an email as read"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except HttpError as error:
            print(f'An error occurred: {error}')
            return False
    
    def extract_sender_email(self, from_header):
        """
        Extract email address from 'From' header
        
        Args:
            from_header: From header value (e.g., "John Doe <john@example.com>")
        
        Returns:
            Email address
        """
        import re
        match = re.search(r'<(.+?)>', from_header)
        if match:
            return match.group(1)
        return from_header.strip()
    
    @staticmethod
    def get_service_for_user(user):
        """
        Create Gmail service instance for a user
        
        Args:
            user: User document from database
        
        Returns:
            GmailService instance or None
        """
        if not user.get('gmail_refresh_token'):
            return None
        
        credentials = {
            'refresh_token': user['gmail_refresh_token'],
            'access_token': None  # Will be refreshed automatically
        }
        
        return GmailService(credentials)
