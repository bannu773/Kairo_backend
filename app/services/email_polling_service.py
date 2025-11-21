import threading
import time
from datetime import datetime, timedelta
from flask import current_app
from app.models.user import User
from app.models.task import Task
from app.models.processed_email import ProcessedEmail
from app.services.gmail_service import GmailService
from app.services.gemini_service import GeminiService

class EmailPollingService:
    """Service for polling Gmail and automatically creating tasks"""
    
    def __init__(self, app=None):
        self.app = app
        self.polling_thread = None
        self.is_running = False
        self.poll_interval = 300  # Check every 5 minutes (300 seconds)
        
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        
    def start_polling(self):
        """Start the email polling service"""
        if self.is_running:
            print("Email polling service is already running")
            return
            
        self.is_running = True
        self.polling_thread = threading.Thread(target=self._poll_emails, daemon=True)
        self.polling_thread.start()
        print("✅ Email polling service started - checking every 5 minutes")
        
    def stop_polling(self):
        """Stop the email polling service"""
        self.is_running = False
        if self.polling_thread:
            self.polling_thread.join(timeout=5)
        print("❌ Email polling service stopped")
        
    def _poll_emails(self):
        """Main polling loop"""
        print("🔄 Email polling loop started...")
        
        while self.is_running:
            try:
                with self.app.app_context():
                    self._check_all_users_for_new_emails()
            except Exception as e:
                print(f"❌ Error in email polling: {e}")
                
            # Wait before next poll
            for _ in range(self.poll_interval):
                if not self.is_running:
                    break
                time.sleep(1)
                
        print("🛑 Email polling loop ended")
        
    def _check_all_users_for_new_emails(self):
        """Check all users for new emails"""
        try:
            # Get all users with Gmail tokens
            users = User.get_users_with_gmail_tokens()
            
            if not users:
                return
                
            print(f"📧 Checking emails for {len(users)} users...")
            
            for user in users:
                try:
                    self._check_user_emails(user)
                except Exception as e:
                    print(f"❌ Error checking emails for user {user.get('email', 'unknown')}: {e}")
                    
        except Exception as e:
            print(f"❌ Error getting users with Gmail tokens: {e}")
    
    def _check_user_emails(self, user):
        """Check emails for a specific user"""
        try:
            # Get Gmail service for user
            gmail_service = GmailService.get_service_for_user(user)
            if not gmail_service:
                return
                
            # Get the last check time (default to 5 minutes ago)
            last_check = user.get('last_email_check')
            if not last_check:
                last_check = datetime.utcnow() - timedelta(minutes=5)
            elif isinstance(last_check, str):
                last_check = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
                
            # Get emails since last check
            emails = gmail_service.get_emails_since(last_check)
            
            if not emails:
                return
                
            print(f"📬 Found {len(emails)} new emails for {user.get('email')}")
            
            # Process each email
            new_tasks_count = 0
            for email_msg in emails:
                try:
                    task_created = self._process_email_for_tasks(email_msg, user, gmail_service)
                    if task_created:
                        new_tasks_count += 1
                except Exception as e:
                    print(f"❌ Error processing email: {e}")
                    
            # Update last check time
            User.update_last_email_check(str(user['_id']))
            
            if new_tasks_count > 0:
                print(f"✅ Created {new_tasks_count} new tasks for {user.get('email')}")
                
        except Exception as e:
            print(f"❌ Error in _check_user_emails: {e}")
    
    def _process_email_for_tasks(self, email_msg, user, gmail_service):
        """Process an email to extract and create tasks"""
        try:
            # Parse email
            email_data = gmail_service.parse_email(email_msg)
            email_id = email_data['message_id']
            user_id = str(user['_id'])
            
            # Skip if email is from the user themselves
            sender_email = gmail_service.extract_sender_email(email_data['from'])
            if sender_email.lower() == user.get('email', '').lower():
                return False
            
            # Check if this email was already processed using ProcessedEmail model
            if ProcessedEmail.is_processed(email_id, user_id):
                print(f"   ⏭️  Email already processed: {email_data['subject'][:50]}...")
                return False
                
            print(f"🔍 Processing email from {sender_email}: {email_data['subject'][:50]}...")
            
            # Use Gemini to extract task information
            gemini_service = GeminiService()
            task_data = gemini_service.extract_task_from_email(
                email_subject=email_data['subject'],
                email_body=email_data['body']
            )
            
            if not task_data or not task_data.get('has_task', False):
                print(f"   ℹ️ No task found in email")
                # Mark as processed even if no tasks were found to avoid reprocessing
                ProcessedEmail.mark_as_processed(email_id, user_id, tasks_created=0)
                return False
            
            # Check if multiple tasks were extracted
            tasks_to_create = task_data.get('tasks', [])
            if not tasks_to_create:
                # Fallback to single task format for backward compatibility
                tasks_to_create = [{
                    'title': task_data.get('title', email_data['subject']),
                    'description': task_data.get('description', ''),
                    'priority': task_data.get('priority', 'medium'),
                    'deadline': task_data.get('deadline')
                }]
            
            # Create all extracted tasks
            created_count = 0
            for task_info in tasks_to_create:
                try:
                    task = Task.create(
                        title=task_info.get('title', email_data['subject']),
                        description=task_info.get('description', ''),
                        priority=task_info.get('priority', 'medium'),
                        deadline=task_info.get('deadline'),
                        assigned_to=str(user['_id']),
                        created_by=str(user['_id']),  # Auto-assigned
                        status='pending',
                        email_id=email_data['message_id'],
                        sender_email=sender_email,
                        user_email=user.get('email'),  # CRITICAL FIX: Store which user received this email
                        labels=task_data.get('labels', []),
                        source_type='email'  # Mark as email-sourced task
                    )
                    
                    print(f"   ✅ Created task: {task_info.get('title', email_data['subject'])}")
                    created_count += 1
                    
                except Exception as e:
                    print(f"   ❌ Failed to create task: {e}")
            
            # Mark email as processed with count of tasks created
            ProcessedEmail.mark_as_processed(email_id, user_id, tasks_created=created_count)
            
            # Mark email as read (optional)
            # gmail_service.mark_as_read(email_data['message_id'])
            
            return created_count > 0
            
        except Exception as e:
            print(f"❌ Error processing email for tasks: {e}")
            return False


# Global instance
email_polling_service = EmailPollingService()
