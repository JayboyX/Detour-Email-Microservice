# main.py - FIXED
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.api.auth import router as auth_router
from app.config import settings
import logging
from datetime import datetime  # ADD THIS IMPORT

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

if __name__ == "__main__":
    print("=" * 50)
    print("🚗 Starting Detour Email Verification Service")
    print(f"📧 Email Sender: {settings.ses_sender_email}")
    print(f"🔗 Supabase Project: {settings.supabase_url}")
    print(f"🌐 API URL: http://localhost:8000")
    print(f"📚 Docs: http://localhost:8000/docs")
    print("=" * 50)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )

