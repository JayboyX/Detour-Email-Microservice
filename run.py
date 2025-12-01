#!/usr/bin/env python3
"""
Entry point for Detour Email Verification Service
Exports 'app' for uvicorn
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Check for required environment variables
def check_environment():
    """Verify required environment variables are set"""
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE",
        "JWT_SECRET_KEY",
        "SES_SENDER_EMAIL",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY"
    ]
    
    print("🔍 Checking environment variables...")
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("💡 Make sure they are set in App Runner's environment configuration")
        return False
    
    print("✅ All environment variables are set")
    return True

# Check environment BEFORE importing anything else
if not check_environment():
    sys.exit(1)

# Now import and create the app
from main import app as main_app

# Re-export the app
app = main_app

# Startup script when run directly
if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚗 Detour Email Verification Service")
    print("=" * 60)
    print(f"📧 Email Sender: {os.getenv('SES_SENDER_EMAIL')}")
    print(f"🔗 Supabase URL: {os.getenv('SUPABASE_URL')}")
    print(f"🌐 API Base URL: {os.getenv('API_BASE_URL', 'http://localhost:8000')}")
    print("=" * 60)
    
    port = int(os.getenv("PORT", "8000"))
    
    print(f"🚀 Starting server on port {port}...")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False
    )