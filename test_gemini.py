#!/usr/bin/env python3
"""
Test script for Gemini service and email polling
"""
import sys
import os

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)

from app.services.gemini_service import GeminiService

def test_gemini_service():
    """Test the Gemini service with sample email data"""
    print("🧪 Testing Gemini Service...")
    
    try:
        # Initialize Gemini service
        gemini_service = GeminiService()
        print("✅ Gemini service initialized successfully")
        
        # Test email data
        test_email_subject = "Create user profile page"
        test_email_body = """
        Hi there,
        
        I need you to complete the following task:
        
        Task: Create user profile page
        Priority: High
        Deadline: December 25, 2024
        Description: Build a page where users can edit their profile information and upload profile pictures.
        
        Please complete this as soon as possible.
        
        Thanks!
        Manager
        """
        
        print(f"\n📧 Testing with sample email:")
        print(f"Subject: {test_email_subject}")
        print(f"Body: {test_email_body[:100]}...")
        
        # Extract task information
        result = gemini_service.extract_task_from_email(
            email_subject=test_email_subject,
            email_body=test_email_body
        )
        
        print(f"\n🎯 Gemini extraction result:")
        if result:
            print(f"✅ Task found: {result.get('has_task', False)}")
            print(f"📝 Title: {result.get('title', 'N/A')}")
            print(f"📄 Description: {result.get('description', 'N/A')[:100]}...")
            print(f"⚡ Priority: {result.get('priority', 'N/A')}")
            print(f"📅 Deadline: {result.get('deadline', 'N/A')}")
        else:
            print("❌ No task extracted")
        
        return result is not None
        
    except Exception as e:
        print(f"❌ Error testing Gemini service: {e}")
        return False

def test_email_format():
    """Test different email formats"""
    print("\n🧪 Testing different email formats...")
    
    test_cases = [
        {
            "name": "Simple task email",
            "subject": "New Assignment",
            "body": "Please update the homepage by Friday. Priority: Medium."
        },
        {
            "name": "No task email", 
            "subject": "Meeting reminder",
            "body": "Don't forget about our meeting tomorrow at 2 PM."
        },
        {
            "name": "Detailed task email",
            "subject": "Bug Fix Required",
            "body": "There's a critical bug in the login system. Fix it ASAP. Due: Tomorrow. High priority."
        }
    ]
    
    try:
        gemini_service = GeminiService()
        
        for test_case in test_cases:
            print(f"\n📧 Testing: {test_case['name']}")
            result = gemini_service.extract_task_from_email(
                email_subject=test_case['subject'],
                email_body=test_case['body']
            )
            
            if result and result.get('has_task'):
                print(f"   ✅ Task detected: {result.get('title')}")
            else:
                print(f"   ❌ No task detected")
                
    except Exception as e:
        print(f"❌ Error in format testing: {e}")

if __name__ == "__main__":
    print("🚀 Starting Gemini Service Tests...\n")
    
    # Test basic functionality
    success = test_gemini_service()
    
    if success:
        # Test different formats
        test_email_format()
        print("\n✅ All tests completed!")
    else:
        print("\n❌ Basic test failed - check your Gemini API key")
        
    print("\n💡 If tests pass, your email polling should work correctly!")
