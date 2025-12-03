"""
Email Service for Detour
"""
import boto3
from botocore.exceptions import ClientError
import logging
from datetime import datetime, timezone
import json
from app.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.sender_email = settings.ses_sender_email
        self.aws_region = settings.aws_region
        self.has_ses_permissions = False
        
        try:
            self.ses_client = boto3.client(
                'ses',
                region_name=self.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
            self._check_permissions()
            logger.info("✅ Email Service Initialized")
        except Exception as e:
            logger.error(f"Failed to initialize EmailService: {e}")
    
    def _check_permissions(self):
        """Check if we have SES permissions"""
        try:
            self.ses_client.get_send_quota()
            self.has_ses_permissions = True
        except ClientError as e:
            logger.warning(f"No SES permissions: {e.response['Error']['Code']}")
            self.has_ses_permissions = False
    
    def send_verification_email(self, email: str, verification_url: str, user_name: str) -> bool:
        """Send email verification email"""
        if not self._validate_email(email):
            logger.error(f"Invalid email address: {email}")
            return False
        
        if self.has_ses_permissions and not settings.debug:
            return self._send_via_ses(email, verification_url, user_name)
        else:
            return self._debug_send(email, verification_url, user_name)
    
    def _validate_email(self, email: str) -> bool:
        """Validate email address format"""
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        return bool(email_pattern.match(email))
    
    def _send_via_ses(self, email: str, verification_url: str, user_name: str) -> bool:
        """Send email via AWS SES"""
        subject = "Verify Your Email - Detour Driver App"
        html_body = self._create_html_email(verification_url, user_name)
        text_body = self._create_text_email(verification_url, user_name)
        
        try:
            response = self.ses_client.send_email(
                Source=self.sender_email,
                Destination={'ToAddresses': [email]},
                Message={
                    'Subject': {'Charset': 'UTF-8', 'Data': subject},
                    'Body': {
                        'Html': {'Charset': 'UTF-8', 'Data': html_body},
                        'Text': {'Charset': 'UTF-8', 'Data': text_body},
                    },
                }
            )
            
            logger.info(f"✅ Email sent via SES to {email}")
            return True
            
        except ClientError as e:
            logger.error(f"❌ SES send failed: {e.response['Error']['Code']}")
            return False
    
    def _debug_send(self, email: str, verification_url: str, user_name: str) -> bool:
        """Handle email in debug mode"""
        debug_info = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'mode': 'DEBUG' if settings.debug else 'FALLBACK',
            'recipient': email,
            'verification_url': verification_url,
            'user_name': user_name
        }
        
        print(f"\n{'='*60}")
        print(f"📧 DEBUG MODE - Email to: {email}")
        print(f"   Verification URL: {verification_url}")
        print(f"{'='*60}\n")
        
        try:
            with open('logs/email_debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps(debug_info, indent=2))
                f.write('\n' + '-'*50 + '\n')
        except Exception as e:
            logger.error(f"Failed to write debug log: {e}")
        
        return True
    
    def _create_html_email(self, verification_url: str, user_name: str) -> str:
        """Create HTML email template"""
        current_year = datetime.now().year
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verify Your Email - Detour</title>
        </head>
        <body>
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1>🚗 Welcome to Detour, {user_name}!</h1>
                <p>Click the link below to verify your email:</p>
                <p><a href="{verification_url}" style="background-color: #2AB576; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">Verify Email</a></p>
                <p>Or copy this link: {verification_url}</p>
                <p>This link expires in 24 hours.</p>
                <p>Best regards,<br>The Detour Team</p>
                <hr>
                <p style="color: #666; font-size: 12px;">© {current_year} Detour Driver App</p>
            </div>
        </body>
        </html>
        """
    
    def _create_text_email(self, verification_url: str, user_name: str) -> str:
        """Create plain text email"""
        current_year = datetime.now().year
        return f"""
        Verify Your Email - Detour Driver App
        
        Hi {user_name},
        
        Verify your email by clicking: {verification_url}
        
        This link expires in 24 hours.
        
        Best regards,
        The Detour Team
        
        © {current_year} Detour Driver App.
        """

# Create global instance
email_service = EmailService()