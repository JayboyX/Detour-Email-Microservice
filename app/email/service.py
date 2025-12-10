"""
Email Service for Detour
"""
import boto3
from botocore.exceptions import ClientError
import logging
from datetime import datetime, timezone
import json
import re
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
            logger.info("Email Service Initialized")
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
        
        subject = "Verify Your Email - Detour Driver App"
        html_body = self._create_verification_html_email(verification_url, user_name)
        text_body = self._create_verification_text_email(verification_url, user_name)
        
        return self._send_email_internal(email, subject, html_body, text_body)
    
    def send_wallet_welcome_email(self, email: str, user_name: str, wallet_number: str) -> bool:
        """Send welcome email for wallet creation"""
        subject = "Welcome to Detour - Your Driver Wallet is Ready"
        
        html_body = self._create_wallet_welcome_html(user_name, wallet_number)
        text_body = self._create_wallet_welcome_text(user_name, wallet_number)
        
        logger.info(f"Attempting to send wallet welcome email to: {email}")
        logger.info(f"User: {user_name}, Wallet: {wallet_number}")
        
        return self._send_email_internal(email, subject, html_body, text_body)
    
    def send_kyc_revoked_email(self, email: str, full_name: str, reason: str) -> bool:
        """Send KYC revoked email"""
        subject = "Your Detour KYC Has Been Revoked"
        
        html_body = self._create_kyc_revoked_html_email(full_name, reason)
        text_body = self._create_kyc_revoked_text_email(full_name, reason)
        
        logger.info(f"Attempting to send KYC revoked email to: {email}")
        
        return self._send_email_internal(email, subject, html_body, text_body)
    
    def send_subscription_confirmation_email(self, email: str, user_name: str, plan_name: str, 
                                           amount: str, billing_cycle: str, next_billing_date: str) -> bool:
        """Send subscription confirmation email"""
        subject = "Your Detour Subscription Confirmation"
        
        html_body = self._create_subscription_confirmation_html(user_name, plan_name, amount, billing_cycle, next_billing_date)
        text_body = self._create_subscription_confirmation_text(user_name, plan_name, amount, billing_cycle, next_billing_date)
        
        logger.info(f"Attempting to send subscription confirmation email to: {email}")
        
        return self._send_email_internal(email, subject, html_body, text_body)
    
    def send_password_reset_email(self, email: str, reset_url: str, user_name: str) -> bool:
        """Send password reset email"""
        subject = "Reset Your Password - Detour Driver App"
        
        html_body = self._create_password_reset_html_email(reset_url, user_name)
        text_body = self._create_password_reset_text_email(reset_url, user_name)
        
        logger.info(f"Attempting to send password reset email to: {email}")
        
        return self._send_email_internal(email, subject, html_body, text_body)
    
    def send_ride_completed_email(self, email: str, user_name: str, ride_id: str, 
                                amount: str, pickup_location: str, dropoff_location: str) -> bool:
        """Send ride completion confirmation email"""
        subject = "Ride Completed - Payment Processed"
        
        html_body = self._create_ride_completed_html_email(user_name, ride_id, amount, pickup_location, dropoff_location)
        text_body = self._create_ride_completed_text_email(user_name, ride_id, amount, pickup_location, dropoff_location)
        
        logger.info(f"Attempting to send ride completed email to: {email}")
        
        return self._send_email_internal(email, subject, html_body, text_body)
    
    def _validate_email(self, email: str) -> bool:
        """Validate email address format"""
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        return bool(email_pattern.match(email))
    
    def _send_email_internal(self, email: str, subject: str, html_body: str, text_body: str) -> bool:
        """Internal method to send email with fallback"""
        if not self._validate_email(email):
            logger.error(f"Invalid email address: {email}")
            return False
        
        if self.has_ses_permissions and not settings.debug:
            return self._send_via_ses(email, subject, html_body, text_body)
        else:
            return self._debug_send(email, subject, html_body, text_body)
    
    def _send_via_ses(self, email: str, subject: str, html_body: str, text_body: str) -> bool:
        """Send email via AWS SES"""
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
            
            logger.info(f"Email sent via SES to {email}")
            return True
            
        except ClientError as e:
            logger.error(f"SES send failed: {e.response['Error']['Code']}")
            return False
    
    def _debug_send(self, email: str, subject: str, html_body: str, text_body: str) -> bool:
        """Handle email in debug mode"""
        debug_info = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'mode': 'DEBUG' if settings.debug else 'FALLBACK',
            'recipient': email,
            'subject': subject,
            'html_preview': html_body[:500] + '...' if len(html_body) > 500 else html_body
        }
        
        print(f"\n{'='*60}")
        print(f"DEBUG MODE - Email to: {email}")
        print(f"Subject: {subject}")
        print(f"{'='*60}\n")
        
        try:
            with open('logs/email_debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps(debug_info, indent=2))
                f.write('\n' + '-'*50 + '\n')
        except Exception as e:
            logger.error(f"Failed to write debug log: {e}")
        
        return True
    
    def _create_base_html_template(self, title: str, user_name: str, content: str) -> str:
        """Create base HTML template for all emails"""
        current_year = datetime.now().year
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .header {{
            background-color: #2AB576;
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }}
        .content {{
            padding: 40px 30px;
        }}
        .content h2 {{
            color: #2AB576;
            margin-top: 0;
            font-size: 20px;
            font-weight: 600;
        }}
        .content p {{
            margin: 15px 0;
            font-size: 15px;
            color: #555;
        }}
        .info-box {{
            background: #f8f9fa;
            border-left: 4px solid #2AB576;
            padding: 20px;
            margin: 25px 0;
            border-radius: 4px;
        }}
        .button {{
            display: inline-block;
            background: #2AB576;
            color: white;
            padding: 14px 28px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            font-size: 15px;
            border: none;
            cursor: pointer;
        }}
        .footer {{
            background-color: #f8f9fa;
            padding: 25px 30px;
            text-align: center;
            color: #666;
            font-size: 13px;
            border-top: 1px solid #eaeaea;
        }}
        .footer a {{
            color: #2AB576;
            text-decoration: none;
        }}
        .highlight {{
            background: #fff9e6;
            border: 1px solid #ffe58f;
            padding: 12px 16px;
            border-radius: 6px;
            margin: 20px 0;
        }}
        ul {{
            padding-left: 20px;
        }}
        li {{
            margin: 8px 0;
            color: #555;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Detour Driver App</h1>
        </div>
        <div class="content">
            <h2>Hi {user_name},</h2>
            {content}
        </div>
        <div class="footer">
            <p>&copy; {current_year} Detour Driver App. All rights reserved.</p>
            <p>
                <a href="detourui://dashboard">Dashboard</a> | 
                <a href="detourui://support">Support</a> | 
                <a href="detourui://privacy">Privacy Policy</a>
            </p>
            <p style="font-size: 12px; margin-top: 10px; color: #888;">
                This is an automated message. Please do not reply to this email.
            </p>
        </div>
    </div>
</body>
</html>
"""
    
    def _create_verification_html_email(self, verification_url: str, user_name: str) -> str:
        """Create HTML for verification email"""
        content = f"""
            <p>Welcome to Detour! To complete your registration and access all driver features, please verify your email address.</p>
            
            <div class="info-box">
                <p><strong>Verification Link:</strong></p>
                <p>{verification_url}</p>
            </div>
            
            <p>Click the button below to verify your email address:</p>
            <a href="{verification_url}" class="button">Verify Email Address</a>
            
            <div class="highlight">
                <p><strong>Important:</strong> This verification link will expire in 24 hours.</p>
                <p>If you did not create a Detour account, please ignore this email.</p>
            </div>
            
            <p>Once verified, you'll be able to:</p>
            <ul>
                <li>Access your driver dashboard</li>
                <li>Complete your profile setup</li>
                <li>Start accepting ride requests</li>
                <li>Manage your earnings and wallet</li>
            </ul>
            
            <p>If you're having trouble with the button above, copy and paste the link into your browser.</p>
            
            <p>Best regards,<br>
            <strong>The Detour Team</strong></p>
        """
        
        return self._create_base_html_template("Verify Your Email - Detour", user_name, content)
    
    def _create_verification_text_email(self, verification_url: str, user_name: str) -> str:
        """Create plain text for verification email"""
        return f"""
Verify Your Email - Detour Driver App

Hi {user_name},

Welcome to Detour! To complete your registration and access all driver features, please verify your email address.

Verification Link: {verification_url}

Click the link above to verify your email address.

Important: This verification link will expire in 24 hours.
If you did not create a Detour account, please ignore this email.

Once verified, you'll be able to:
- Access your driver dashboard
- Complete your profile setup
- Start accepting ride requests
- Manage your earnings and wallet

If you're having trouble with the link above, copy and paste it into your browser.

Best regards,
The Detour Team
"""
    
    def _create_wallet_welcome_html(self, user_name: str, wallet_number: str) -> str:
        """Create HTML for wallet welcome email"""
        content = f"""
            <p>Congratulations! Your KYC verification has been <strong>approved</strong> and your driver wallet is now active.</p>
            
            <div class="info-box">
                <h3>Your Driver Wallet Details</h3>
                <p><strong>Wallet Number:</strong> {wallet_number}</p>
                <p><strong>Initial Balance:</strong> R 0.00</p>
                <p><strong>Status:</strong> Active</p>
                <p><strong>Activation Date:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
            </div>
            
            <p>You can now start earning as a Detour driver! Your wallet is ready to receive payments from completed rides.</p>
            
            <h3>Next Steps to Get Started:</h3>
            <ul>
                <li>Access your wallet from the Dashboard to view your balance</li>
                <li>Check available rides in your area from the Rides tab</li>
                <li>Set your availability status to start receiving ride requests</li>
                <li>Complete your driver profile with vehicle information</li>
            </ul>
            
            <div class="highlight">
                <p><strong>Premium Features Available:</strong> Enhance your driving experience with premium features including priority ride matching, advanced analytics, and dedicated support.</p>
                <a href="detourui://dashboard/subscription" class="button">View Subscription Plans</a>
            </div>
            
            <p>If you have any questions about your wallet or need assistance getting started, please visit our support section in the app.</p>
            
            <p>Welcome aboard and happy driving!<br>
            <strong>The Detour Team</strong></p>
        """
        
        return self._create_base_html_template("Your Driver Wallet is Ready - Detour", user_name, content)
    
    def _create_wallet_welcome_text(self, user_name: str, wallet_number: str) -> str:
        """Create text version for wallet welcome email"""
        return f"""
Welcome to Detour - Your Driver Wallet is Ready

Hi {user_name},

Congratulations! Your KYC verification has been approved and your driver wallet is now active.

Your Driver Wallet Details:
- Wallet Number: {wallet_number}
- Initial Balance: R 0.00
- Status: Active
- Activation Date: {datetime.now().strftime('%Y-%m-%d')}

You can now start earning as a Detour driver! Your wallet is ready to receive payments from completed rides.

Next Steps to Get Started:
1. Access your wallet from the Dashboard to view your balance
2. Check available rides in your area from the Rides tab
3. Set your availability status to start receiving ride requests
4. Complete your driver profile with vehicle information

Premium Features Available: Enhance your driving experience with premium features including priority ride matching, advanced analytics, and dedicated support.

View subscription plans in your dashboard under Subscription.

If you have any questions about your wallet or need assistance getting started, please visit our support section in the app.

Welcome aboard and happy driving!
The Detour Team
"""
    
    def _create_kyc_revoked_html_email(self, full_name: str, reason: str) -> str:
        """Create HTML for KYC revoked email"""
        content = f"""
            <p>Your KYC verification status has been updated after a manual review of your submitted documents.</p>
            
            <div class="info-box" style="border-left-color: #dc3545; background-color: #fff5f5;">
                <h3>KYC Status: Revoked</h3>
                <p><strong>Reason for Revocation:</strong></p>
                <p>{reason}</p>
                <p><strong>Effective Date:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
            </div>
            
            <p>Due to this revocation, your driver wallet has been temporarily suspended. You will not be able to:</p>
            <ul>
                <li>Access your wallet balance</li>
                <li>Withdraw funds from your wallet</li>
                <li>Receive new ride payments</li>
                <li>Accept new ride requests</li>
            </ul>
            
            <h3>How to Restore Access:</h3>
            <p>To restore your KYC status and regain full access to your wallet and driving privileges:</p>
            <ol>
                <li>Open the Detour Driver App</li>
                <li>Go to Profile > Documents</li>
                <li>Resubmit corrected or valid documentation</li>
                <li>Our compliance team will review within 24-48 hours</li>
            </ol>
            
            <a href="detourui://profile/documents" class="button">Resubmit Documents</a>
            
            <div class="highlight">
                <p><strong>Important:</strong> Any existing funds in your wallet remain secure and will be accessible once your KYC is re-approved.</p>
            </div>
            
            <p>If you believe this revocation was made in error, or if you need clarification on the required documents, please reply to this email for immediate support.</p>
            
            <p>Sincerely,<br>
            <strong>Detour Compliance Team</strong></p>
        """
        
        return self._create_base_html_template("KYC Status Update - Detour", full_name, content)
    
    def _create_kyc_revoked_text_email(self, full_name: str, reason: str) -> str:
        """Create text version for KYC revoked email"""
        return f"""
Your Detour KYC Has Been Revoked

Hi {full_name},

Your KYC verification status has been updated after a manual review of your submitted documents.

KYC Status: REVOKED
Reason for Revocation: {reason}
Effective Date: {datetime.now().strftime('%Y-%m-%d')}

Due to this revocation, your driver wallet has been temporarily suspended. You will not be able to:
- Access your wallet balance
- Withdraw funds from your wallet
- Receive new ride payments
- Accept new ride requests

How to Restore Access:
To restore your KYC status and regain full access to your wallet and driving privileges:
1. Open the Detour Driver App
2. Go to Profile > Documents
3. Resubmit corrected or valid documentation
4. Our compliance team will review within 24-48 hours

Important: Any existing funds in your wallet remain secure and will be accessible once your KYC is re-approved.

If you believe this revocation was made in error, or if you need clarification on the required documents, please reply to this email for immediate support.

Sincerely,
Detour Compliance Team
"""
    
    def _create_subscription_confirmation_html(self, user_name: str, plan_name: str, amount: str, 
                                             billing_cycle: str, next_billing_date: str) -> str:
        """Create HTML for subscription confirmation email"""
        content = f"""
            <p>Thank you for subscribing to Detour Premium! Your subscription has been successfully activated.</p>
            
            <div class="info-box">
                <h3>Subscription Details</h3>
                <p><strong>Plan:</strong> {plan_name}</p>
                <p><strong>Amount:</strong> {amount}</p>
                <p><strong>Billing Cycle:</strong> {billing_cycle}</p>
                <p><strong>Next Billing Date:</strong> {next_billing_date}</p>
                <p><strong>Status:</strong> Active</p>
            </div>
            
            <h3>Premium Features Now Available:</h3>
            <ul>
                <li><strong>Priority Ride Matching:</strong> Get matched with rides faster</li>
                <li><strong>Advanced Analytics:</strong> Detailed insights into your earnings and performance</li>
                <li><strong>Dedicated Support:</strong> Priority access to our support team</li>
                <li><strong>Higher Commission Rates:</strong> Keep more of your earnings</li>
                <li><strong>Extended Ride Radius:</strong> Access to rides in wider areas</li>
            </ul>
            
            <p>Your premium features are now active and available in your app. You can manage your subscription, update payment methods, or view billing history in the Subscription section of your dashboard.</p>
            
            <a href="detourui://dashboard/subscription" class="button">Manage Subscription</a>
            
            <div class="highlight">
                <p><strong>Need Help?</strong> If you have any questions about your subscription or premium features, visit our Help Center or contact premium support directly from the app.</p>
            </div>
            
            <p>Thank you for choosing Detour Premium. We're committed to helping you maximize your earnings and driving experience.</p>
            
            <p>Best regards,<br>
            <strong>Detour Premium Team</strong></p>
        """
        
        return self._create_base_html_template("Subscription Confirmation - Detour", user_name, content)
    
    def _create_subscription_confirmation_text(self, user_name: str, plan_name: str, amount: str, 
                                              billing_cycle: str, next_billing_date: str) -> str:
        """Create text version for subscription confirmation email"""
        return f"""
Your Detour Subscription Confirmation

Hi {user_name},

Thank you for subscribing to Detour Premium! Your subscription has been successfully activated.

Subscription Details:
- Plan: {plan_name}
- Amount: {amount}
- Billing Cycle: {billing_cycle}
- Next Billing Date: {next_billing_date}
- Status: Active

Premium Features Now Available:
- Priority Ride Matching: Get matched with rides faster
- Advanced Analytics: Detailed insights into your earnings and performance
- Dedicated Support: Priority access to our support team
- Higher Commission Rates: Keep more of your earnings
- Extended Ride Radius: Access to rides in wider areas

Your premium features are now active and available in your app. You can manage your subscription, update payment methods, or view billing history in the Subscription section of your dashboard.

Manage your subscription from the Subscription section in your dashboard.

Need Help? If you have any questions about your subscription or premium features, visit our Help Center or contact premium support directly from the app.

Thank you for choosing Detour Premium. We're committed to helping you maximize your earnings and driving experience.

Best regards,
Detour Premium Team
"""
    
    def _create_password_reset_html_email(self, reset_url: str, user_name: str) -> str:
        """Create HTML for password reset email"""
        content = f"""
            <p>We received a request to reset the password for your Detour account.</p>
            
            <div class="info-box">
                <p><strong>Reset Link:</strong></p>
                <p>{reset_url}</p>
            </div>
            
            <p>Click the button below to reset your password:</p>
            <a href="{reset_url}" class="button">Reset Password</a>
            
            <div class="highlight">
                <p><strong>Security Notice:</strong> This password reset link will expire in 1 hour.</p>
                <p>If you did not request a password reset, please ignore this email. Your account remains secure.</p>
            </div>
            
            <h3>Password Security Tips:</h3>
            <ul>
                <li>Use a unique password that you don't use for other accounts</li>
                <li>Include a mix of uppercase, lowercase, numbers, and special characters</li>
                <li>Avoid using personal information like birthdays or names</li>
                <li>Consider using a password manager to generate and store secure passwords</li>
            </ul>
            
            <p>If you're having trouble resetting your password or suspect unauthorized access to your account, please contact our support team immediately.</p>
            
            <p>Stay secure,<br>
            <strong>Detour Security Team</strong></p>
        """
        
        return self._create_base_html_template("Reset Your Password - Detour", user_name, content)
    
    def _create_password_reset_text_email(self, reset_url: str, user_name: str) -> str:
        """Create text version for password reset email"""
        return f"""
Reset Your Password - Detour Driver App

Hi {user_name},

We received a request to reset the password for your Detour account.

Reset Link: {reset_url}

Click the link above to reset your password.

Security Notice: This password reset link will expire in 1 hour.
If you did not request a password reset, please ignore this email. Your account remains secure.

Password Security Tips:
- Use a unique password that you don't use for other accounts
- Include a mix of uppercase, lowercase, numbers, and special characters
- Avoid using personal information like birthdays or names
- Consider using a password manager to generate and store secure passwords

If you're having trouble resetting your password or suspect unauthorized access to your account, please contact our support team immediately.

Stay secure,
Detour Security Team
"""
    
    def _create_ride_completed_html_email(self, user_name: str, ride_id: str, amount: str, 
                                        pickup_location: str, dropoff_location: str) -> str:
        """Create HTML for ride completion email"""
        content = f"""
            <p>Great news! Payment for your completed ride has been processed and added to your wallet.</p>
            
            <div class="info-box">
                <h3>Ride Payment Details</h3>
                <p><strong>Ride ID:</strong> {ride_id}</p>
                <p><strong>Amount Credited:</strong> {amount}</p>
                <p><strong>Pickup Location:</strong> {pickup_location}</p>
                <p><strong>Dropoff Location:</strong> {dropoff_location}</p>
                <p><strong>Completion Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                <p><strong>Payment Status:</strong> Completed</p>
            </div>
            
            <p>The payment has been successfully transferred to your driver wallet. You can now:</p>
            <ul>
                <li>View your updated wallet balance in the Dashboard</li>
                <li>Track this transaction in your Earnings History</li>
                <li>Withdraw funds to your linked bank account</li>
                <li>Review ride details and customer rating</li>
            </ul>
            
            <a href="detourui://dashboard/wallet" class="button">View Wallet Balance</a>
            
            <div class="highlight">
                <p><strong>Earnings Tip:</strong> Premium subscribers earn 15% more on average rides. Consider upgrading to maximize your earnings potential.</p>
                <a href="detourui://dashboard/subscription" style="background-color: #6c757d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-size: 14px; display: inline-block; margin-top: 10px;">Learn About Premium</a>
            </div>
            
            <h3>Your Next Opportunity Awaits</h3>
            <p>Keep up the great work! More rides are available in your area. Set your status to "Available" to receive new ride requests.</p>
            
            <p>Thank you for providing excellent service with Detour. Your commitment helps us build a reliable transportation network.</p>
            
            <p>Drive safely,<br>
            <strong>The Detour Team</strong></p>
        """
        
        return self._create_base_html_template("Ride Completed - Payment Processed", user_name, content)
    
    def _create_ride_completed_text_email(self, user_name: str, ride_id: str, amount: str, 
                                         pickup_location: str, dropoff_location: str) -> str:
        """Create text version for ride completion email"""
        return f"""
Ride Completed - Payment Processed

Hi {user_name},

Great news! Payment for your completed ride has been processed and added to your wallet.

Ride Payment Details:
- Ride ID: {ride_id}
- Amount Credited: {amount}
- Pickup Location: {pickup_location}
- Dropoff Location: {dropoff_location}
- Completion Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
- Payment Status: Completed

The payment has been successfully transferred to your driver wallet. You can now:
- View your updated wallet balance in the Dashboard
- Track this transaction in your Earnings History
- Withdraw funds to your linked bank account
- Review ride details and customer rating

View your wallet balance from the Wallet section in your dashboard.

Earnings Tip: Premium subscribers earn 15% more on average rides. Consider upgrading to maximize your earnings potential.

Your Next Opportunity Awaits
Keep up the great work! More rides are available in your area. Set your status to "Available" to receive new ride requests.

Thank you for providing excellent service with Detour. Your commitment helps us build a reliable transportation network.

Drive safely,
The Detour Team
"""

# Create global instance
email_service = EmailService()