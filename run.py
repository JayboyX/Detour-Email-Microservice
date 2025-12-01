#!/usr/bin/env python3
"""
Entry point for Detour Email Verification Service
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
        # AWS credentials - can come from IAM role or environment
        # "AWS_ACCESS_KEY_ID",
        # "AWS_SECRET_ACCESS_KEY"
    ]
    
    print("🔍 Checking environment variables...")
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            # Don't print secrets, just confirm they exist
            if "SECRET" in var or "KEY" in var or "PASSWORD" in var:
                print(f"   ✅ {var}: [SET]")
            else:
                print(f"   ✅ {var}: {value[:30]}..." if len(value) > 30 else f"   ✅ {var}: {value}")
    
    # Check AWS credentials - either from env or IAM role
    if not os.getenv("AWS_ACCESS_KEY_ID") and not os.getenv("AWS_SECRET_ACCESS_KEY"):
        print("   ℹ️  AWS credentials: Using IAM role (not from environment)")
    else:
        print("   ✅ AWS credentials: From environment variables")
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("💡 Make sure they are set in App Runner's environment configuration")
        return False
    
    print("✅ All environment variables are set")
    return True

def print_startup_info():
    """Print startup information"""
    print("=" * 60)
    print("🚗 Detour Email Verification Service")
    print("=" * 60)
    print(f"📧 Email Sender: {os.getenv('SES_SENDER_EMAIL')}")
    print(f"🔗 Supabase URL: {os.getenv('SUPABASE_URL')}")
    print(f"🌐 API Base URL: {os.getenv('API_BASE_URL', 'http://localhost:8000')}")
    print(f"🔐 JWT Algorithm: {os.getenv('JWT_ALGORITHM', 'HS256')}")
    print(f"⚡ Debug Mode: {os.getenv('DEBUG', 'False')}")
    print(f"🌍 Port: {os.getenv('PORT', '8000')}")
    print("=" * 60)

def main():
    """Main entry point"""
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Print startup info
    print_startup_info()
    
    # Import app AFTER environment is loaded
    from main import app
    
    # Get port from environment (App Runner sets PORT)
    port = int(os.getenv("PORT", "8000"))
    
    print(f"🚀 Starting server on port {port}...")
    print("📚 API Documentation: /docs")
    print("🔧 Health Check: /health")
    print("📧 Verification Page: /verify-email")
    print("=" * 60)
    
    # Start the server
    uvicorn.run(
        app,
        host="0.0.0.0",  # Important: must bind to all interfaces
        port=port,
        log_level="info",
        # Don't use reload in production (App Runner handles it)
        reload=False,
        access_log=True
    )

if __name__ == "__main__":
    main()