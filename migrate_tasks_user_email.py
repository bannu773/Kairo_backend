"""
Migration script to add user_email field to existing tasks
This ensures proper user isolation for tasks created before the fix
"""
from app import create_app, get_db
from app.models.user import User
from bson import ObjectId

def migrate_existing_tasks():
    """Add user_email field to existing tasks based on assigned_to"""
    
    app = create_app('development')
    
    with app.app_context():
        db = get_db()
        
        print("\n" + "="*80)
        print("MIGRATING EXISTING TASKS - ADDING user_email FIELD")
        print("="*80)
        
        # Get all tasks without user_email field
        tasks_without_user_email = list(db.tasks.find({'user_email': {'$exists': False}}))
        
        print(f"\n📋 Found {len(tasks_without_user_email)} tasks without user_email field")
        
        if not tasks_without_user_email:
            print("✅ All tasks already have user_email field. No migration needed.")
            return
        
        updated_count = 0
        error_count = 0
        
        for task in tasks_without_user_email:
            try:
                # Get the user from assigned_to
                assigned_to_id = task.get('assigned_to')
                
                if assigned_to_id:
                    user = db.users.find_one({'_id': ObjectId(assigned_to_id)})
                    
                    if user and user.get('email'):
                        # Update task with user_email
                        db.tasks.update_one(
                            {'_id': task['_id']},
                            {'$set': {'user_email': user['email']}}
                        )
                        updated_count += 1
                        print(f"   ✅ Updated task '{task['title'][:50]}...' with user_email: {user['email']}")
                    else:
                        print(f"   ⚠️  User not found for task '{task['title'][:50]}...'")
                        error_count += 1
                else:
                    print(f"   ⚠️  Task '{task['title'][:50]}...' has no assigned_to")
                    error_count += 1
                    
            except Exception as e:
                print(f"   ❌ Error updating task '{task.get('title', 'unknown')[:50]}...': {e}")
                error_count += 1
        
        print("\n" + "="*80)
        print(f"✅ Migration complete!")
        print(f"   Updated: {updated_count} tasks")
        print(f"   Errors: {error_count} tasks")
        print("="*80)

if __name__ == '__main__':
    migrate_existing_tasks()
