# Detour Microservices

Email, SMS, and Authentication services for Detour Driver App.

## Services

- **Auth**: User registration, login, email verification
- **Email**: AWS SES email sending
- **SMS**: WinSMS OTP sending

## Setup

1. Copy `.env.example` to `.env` and configure
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python run.py`

## API Endpoints

- `POST /api/auth/signup` - Register user
- `POST /api/auth/verify-email` - Verify email
- `POST /api/auth/login` - User login
- `POST /api/auth/send-phone-otp` - Send SMS OTP
