from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role: str
    
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    verification_token_expire_hours: int = 24
    
    # AWS SES
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-1"
    ses_sender_email: str
    
    # App
    app_scheme: str = "detourui"
    api_base_url: str = "https://3a5ea9256115.ngrok-free.app"  # Added default
    frontend_url: str = "https://3a5ea9256115.ngrok-free.app"   # Added default
    
    # Development
    debug: bool = False
    use_supabase_auth: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()