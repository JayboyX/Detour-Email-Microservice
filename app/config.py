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
    api_base_url: str = "https://sjkixfkta8.us-east-1.awsapprunner.com"  # Added default
    frontend_url: str = "https://sjkixfkta8.us-east-1.awsapprunner.com"   # Added default
    
    # Development
    debug: bool = False
    use_supabase_auth: bool = False
    

    # SMS Configuration
    sms_user: Optional[str] = None
    sms_password: Optional[str] = None
    sms_api_url: str = "https://api.winsms.co.za/api/batchmessage.asp"
    
    # OTP Configuration
    otp_expiry_minutes: int = 10
    otp_max_attempts: int = 3
    otp_resend_delay_seconds: int = 60
    
    class Config:
        env_file = ".env"

settings = Settings()

