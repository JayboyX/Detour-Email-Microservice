"""
AWS SES Email Service for Detour Driver App
Complete production-ready email service
"""

import boto3
from botocore.exceptions import ClientError
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.config import settings
import json
import time

logger = logging.getLogger(__name__)

class EmailService:
    """
    AWS SES Email Service with permission-aware error handling
    """
    
    def __init__(self):
        """
        Initialize SES client with fallback mechanisms
        """
        self.sender_email = settings.ses_sender_email
        self.aws_region = settings.aws_region
        self.has_ses_permissions = False
        self.initialized = False
        
        try:
            # Initialize SES client
            self.ses_client = boto3.client(
                'ses',
                region_name=self.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
            
            # Test permissions
            self._check_permissions()
            
            if self.has_ses_permissions:
                self._log_successful_init()
            else:
                self._log_permission_warning()
                
            self.initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize EmailService: {e}")
            self._log_failed_init(e)
    
    def _check_permissions(self):
        """
        Check if we have the necessary SES permissions
        """
        try:
            # Test with a simple SES API call that requires minimal permissions
            self.ses_client.get_send_quota()
            self.has_ses_permissions = True
            
            # Log available permissions
            if settings.debug:
                print(f"✅ SES permissions verified for region: {self.aws_region}")
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'InvalidClientTokenId':
                logger.error("Invalid AWS credentials")
                self.has_ses_permissions = False
            elif error_code == 'AccessDeniedException':
                logger.warning("Missing SES permissions")
                self.has_ses_permissions = False
            else:
                logger.error(f"SES permission check failed: {error_code}")
                self.has_ses_permissions = False
    
    def _log_successful_init(self):
        """Log successful initialization"""
        logger.info("✅ Email Service Initialized Successfully")
        logger.info(f"   Sender: {self.sender_email}")
        logger.info(f"   Region: {self.aws_region}")
        logger.info(f"   Has SES Permissions: Yes")
        
        if settings.debug:
            print(f"✅ Email service ready with SES permissions")
    
    def _log_permission_warning(self):
        """Log permission warnings"""
        logger.warning("⚠️  Email Service initialized WITHOUT SES permissions")
        logger.warning("   Emails will be logged to file instead of being sent")
        logger.warning("   To fix: Add SES permissions to your IAM user")
        logger.warning("   Required actions: ses:SendEmail, ses:SendRawEmail")
        
        if settings.debug:
            print(f"⚠️  Email service running in debug mode (no SES permissions)")
            print(f"   To send real emails, add SES permissions to your AWS user")
    
    def _log_failed_init(self, error: Exception):
        """Log initialization failure"""
        logger.error("❌ Email Service failed to initialize")
        logger.error(f"   Error: {error}")
        
        if settings.debug:
            print(f"❌ Email service initialization failed")
            print(f"   Error: {error}")
    
    def send_verification_email(self, email: str, verification_url: str, user_name: str) -> bool:
        """
        Send email verification email
        Falls back to debug mode if no SES permissions
        """
        # Always validate email
        if not self._validate_email(email):
            logger.error(f"Invalid email address: {email}")
            return False
        
        # Check if we can send via SES
        if self.has_ses_permissions and not settings.debug:
            return self._send_via_ses(email, verification_url, user_name)
        else:
            # Fallback to debug/logging mode
            return self._debug_send(email, verification_url, user_name)
    
    def _validate_email(self, email: str) -> bool:
        """Validate email address format"""
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        return bool(email_pattern.match(email))
    
    def _send_via_ses(self, email: str, verification_url: str, user_name: str) -> bool:
        """
        Send email via AWS SES
        """
        subject = "Verify Your Email - Detour Driver App"
        
        # Create email content
        html_body = self._create_html_email(verification_url, user_name)
        text_body = self._create_text_email(verification_url, user_name)
        
        try:
            # Send email
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
            
            message_id = response['MessageId']
            
            # Log success
            logger.info(f"✅ Email sent via SES to {email}")
            logger.info(f"   Message ID: {message_id}")
            
            # Store for monitoring
            self._log_sent_email(email, message_id, 'ses')
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            logger.error(f"❌ SES send failed for {email}")
            logger.error(f"   Error: {error_code} - {error_message}")
            
            # Fallback to debug mode on certain errors
            if error_code in ['AccessDenied', 'InvalidClientTokenId']:
                logger.warning("Falling back to debug mode for this email")
                return self._debug_send(email, verification_url, user_name)
            
            return False
    
    def _debug_send(self, email: str, verification_url: str, user_name: str) -> bool:
        """
        Handle email in debug/logging mode
        """
        debug_info = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'mode': 'DEBUG' if settings.debug else 'FALLBACK (no SES permissions)',
            'recipient': email,
            'verification_url': verification_url,
            'user_name': user_name,
            'sender': self.sender_email,
            'sent_via_ses': False
        }
        
        # Log to console
        print(f"\n{'='*60}")
        print(f"📧 {'DEBUG' if settings.debug else 'FALLBACK'} MODE")
        print(f"   To: {email}")
        print(f"   User: {user_name}")
        print(f"   URL: {verification_url}")
        if not self.has_ses_permissions:
            print(f"   ⚠️  No SES permissions - email logged to file")
        print(f"{'='*60}\n")
        
        # Log to file
        try:
            with open('email_log.json', 'a', encoding='utf-8') as f:
                f.write(json.dumps(debug_info, indent=2))
                f.write('\n' + '-'*50 + '\n')
            
            # Also create HTML preview
            html_content = self._create_html_email(verification_url, user_name)
            with open('email_preview.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Email logged to file for {email}")
            
        except Exception as e:
            logger.error(f"Failed to write debug log: {e}")
        
        return True
    
    def _log_sent_email(self, recipient: str, message_id: str, method: str):
        """Log sent email details"""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'recipient': recipient,
            'message_id': message_id,
            'method': method,
            'sender': self.sender_email
        }
        
        if settings.debug:
            print(f"📨 Email {method}: {log_entry}")
    
    def get_send_statistics(self) -> Dict[str, Any]:
        """
        Get current SES sending statistics
        """
        try:
            if not self.has_ses_permissions:
                return {
                    'error': 'No SES permissions',
                    'status': 'debug_mode',
                    'max_24_hour_send': 0,
                    'sent_last_24_hours': 0,
                    'max_send_rate': 0,
                    'available_quota': 0
                }
            
            quota = self.ses_client.get_send_quota()
            
            return {
                'max_24_hour_send': quota.get('Max24HourSend', 0),
                'sent_last_24_hours': quota.get('SentLast24Hours', 0),
                'max_send_rate': quota.get('MaxSendRate', 0),
                'available_quota': quota.get('Max24HourSend', 0) - quota.get('SentLast24Hours', 0)
            }
            
        except ClientError as e:
            logger.error(f"Failed to get send statistics: {e}")
            return {
                'error': str(e),
                'status': 'error',
                'max_24_hour_send': 0,
                'sent_last_24_hours': 0,
                'max_send_rate': 0,
                'available_quota': 0
            }
    
    def check_sender_status(self) -> Dict[str, Any]:
        """
        Check sender email verification status
        """
        try:
            if not self.has_ses_permissions:
                return {
                    'status': 'no_permissions',
                    'verified': False,
                    'sender_email': self.sender_email
                }
            
            response = self.ses_client.get_identity_verification_attributes(
                Identities=[self.sender_email]
            )
            
            verification_attrs = response.get('VerificationAttributes', {})
            sender_attrs = verification_attrs.get(self.sender_email, {})
            status = sender_attrs.get('VerificationStatus', 'Not Found')
            
            return {
                'status': status,
                'verified': status == 'Success',
                'sender_email': self.sender_email
            }
            
        except ClientError as e:
            logger.error(f"Failed to check sender status: {e}")
            return {
                'error': str(e),
                'sender_email': self.sender_email
            }
    
    def verify_sender_email(self) -> bool:
        """
        Start verification process for sender email
        Returns True if verification email was sent
        """
        try:
            response = self.ses_client.verify_email_identity(
                EmailAddress=self.sender_email
            )
            
            logger.info(f"Verification email sent to {self.sender_email}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to send verification email: {e}")
            return False
    
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
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 0 20px rgba(0,0,0,0.1); }}
                .header {{ background-color: #2AB576; color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 30px; }}
                .button {{ background-color: #2AB576; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: bold; font-size: 16px; }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚗 Welcome to Detour!</h1>
                    <p>Your journey to earning starts here</p>
                </div>
                
                <div class="content">
                    <h2>Hi {user_name},</h2>
                    <p>Thank you for signing up to become a Detour driver! To activate your account, please verify your email.</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{verification_url}" class="button">✅ Verify My Email</a>
                    </div>
                    
                    <p><strong>Link not working?</strong> Copy and paste this URL:</p>
                    <div style="background: #f8f9fa; padding: 12px; border-radius: 4px; font-family: monospace;">
                        {verification_url}
                    </div>
                    
                    <p><strong>⚠️ Important:</strong> This link expires in 24 hours.</p>
                    
                    <p>Best regards,<br>The Detour Team</p>
                </div>
                
                <div class="footer">
                    <p>© {current_year} Detour Driver App. All rights reserved.</p>
                    <p>Intermediate DS | justice@intermediateds.co.za</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _create_text_email(self, verification_url: str, user_name: str) -> str:
        """Create plain text email version"""
        current_year = datetime.now().year
        
        return f"""
        Verify Your Email - Detour Driver App
        
        Hi {user_name},
        
        Thank you for signing up to become a Detour driver!
        
        VERIFICATION LINK:
        {verification_url}
        
        Click the link above to verify your email.
        
        This link expires in 24 hours.
        
        Best regards,
        The Detour Team
        
        © {current_year} Detour Driver App.
        """


# Create global instance
email_service = EmailService()