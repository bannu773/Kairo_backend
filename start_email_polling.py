#!/usr/bin/env python3
"""
Email Polling Startup Script
Run this after your Flask app starts to begin email polling
"""
import sys
import os
import time
import requests

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)

def wait_for_server():
    """Wait for Flask server to be ready"""
    print("⏳ Waiting for Flask server to start...")
    
    for attempt in range(30):  # Try for 30 seconds
        try:
            response = requests.get('http://localhost:5000/api/health', timeout=2)
            if response.status_code == 200:
                print("✅ Flask server is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(1)
        print(f"   Attempt {attempt + 1}/30...")
    
    print("❌ Flask server failed to start within 30 seconds")
    return False

def start_email_polling():
    """Start the email polling service"""
    try:
        from app.services.email_polling_service import email_polling_service
        from app import create_app
        
        # Create app context
        app = create_app()
        with app.app_context():
            # Check if already running
            if email_polling_service.is_running:
                print("✅ Email polling service is already running")
                return
            
            # Start polling
            email_polling_service.start_polling()
            print("🚀 Email polling service started successfully!")
            
            # Keep the script running
            try:
                while email_polling_service.is_running:
                    time.sleep(10)
                    print("📧 Email polling service is active...")
            except KeyboardInterrupt:
                print("\n🛑 Stopping email polling service...")
                email_polling_service.stop_polling()
                
    except Exception as e:
        print(f"❌ Failed to start email polling: {e}")

if __name__ == "__main__":
    print("🔄 Starting Email Polling Service...")
    
    # Wait for Flask server
    if wait_for_server():
        start_email_polling()
    else:
        print("💡 Start your Flask server first with: python run.py")
