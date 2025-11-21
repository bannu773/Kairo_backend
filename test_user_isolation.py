"""
Test script to verify user isolation bug in task creation
This script demonstrates that tasks created from emails are visible to all users
"""
from app import create_app, get_db
from app.models.user import User
from app.models.task import Task
from bson import ObjectId

def test_user_isolation():
    """Test that tasks are properly isolated per user"""
    
    app = create_app('development')
    
    with app.app_context():
        db = get_db()
        
        print("\n" + "="*80)
        print("TESTING USER ISOLATION BUG")
        print("="*80)
        
        # Get all users
        users = list(db.users.find())
        print(f"\n📊 Found {len(users)} users in database:")
        for user in users:
            print(f"   - {user['email']} (ID: {user['_id']})")
        
        if len(users) < 2:
            print("\n❌ Need at least 2 users to test isolation. Please login with 2 different Gmail accounts first.")
            return
        
        # Get all tasks
        all_tasks = list(db.tasks.find())
        print(f"\n📋 Total tasks in database: {len(all_tasks)}")
        
        # Check tasks per user
        print("\n" + "-"*80)
        print("TASKS PER USER (using current Task.get_user_tasks logic):")
        print("-"*80)
        
        for user in users:
            user_id = str(user['_id'])
            result = Task.get_user_tasks(user_id)
            tasks = result['tasks']
            
            print(f"\n👤 User: {user['email']}")
            print(f"   Tasks count: {len(tasks)}")
            
            for task in tasks:
                print(f"   - {task['title'][:50]}...")
                print(f"     assigned_to: {task.get('assigned_to')}")
                print(f"     created_by: {task.get('created_by')}")
                print(f"     sender_email: {task.get('sender_email', 'N/A')}")
                print(f"     source_type: {task.get('source_type', 'manual')}")
        
        # Now check the bug - show tasks that have same assigned_to but different user emails
        print("\n" + "-"*80)
        print("🐛 BUG ANALYSIS:")
        print("-"*80)
        
        # Check if there are email-sourced tasks
        email_tasks = list(db.tasks.find({'source_type': 'email'}))
        print(f"\n📧 Email-sourced tasks: {len(email_tasks)}")
        
        if email_tasks:
            print("\nChecking which user should see each email task:")
            for task in email_tasks:
                assigned_to_id = task.get('assigned_to')
                assigned_user = db.users.find_one({'_id': ObjectId(assigned_to_id)})
                
                print(f"\n   Task: {task['title'][:50]}...")
                print(f"   - sender_email: {task.get('sender_email')}")
                print(f"   - assigned_to: {assigned_user['email'] if assigned_user else 'Unknown'}")
                
                # The bug: we don't know which user's Gmail received this email!
                print(f"   ⚠️  PROBLEM: No field indicates WHICH USER'S GMAIL received this email!")
                print(f"   ⚠️  This task is visible to: {assigned_user['email'] if assigned_user else 'Unknown'}")
                print(f"   ⚠️  But we don't know if the email was sent TO {assigned_user['email'] if assigned_user else 'Unknown'}")
        
        # Recommendations
        print("\n" + "="*80)
        print("💡 SOLUTION:")
        print("="*80)
        print("""
The fix requires:
1. Add a 'user_email' or 'recipient_email' field to tasks
2. Store the user's email who received the email when creating task from email
3. Filter tasks by both 'assigned_to' AND ensure the task belongs to current user
4. Update Task.create() to include user_email parameter
5. Update email_polling_service to pass user's email when creating tasks
""")

if __name__ == '__main__':
    test_user_isolation()
