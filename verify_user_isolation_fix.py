"""
Complete fix verification and testing script
"""
from app import create_app, get_db
from app.models.user import User
from app.models.task import Task
from bson import ObjectId

def verify_fix():
    """Verify that the user isolation fix is working"""
    
    app = create_app('development')
    
    with app.app_context():
        db = get_db()
        
        print("\n" + "="*80)
        print("USER ISOLATION FIX - VERIFICATION")
        print("="*80)
        
        # Get all users
        users = list(db.users.find())
        print(f"\n📊 Found {len(users)} users in database:")
        for user in users:
            print(f"   - {user['email']} (ID: {user['_id']})")
        
        if len(users) < 2:
            print("\n⚠️  Only 1 user found. Add another user to fully test isolation.")
            if len(users) == 0:
                print("❌ No users found. Please login first.")
                return
        
        # Check all tasks
        all_tasks = list(db.tasks.find())
        print(f"\n📋 Total tasks in database: {len(all_tasks)}")
        
        # Check tasks with/without user_email
        tasks_with_email = list(db.tasks.find({'user_email': {'$exists': True}}))
        tasks_without_email = list(db.tasks.find({'user_email': {'$exists': False}}))
        
        print(f"\n✅ Tasks with user_email field: {len(tasks_with_email)}")
        print(f"⚠️  Tasks without user_email field: {len(tasks_without_email)}")
        
        if tasks_without_email:
            print("\n⚠️  WARNING: Some tasks don't have user_email field!")
            print("   Run: python migrate_tasks_user_email.py")
        
        # Test the get_user_tasks query for each user
        print("\n" + "-"*80)
        print("TESTING get_user_tasks() FOR EACH USER:")
        print("-"*80)
        
        for user in users:
            user_id = str(user['_id'])
            user_email = user.get('email')
            
            # Use the fixed get_user_tasks method
            result = Task.get_user_tasks(user_id)
            tasks = result['tasks']
            
            print(f"\n👤 User: {user_email}")
            print(f"   User ID: {user_id}")
            print(f"   Tasks returned: {len(tasks)}")
            
            # Verify each task belongs to this user
            correct_count = 0
            wrong_count = 0
            
            for task in tasks:
                task_user_email = task.get('user_email')
                task_assigned_to = task.get('assigned_to')
                
                # Check if task belongs to this user
                is_correct_user_email = (task_user_email == user_email) or (task_user_email is None)
                is_correct_assigned_to = (str(task_assigned_to) == user_id)
                
                if is_correct_user_email and is_correct_assigned_to:
                    correct_count += 1
                else:
                    wrong_count += 1
                    print(f"\n   ❌ WRONG TASK RETURNED:")
                    print(f"      Title: {task['title'][:50]}...")
                    print(f"      task.user_email: {task_user_email}")
                    print(f"      task.assigned_to: {task_assigned_to}")
                    print(f"      Expected user_email: {user_email}")
                    print(f"      Expected assigned_to: {user_id}")
            
            if wrong_count == 0:
                print(f"   ✅ All {correct_count} tasks correctly belong to this user")
            else:
                print(f"   ⚠️  {wrong_count} tasks incorrectly returned!")
                print(f"   ✅ {correct_count} tasks correct")
        
        # Summary
        print("\n" + "="*80)
        print("VERIFICATION SUMMARY:")
        print("="*80)
        
        if tasks_without_email > 0:
            print("⚠️  MIGRATION NEEDED: Run 'python migrate_tasks_user_email.py'")
        else:
            print("✅ All tasks have user_email field")
        
        # Check if there are any cross-user contamination
        print("\n🔍 Checking for cross-user task contamination...")
        contamination_found = False
        
        for user in users:
            user_id = str(user['_id'])
            user_email = user.get('email')
            
            # Find tasks that shouldn't belong to this user
            wrong_tasks = list(db.tasks.find({
                'assigned_to': ObjectId(user_id),
                'user_email': {'$exists': True, '$ne': user_email}
            }))
            
            if wrong_tasks:
                contamination_found = True
                print(f"\n❌ CONTAMINATION FOUND for {user_email}:")
                print(f"   {len(wrong_tasks)} tasks have assigned_to={user_id} but user_email != {user_email}")
                for task in wrong_tasks[:3]:  # Show first 3
                    print(f"   - {task['title'][:50]}... (user_email: {task.get('user_email')})")
        
        if not contamination_found:
            print("✅ No cross-user task contamination found!")
        
        print("\n" + "="*80)
        if not contamination_found and tasks_without_email == 0:
            print("🎉 USER ISOLATION FIX VERIFIED SUCCESSFULLY!")
        elif tasks_without_email > 0:
            print("⚠️  Run migration script to complete the fix")
        else:
            print("❌ Issues found - check the output above")
        print("="*80)

if __name__ == '__main__':
    verify_fix()
