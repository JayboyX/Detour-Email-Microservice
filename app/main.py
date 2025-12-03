"""
Main FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
import logging
from datetime import datetime
from typing import Optional

from app.config import settings
import httpx

# Import routers
from app.auth.router import router as auth_router
from app.email.router import router as email_router
from app.sms.router import router as sms_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Detour Microservices",
    description="Email, SMS, and Authentication services for Detour Driver App",
    version="1.0.0",
    docs_url="/docs" if settings.enable_docs else None,  # CHANGE: debug → enable_docs
    redoc_url="/redoc" if settings.enable_docs else None  # CHANGE: debug → enable_docs
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/auth")
app.include_router(email_router, prefix="/api/email")
app.include_router(sms_router, prefix="/api/sms")

@app.get("/")
async def root():
    return {
        "message": "🚗 Detour Microservices API",
        "version": "1.0.0",
        "status": "running",
        "services": {
            "auth": "/api/auth",
            "email": "/api/email",
            "sms": "/api/sms"
        },
        "docs": "/docs" if settings.enable_docs else "disabled in production"  # CHANGE HERE
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "detour-microservices",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/verify-email", response_class=HTMLResponse)
async def verify_email_page(token: Optional[str] = None):
    """
    Email verification landing page
    """
    if not token:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Email Verification - Detour</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .container { max-width: 500px; margin: 0 auto; }
                .error { color: #FF6B6B; font-size: 24px; }
                .button { background: #2AB576; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="error">Missing Verification Token</h1>
                <p>Please use the link from your verification email.</p>
                <a href="detourui://login" class="button">Open Detour App</a>
            </div>
        </body>
        </html>
        """
    
    # Verify the token via API
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.api_base_url}/api/auth/verify-email",
                json={"token": token},
                headers={"Content-Type": "application/json"}
            )
            
            data = response.json()
            
            if response.status_code == 200 and data.get("success"):
                # Success page
                return f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Email Verified - Detour</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                        .container {{ max-width: 500px; margin: 0 auto; }}
                        .success {{ color: #2AB576; font-size: 24px; }}
                        .button {{ background: #2AB576; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; margin: 10px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1 class="success">✅ Email Verified Successfully!</h1>
                        <p>{data.get('message', 'Your email has been verified!')}</p>
                        <a href="detourui://login" class="button">Open Detour App</a>
                    </div>
                </body>
                </html>
                """
            else:
                # Error page
                return f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Verification Failed - Detour</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                        .container {{ max-width: 500px; margin: 0 auto; }}
                        .error {{ color: #FF6B6B; font-size: 24px; }}
                        .button {{ background: #2AB576; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1 class="error">⚠️ Verification Failed</h1>
                        <p>{data.get('message', 'The verification link is invalid or has expired.')}</p>
                        <a href="detourui://login" class="button">Open Detour App</a>
                    </div>
                </body>
                </html>
                """
                
    except Exception as e:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Network Error - Detour</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .container {{ max-width: 500px; margin: 0 auto; }}
                .error {{ color: #FF6B6B; font-size: 24px; }}
                .button {{ background: #2AB576; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="error">🔌 Network Error</h1>
                <p>Unable to verify your email. Please try again.</p>
                <a href="detourui://login" class="button">Open Detour App</a>
            </div>
        </body>
        </html>
        """