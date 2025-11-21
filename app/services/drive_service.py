"""Google Drive API service"""
import os
import io
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)


class DriveService:
    """Service for interacting with Google Drive API"""
    
    def __init__(self, credentials_dict):
        """
        Initialize Drive service with credentials
        
        Args:
            credentials_dict: Dictionary containing token and refresh_token
        """
        scopes = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/drive.metadata.readonly'
        ]
        
        self.credentials = Credentials(
            token=credentials_dict.get('token'),  # Updated from 'access_token'
            refresh_token=credentials_dict.get('refresh_token'),
            token_uri=credentials_dict.get('token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=credentials_dict.get('client_id') or os.getenv('GOOGLE_CLIENT_ID'),
            client_secret=credentials_dict.get('client_secret') or os.getenv('GOOGLE_CLIENT_SECRET'),
            scopes=credentials_dict.get('scopes', scopes)
        )
        
        try:
            self.service = build('drive', 'v3', credentials=self.credentials)
        except Exception as e:
            logger.error(f"Failed to build Drive service: {e}")
            raise
    
    def search_meet_recordings(self, query='', max_results=50):
        """
        Search for Google Meet transcript and notes files in Drive
        
        Args:
            query: Optional search query to filter by name
            max_results: Maximum number of results
            
        Returns:
            List of file dictionaries
        """
        try:
            # Build search query for Meet transcripts and Gemini notes (Google Docs)
            search_query = (
                "mimeType = 'application/vnd.google-apps.document' and "
                "(name contains 'Transcript' or name contains 'Notes by Gemini')"
            )
            if query:
                search_query = f"{search_query} and name contains '{query}'"
            
            results = self.service.files().list(
                q=search_query,
                pageSize=max_results,
                fields="files(id, name, mimeType, createdTime, modifiedTime, webViewLink)",
                orderBy='createdTime desc'
            ).execute()
            
            return results.get('files', [])
            
        except HttpError as error:
            logger.error(f'Drive API error: {error}')
            return []
    
    def get_file_metadata(self, file_id):
        """
        Get metadata for a specific file
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            File metadata dictionary or None
        """
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='id, name, mimeType, createdTime, modifiedTime, size, webViewLink, owners'
            ).execute()
            return file
        except HttpError as error:
            logger.error(f'Drive API error: {error}')
            return None
    
    def download_file(self, file_id, destination_path):
        """
        Download a file from Drive (for documents, exports as text)
        
        Args:
            file_id: Google Drive file ID
            destination_path: Local path to save file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get file metadata to check mime type
            file_metadata = self.get_file_metadata(file_id)
            if not file_metadata:
                return False
            
            mime_type = file_metadata.get('mimeType', '')
            
            # If it's a Google Doc (transcript), export as plain text
            if mime_type == 'application/vnd.google-apps.document':
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/plain'
                )
            else:
                # For other files, download directly
                request = self.service.files().get_media(fileId=file_id)
            
            with io.FileIO(destination_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request, chunksize=1024*1024*10)  # 10MB chunks
                
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        logger.info(f"Download progress: {progress}%")
            
            logger.info(f"Download completed: {destination_path}")
            return True
            
        except HttpError as error:
            logger.error(f'Drive download error: {error}')
            return False
        except Exception as e:
            logger.error(f'Download error: {e}')
            return False
    
    def get_file_download_url(self, file_id):
        """
        Get webViewLink for a file
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            URL string or None
        """
        try:
            file = self.get_file_metadata(file_id)
            return file.get('webViewLink') if file else None
        except Exception as e:
            logger.error(f'Error getting download URL: {e}')
            return None
    
    def list_recordings_by_date_range(self, start_date, end_date):
        """
        List Meet transcript and notes files within a date range
        
        Args:
            start_date: Start datetime
            end_date: End datetime
            
        Returns:
            List of file dictionaries
        """
        try:
            start_str = start_date.isoformat() + 'Z'
            end_str = end_date.isoformat() + 'Z'
            
            query = (
                f"mimeType = 'application/vnd.google-apps.document' and "
                f"(name contains 'Transcript' or name contains 'Notes by Gemini') and "
                f"createdTime >= '{start_str}' and "
                f"createdTime <= '{end_str}'"
            )
            
            results = self.service.files().list(
                q=query,
                pageSize=100,
                fields="files(id, name, mimeType, createdTime, webViewLink)",
                orderBy='createdTime desc'
            ).execute()
            
            return results.get('files', [])
            
        except HttpError as error:
            logger.error(f'Drive API error: {error}')
            return []
    
    def find_meeting_recording(self, meeting_title, meeting_date):
        """
        Find meeting transcript or notes file (Google Docs) by title and date
        
        Args:
            meeting_title: Title of the meeting
            meeting_date: Meeting date (datetime object)
            
        Returns:
            File dictionary or None if not found
        """
        try:
            from datetime import timedelta
            
            # Search within ±2 hours of meeting time
            start_date = meeting_date - timedelta(hours=2)
            end_date = meeting_date + timedelta(hours=4)  # Meetings can run long
            
            start_str = start_date.isoformat() + 'Z'
            end_str = end_date.isoformat() + 'Z'
            
            # Clean meeting title for search (remove special chars)
            import re
            clean_title = re.sub(r'[^\w\s]', '', meeting_title)
            title_parts = clean_title.split()[:3]  # Use first 3 words
            
            # Build query - search for Google Docs (transcripts or Gemini notes) near the meeting time
            # Google Meet saves both "Transcript" and "Notes by Gemini" documents
            query = (
                f"mimeType = 'application/vnd.google-apps.document' and "
                f"(name contains 'Transcript' or name contains 'Notes by Gemini') and "
                f"createdTime >= '{start_str}' and "
                f"createdTime <= '{end_str}'"
            )
            
            # Add title search if we have meaningful words
            if title_parts:
                title_query = " or ".join([f"name contains '{word}'" for word in title_parts])
                query = f"{query} and ({title_query})"
            
            logger.info(f"Searching Drive for transcript/notes with query: {query}")
            
            results = self.service.files().list(
                q=query,
                pageSize=20,
                fields="files(id, name, mimeType, createdTime, modifiedTime, webViewLink)",
                orderBy='createdTime desc'
            ).execute()
            
            files = results.get('files', [])
            
            if not files:
                # Fallback: Try broader search without title
                logger.info(f"No transcript/notes found with title filter, trying broader search...")
                query = (
                    f"mimeType = 'application/vnd.google-apps.document' and "
                    f"(name contains 'Transcript' or name contains 'Notes by Gemini') and "
                    f"createdTime >= '{start_str}' and "
                    f"createdTime <= '{end_str}'"
                )
                
                results = self.service.files().list(
                    q=query,
                    pageSize=20,
                    fields="files(id, name, mimeType, createdTime, modifiedTime, webViewLink)",
                    orderBy='createdTime desc'
                ).execute()
                
                files = results.get('files', [])
            
            if files:
                # Prioritize "Notes by Gemini" over "Transcript" as it's more structured
                gemini_notes = [f for f in files if 'Notes by Gemini' in f['name']]
                transcripts = [f for f in files if 'Transcript' in f['name']]
                
                if gemini_notes:
                    logger.info(f"Found {len(gemini_notes)} Gemini notes file(s): {[f['name'] for f in gemini_notes]}")
                    return gemini_notes[0]
                elif transcripts:
                    logger.info(f"Found {len(transcripts)} transcript file(s): {[f['name'] for f in transcripts]}")
                    return transcripts[0]
            
            logger.warning(f"No transcript or Gemini notes found for meeting: {meeting_title} at {meeting_date}")
            return None
            
        except HttpError as error:
            logger.error(f'Drive API error while searching for transcript/notes: {error}')
            return None
        except Exception as e:
            logger.error(f'Error finding meeting transcript/notes: {e}')
            return None
    
    def get_document_text(self, file_id):
        """
        Get text content from a Google Doc (transcript file)
        
        Args:
            file_id: Google Drive file ID of the document
            
        Returns:
            Text content of the document or None
        """
        try:
            # Export Google Doc as plain text
            request = self.service.files().export_media(
                fileId=file_id,
                mimeType='text/plain'
            )
            
            text_content = request.execute().decode('utf-8')
            logger.info(f"Successfully retrieved document text ({len(text_content)} characters)")
            return text_content
            
        except HttpError as error:
            logger.error(f'Drive API error while getting document text: {error}')
            return None
        except Exception as e:
            logger.error(f'Error getting document text: {e}')
            return None
    
    @staticmethod
    def get_service_for_user(user):
        """
        Create Drive service instance for a user
        
        Args:
            user: User document from database
            
        Returns:
            DriveService instance or None
        """
        # Use calendar_tokens since we're requesting all scopes together
        if not user.get('calendar_tokens'):
            return None
        
        try:
            return DriveService(user['calendar_tokens'])
        except Exception as e:
            logger.error(f"Failed to create Drive service for user: {e}")
            return None
