#!/usr/bin/env python3
"""
Run script for Detour Email Verification Service
"""
import subprocess
import sys
import os

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def check_environment():
    """Check if required environment variables are set"""
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE",
        "JWT_SECRET_KEY",
        "SES_SENDER_EMAIL"
    ]
    
    print("🔍 Checking environment variables...")
    missing_vars = []
    
    for var in required_vars:
        if var not in os.environ:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file or environment")
        return False
    
    print("✅ Environment variables are set")
    return True

def run_server():
    """Run the FastAPI server"""
    print("🚀 Starting Detour Email Verification Service...")
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ])

if __name__ == "__main__":
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Install dependencies if needed
    if len(sys.argv) > 1 and sys.argv[1] == "--install":
        install_dependencies()
    
    # Run server
    run_server()