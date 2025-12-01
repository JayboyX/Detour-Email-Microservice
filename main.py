# main.py - UPDATED WITH VERIFICATION PAGE
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
from app.api.auth import router as auth_router
from app.config import settings
import logging
from datetime import datetime
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Detour Email Verification Microservice",
    description="Email verification service for Detour Driver App",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])

@app.get("/")
async def root():
    return {
        "message": "🚗 Detour Email Verification API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled in production"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "detour-email-verification",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/verify-email", response_class=HTMLResponse)
async def verify_email_page(request: Request, token: Optional[str] = None):
    """
    Email verification landing page
    Shows verification status and allows opening the mobile app
    """
    if not token:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Email Verification - Detour</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    text-align: center; 
                    padding: 40px 20px;
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                    min-height: 100vh;
                    margin: 0;
                }
                .container {
                    max-width: 500px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 20px;
                    padding: 40px 30px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                }
                .icon {
                    font-size: 64px;
                    margin-bottom: 20px;
                }
                .success { 
                    color: #2AB576; 
                    font-size: 28px; 
                    font-weight: 700;
                    margin: 20px 0; 
                }
                .error {
                    color: #FF6B6B;
                    font-size: 28px;
                    font-weight: 700;
                    margin: 20px 0;
                }
                .message { 
                    color: #666; 
                    font-size: 16px; 
                    line-height: 1.6;
                    margin: 20px 0; 
                }
                .token {
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 10px;
                    font-family: monospace;
                    font-size: 14px;
                    word-break: break-all;
                    margin: 20px 0;
                    border: 1px solid #e9ecef;
                }
                .button { 
                    background: #2AB576; 
                    color: white; 
                    padding: 15px 30px; 
                    border-radius: 12px; 
                    text-decoration: none; 
                    display: inline-block;
                    font-weight: 600;
                    font-size: 16px;
                    margin: 10px;
                    border: none;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }
                .button:hover {
                    background: #229c61;
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(42, 181, 118, 0.3);
                }
                .button-outline {
                    background: white;
                    color: #2AB576;
                    border: 2px solid #2AB576;
                }
                .button-outline:hover {
                    background: #f0f9f4;
                }
                .instructions {
                    text-align: left;
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 30px 0;
                    border-left: 4px solid #2AB576;
                }
                .instructions h3 {
                    color: #333;
                    margin-top: 0;
                }
                .instructions li {
                    margin: 10px 0;
                    color: #666;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">📧</div>
                <div class="error">Missing Verification Token</div>
                <div class="message">
                    This link requires a verification token. Please use the link from your verification email.
                </div>
                <div class="instructions">
                    <h3>What to do:</h3>
                    <ul>
                        <li>Check your email for the verification link</li>
                        <li>Make sure you click the complete link</li>
                        <li>If the link is broken, request a new verification email</li>
                    </ul>
                </div>
                <a href="detourui://login" class="button">Open Detour App</a>
            </div>
        </body>
        </html>
        """
    
    # Try to verify the token via API
    import httpx
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
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {{ 
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            text-align: center; 
                            padding: 40px 20px;
                            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                            min-height: 100vh;
                            margin: 0;
                        }}
                        .container {{
                            max-width: 500px;
                            margin: 0 auto;
                            background: white;
                            border-radius: 20px;
                            padding: 40px 30px;
                            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                        }}
                        .icon {{
                            font-size: 80px;
                            margin-bottom: 20px;
                        }}
                        .success {{ 
                            color: #2AB576; 
                            font-size: 32px; 
                            font-weight: 700;
                            margin: 20px 0; 
                        }}
                        .message {{ 
                            color: #666; 
                            font-size: 18px; 
                            line-height: 1.6;
                            margin: 20px 0; 
                        }}
                        .button {{ 
                            background: #2AB576; 
                            color: white; 
                            padding: 16px 32px; 
                            border-radius: 12px; 
                            text-decoration: none; 
                            display: inline-block;
                            font-weight: 600;
                            font-size: 18px;
                            margin: 20px 10px;
                            border: none;
                            cursor: pointer;
                            transition: all 0.3s ease;
                        }}
                        .button:hover {{
                            background: #229c61;
                            transform: translateY(-2px);
                            box-shadow: 0 5px 15px rgba(42, 181, 118, 0.3);
                        }}
                        .button-outline {{
                            background: white;
                            color: #2AB576;
                            border: 2px solid #2AB576;
                        }}
                        .button-outline:hover {{
                            background: #f0f9f4;
                        }}
                        .instructions {{
                            text-align: left;
                            background: #f8f9fa;
                            padding: 20px;
                            border-radius: 10px;
                            margin: 30px 0;
                            border-left: 4px solid #2AB576;
                        }}
                        .instructions h3 {{
                            color: #333;
                            margin-top: 0;
                        }}
                        .instructions li {{
                            margin: 10px 0;
                            color: #666;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon">✅</div>
                        <div class="success">Email Verified Successfully!</div>
                        <div class="message">
                            {data.get('message', 'Your email has been verified! You can now log in to the Detour Driver App.')}
                        </div>
                        
                        <div class="instructions">
                            <h3>🎉 You're all set!</h3>
                            <ul>
                                <li>Your account is now active</li>
                                <li>You can log in with your email and password</li>
                                <li>Start earning as a Detour driver</li>
                            </ul>
                        </div>
                        
                        <a href="detourui://login" class="button">Open Detour App & Login</a>
                        <br>
                        <a href="detourui://dashboard" class="button button-outline">Go to Dashboard</a>
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
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {{ 
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            text-align: center; 
                            padding: 40px 20px;
                            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                            min-height: 100vh;
                            margin: 0;
                        }}
                        .container {{
                            max-width: 500px;
                            margin: 0 auto;
                            background: white;
                            border-radius: 20px;
                            padding: 40px 30px;
                            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                        }}
                        .icon {{
                            font-size: 64px;
                            margin-bottom: 20px;
                        }}
                        .error {{
                            color: #FF6B6B;
                            font-size: 28px;
                            font-weight: 700;
                            margin: 20px 0;
                        }}
                        .message {{ 
                            color: #666; 
                            font-size: 16px; 
                            line-height: 1.6;
                            margin: 20px 0; 
                        }}
                        .token {{
                            background: #f8f9fa;
                            padding: 15px;
                            border-radius: 10px;
                            font-family: monospace;
                            font-size: 14px;
                            word-break: break-all;
                            margin: 20px 0;
                            border: 1px solid #e9ecef;
                        }}
                        .button {{ 
                            background: #2AB576; 
                            color: white; 
                            padding: 15px 30px; 
                            border-radius: 12px; 
                            text-decoration: none; 
                            display: inline-block;
                            font-weight: 600;
                            font-size: 16px;
                            margin: 10px;
                            border: none;
                            cursor: pointer;
                            transition: all 0.3s ease;
                        }}
                        .button:hover {{
                            background: #229c61;
                            transform: translateY(-2px);
                            box-shadow: 0 5px 15px rgba(42, 181, 118, 0.3);
                        }}
                        .button-outline {{
                            background: white;
                            color: #2AB576;
                            border: 2px solid #2AB576;
                        }}
                        .instructions {{
                            text-align: left;
                            background: #f8f9fa;
                            padding: 20px;
                            border-radius: 10px;
                            margin: 30px 0;
                            border-left: 4px solid #2AB576;
                        }}
                        .instructions h3 {{
                            color: #333;
                            margin-top: 0;
                        }}
                        .instructions li {{
                            margin: 10px 0;
                            color: #666;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon">⚠️</div>
                        <div class="error">Verification Failed</div>
                        <div class="message">
                            {data.get('message', 'The verification link is invalid or has expired.')}
                        </div>
                        
                        <div class="instructions">
                            <h3>What to do next:</h3>
                            <ul>
                                <li>Request a new verification email from the app</li>
                                <li>Make sure you're using the latest link</li>
                                <li>Links expire after 24 hours</li>
                                <li>Contact support if you continue having issues</li>
                            </ul>
                        </div>
                        
                        <a href="detourui://login" class="button">Open Detour App</a>
                        <a href="detourui://resend-verification" class="button button-outline">Resend Verification</a>
                    </div>
                </body>
                </html>
                """
                
    except Exception as e:
        # Network error page
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Network Error - Detour</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    text-align: center; 
                    padding: 40px 20px;
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                    min-height: 100vh;
                    margin: 0;
                }}
                .container {{
                    max-width: 500px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 20px;
                    padding: 40px 30px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                }}
                .icon {{
                    font-size: 64px;
                    margin-bottom: 20px;
                }}
                .error {{
                    color: #FF6B6B;
                    font-size: 28px;
                    font-weight: 700;
                    margin: 20px 0;
                }}
                .message {{ 
                    color: #666; 
                    font-size: 16px; 
                    line-height: 1.6;
                    margin: 20px 0; 
                }}
                .button {{ 
                    background: #2AB576; 
                    color: white; 
                    padding: 15px 30px; 
                    border-radius: 12px; 
                    text-decoration: none; 
                    display: inline-block;
                    font-weight: 600;
                    font-size: 16px;
                    margin: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">🔌</div>
                <div class="error">Network Error</div>
                <div class="message">
                    Unable to verify your email at the moment. Please check your internet connection and try again.
                </div>
                <a href="detourui://login" class="button">Open Detour App</a>
            </div>
        </body>
        </html>
        """

if __name__ == "__main__":
    print("=" * 50)
    print("🚗 Starting Detour Email Verification Service")
    print(f"📧 Email Sender: {settings.ses_sender_email}")
    print(f"🔗 Supabase Project: {settings.supabase_url}")
    print(f"🌐 API URL: {settings.api_base_url}")
    print(f"📧 Verification URL: {settings.api_base_url}/verify-email")
    print(f"📚 Docs: {settings.api_base_url}/docs")
    print("=" * 50)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )