#!/usr/bin/env python3
"""
Check available Gemini models and test initialization
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)

import google.generativeai as genai

def check_gemini_setup():
    """Check Gemini API setup and available models"""
    print("🔍 Checking Gemini API setup...")
    
    # Check API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment variables")
        return False
    
    print(f"✅ API Key found: {api_key[:20]}...")
    
    # Configure Gemini
    try:
        genai.configure(api_key=api_key)
        print("✅ Gemini API configured successfully")
    except Exception as e:
        print(f"❌ Failed to configure Gemini API: {e}")
        return False
    
    # List available models
    print("\n📋 Listing available models...")
    try:
        models = list(genai.list_models())
        if not models:
            print("❌ No models available")
            return False
        
        print(f"✅ Found {len(models)} available models:")
        for model in models:
            print(f"   - {model.name}")
            if hasattr(model, 'display_name'):
                print(f"     Display: {model.display_name}")
            if hasattr(model, 'supported_generation_methods'):
                print(f"     Methods: {model.supported_generation_methods}")
        
    except Exception as e:
        print(f"❌ Failed to list models: {e}")
        return False
    
    # Test model initialization
    print("\n🧪 Testing model initialization...")
    
    model_names_to_test = [
        'gemini-2.5-flash',
        'gemini-1.5-flash',
        'gemini-1.5-pro', 
        'gemini-pro',
    ]
    
    working_model = None
    for model_name in model_names_to_test:
        try:
            model = genai.GenerativeModel(model_name)
            print(f"✅ {model_name} - Initialized successfully")
            if not working_model:
                working_model = model_name
        except Exception as e:
            print(f"❌ {model_name} - Failed: {e}")
    
    if working_model:
        print(f"\n🎉 Recommended model: {working_model}")
        
        # Test generation
        try:
            model = genai.GenerativeModel(working_model)
            response = model.generate_content("Hello, how are you?")
            print(f"✅ Test generation successful: {response.text[:100]}...")
            return True
        except Exception as e:
            print(f"❌ Test generation failed: {e}")
            return False
    else:
        print("\n❌ No working models found")
        return False

def test_gemini_service():
    """Test our GeminiService class"""
    print("\n🧪 Testing GeminiService class...")
    
    try:
        from app.services.gemini_service import GeminiService
        
        service = GeminiService()
        print("✅ GeminiService initialized successfully")
        
        # Test task extraction
        test_result = service.extract_task_from_email(
            email_subject="Test Task",
            email_body="Please complete this task: Update the homepage. Priority: High. Deadline: Tomorrow."
        )
        
        if test_result:
            print(f"✅ Task extraction test successful")
            print(f"   Has task: {test_result.get('has_task')}")
            print(f"   Title: {test_result.get('title')}")
        else:
            print("❌ Task extraction returned None")
            
        return True
        
    except Exception as e:
        print(f"❌ GeminiService test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Gemini API Diagnostic Tool\n")
    
    # Check basic setup
    setup_ok = check_gemini_setup()
    
    if setup_ok:
        # Test our service
        service_ok = test_gemini_service()
        
        if service_ok:
            print("\n🎉 All tests passed! Your Gemini integration should work.")
        else:
            print("\n⚠️ Basic setup works, but GeminiService has issues.")
    else:
        print("\n❌ Basic setup failed. Check your API key and internet connection.")
    
    print("\n💡 Use the recommended model in your GeminiService initialization.")
