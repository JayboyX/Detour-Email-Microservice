#!/usr/bin/env python3
"""
Detour Microservices — Production Entry Point
Optimized for AWS App Runner Deployment
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

# ---------------------------------------------------------
# Load Environment Variables
# ---------------------------------------------------------
load_dotenv()


# ---------------------------------------------------------
# Validate Required Environment Variables
# ---------------------------------------------------------
def check_environment():
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE",
        "JWT_SECRET_KEY",
        "SES_SENDER_EMAIL",
    ]

    print("\n🔍 Checking environment variables...")
    missing = []

    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
        else:
            if any(x in var for x in ["SECRET", "KEY", "PASSWORD"]):
                print(f"   ✅ {var}: [SET]")
            else:
                preview = value[:30] + ("..." if len(value) > 30 else "")
                print(f"   ✅ {var}: {preview}")

    # AWS Credentials Check
    if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
        print("   ✅ AWS credentials: From environment")
    else:
        print("   ℹ️  AWS credentials: Using IAM role")

    if missing:
        print(f"\n❌ Missing required environment variables: {', '.join(missing)}\n")
        return False

    print("✅ All environment variables are set\n")
    return True


# ---------------------------------------------------------
# Application Entry
# ---------------------------------------------------------
def main():
    if not check_environment():
        sys.exit(1)

    port = int(os.getenv("PORT", "8000"))

    print("=" * 60)
    print("🚗 Detour Microservices — Production Start")
    print("=" * 60)
    print(f"🌐 Port: {port}")
    print(f"📧 Email Sender: {os.getenv('SES_SENDER_EMAIL')}")
    print(f"🔗 Supabase URL: {os.getenv('SUPABASE_URL')}")
    print(f"🔐 JWT Algorithm: {os.getenv('JWT_ALGORITHM', 'HS256')}")
    print(f"⚡ Debug Mode: {os.getenv('DEBUG', 'False')}")
    print("=" * 60)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=os.getenv("DEBUG", "False").lower() == "true",
    )


if __name__ == "__main__":
    main()
