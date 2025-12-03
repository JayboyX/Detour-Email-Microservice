from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    app_name: str = "Detour Microservices"
    debug: bool = False
    app_scheme: str = "detourui"
    api_base_url: str
    frontend_url: str = "http://localhost:3000"
    
    # Database
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role: str
    
    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    verification_token_expire_hours: int = 24
    
    # Email
    ses_sender_email: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-1"
    
    # SMS
    sms_user: Optional[str] = None
    sms_password: Optional[str] = None
    sms_api_url: str = "https://api.winsms.co.za/api/batchmessage.asp"
    otp_expiry_minutes: int = 10
    otp_max_attempts: int = 3
    otp_resend_delay_seconds: int = 60
    
    # Development
    use_supabase_auth: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()