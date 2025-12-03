#!/usr/bin/env python3
"""
Entry point for Detour Microservices
Optimized for AWS App Runner
"""
import uvicorn
import os
import sys
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

def check_environment():
    """Verify required environment variables are set"""
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE",
        "JWT_SECRET_KEY",
        "SES_SENDER_EMAIL",
    ]
    
    print("🔍 Checking environment variables...")
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            # Don't print secrets
            if "SECRET" in var or "KEY" in var or "PASSWORD" in var:
                print(f"   ✅ {var}: [SET]")
            else:
                print(f"   ✅ {var}: {value[:30]}..." if len(value) > 30 else f"   ✅ {var}: {value}")
    
    # Check AWS credentials
    if not os.getenv("AWS_ACCESS_KEY_ID") and not os.getenv("AWS_SECRET_ACCESS_KEY"):
        print("   ℹ️  AWS credentials: Using IAM role")
    else:
        print("   ✅ AWS credentials: From environment")
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ All environment variables are set")
    return True

def main():
    """Main entry point"""
    if not check_environment():
        sys.exit(1)
    
    # Get port from environment (App Runner sets PORT)
    port = int(os.getenv("PORT", "8000"))
    
    print("=" * 60)
    print("🚗 Detour Microservices")
    print("=" * 60)
    print(f"🌐 Port: {port}")
    print(f"📧 Email Sender: {os.getenv('SES_SENDER_EMAIL')}")
    print(f"🔗 Supabase URL: {os.getenv('SUPABASE_URL')}")
    print(f"🔐 JWT Algorithm: {os.getenv('JWT_ALGORITHM', 'HS256')}")
    print(f"⚡ Debug Mode: {os.getenv('DEBUG', 'False')}")
    print("=" * 60)
    
    # Start the server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )

if __name__ == "__main__":
    main()