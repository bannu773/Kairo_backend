"""
Script to clean up duplicate processed_emails entries
"""
from app import create_app, get_db
from bson import ObjectId

def cleanup_duplicates():
    """Remove duplicate processed_emails and drop/recreate index"""
    
    app = create_app('development')
    
    with app.app_context():
        db = get_db()
        
        print("\n" + "="*80)
        print("CLEANING UP DUPLICATE PROCESSED EMAILS")
        print("="*80)
        
        # Drop the unique index if it exists
        try:
            db.processed_emails.drop_index('email_id_1_user_id_1')
            print("✅ Dropped existing unique index")
        except Exception as e:
            print(f"ℹ️  No existing index to drop (this is okay): {e}")
        
        # Find duplicates
        pipeline = [
            {
                '$group': {
                    '_id': {
                        'email_id': '$email_id',
                        'user_id': '$user_id'
                    },
                    'count': {'$sum': 1},
                    'docs': {'$push': '$_id'}
                }
            },
            {
                '$match': {
                    'count': {'$gt': 1}
                }
            }
        ]
        
        duplicates = list(db.processed_emails.aggregate(pipeline))
        
        print(f"\n📊 Found {len(duplicates)} duplicate groups")
        
        # Remove duplicates, keeping only the first one
        removed_count = 0
        for dup in duplicates:
            # Keep the first doc, remove the rest
            docs_to_remove = dup['docs'][1:]  # Skip first one
            for doc_id in docs_to_remove:
                db.processed_emails.delete_one({'_id': doc_id})
                removed_count += 1
            
            email_id = dup['_id']['email_id']
            user_id = dup['_id']['user_id']
            print(f"   Cleaned: email_id={email_id}, user_id={user_id}, removed {len(docs_to_remove)} duplicates")
        
        print(f"\n✅ Removed {removed_count} duplicate entries")
        
        # Recreate the unique index
        try:
            db.processed_emails.create_index([('email_id', 1), ('user_id', 1)], unique=True)
            print("✅ Created unique index on (email_id, user_id)")
        except Exception as e:
            print(f"❌ Failed to create index: {e}")
        
        # Show final count
        total = db.processed_emails.count_documents({})
        print(f"\n📧 Total processed_emails after cleanup: {total}")

if __name__ == '__main__':
    cleanup_duplicates()
