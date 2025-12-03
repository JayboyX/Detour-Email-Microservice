
# 🚗 Detour Microservices

**Email, SMS, and Authentication services for Detour Driver App** - A production-ready FastAPI microservice deployed on AWS App Runner.

## 📋 Overview

| Service                  | Description                                  | Endpoints        |
| ------------------------ | -------------------------------------------- | ---------------- |
| **Authentication** | User registration, login, email verification | `/api/auth/*`  |
| **Email**          | AWS SES email sending for verification       | `/api/email/*` |
| **SMS**            | WinSMS OTP sending for phone verification    | `/api/sms/*`   |

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Locally

```bash
python run.py
```

Server starts at: `http://localhost:8000`

### 4. AWS App Runner Deployment

1. Connect GitHub repository
2. Set environment variables in App Runner console
3. Build command: `pip install -r requirements.txt`
4. Start command: `python run.py`

## 🔧 Environment Variables

### Required:

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE=your-service-role-key

# JWT
JWT_SECRET_KEY=your-secret-key

# AWS SES
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
SES_SENDER_EMAIL=verified-email@domain.com

# App
API_BASE_URL=https://your-app-runner-url.awsapprunner.com
```

### Optional:

```env
# SMS (WinSMS)
SMS_USER=your-winsms-username
SMS_PASSWORD=your-winsms-password

# Development
DEBUG=True
```

## 📡 API Reference

### **Authentication Service** (`/api/auth`)

#### **Register User**

```http
POST /api/auth/signup
```

**Request:**

```json
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "password": "password123",
  "terms_agreed": true,
  "phone_number": "+27721234567"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Account created! Check email for verification.",
  "data": {
    "user_id": "uuid",
    "email": "john@example.com",
    "requires_verification": true
  }
}
```

#### **Verify Email**

```http
POST /api/auth/verify-email
```

**Request:**

```json
{
  "token": "jwt-verification-token"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Email verified successfully!",
  "data": {
    "user_id": "uuid",
    "email": "john@example.com",
    "verified": true
  }
}
```

#### **User Login**

```http
POST /api/auth/login
```

**Request:**

```json
{
  "email": "john@example.com",
  "password": "password123"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access_token": "jwt-token",
    "token_type": "bearer",
    "user": {
      "id": "uuid",
      "email": "john@example.com",
      "full_name": "John Doe",
      "email_verified": true
    }
  }
}
```

#### **Send SMS OTP**

```http
POST /api/auth/send-phone-otp
```

**Request:**

```json
{
  "user_id": "uuid",
  "phone_number": "+27721234567"
}
```

**Response:**

```json
{
  "success": true,
  "message": "OTP sent to +27721234567",
  "data": {
    "expires_in_minutes": 10,
    "user_id": "uuid",
    "simulated": false
  }
}
```

### **Email Service** (`/api/email`)

#### **Test Email Service**

```http
GET /api/email/test-email
```

**Response:**

```json
{
  "success": true,
  "message": "Email service is running",
  "sender": "justice@intermediateds.co.za",
  "has_ses_permissions": true
}
```

### **SMS Service** (`/api/sms`)

#### **Test SMS Service**

```http
GET /api/sms/test-sms
```

**Response:**

```json
{
  "success": true,
  "message": "SMS service is connected",
  "data": {
    "initialized": true,
    "user": "johannes@intermediateds.co.za"
  }
}
```

## 🌐 Web Pages

### **Email Verification Page**

```http
GET /verify-email?token=jwt-token
```

- Interactive HTML page for email verification
- Shows success/error messages
- Deep links to mobile app: `detourui://login`

### **API Documentation**

```http
GET /docs
```

- Interactive Swagger UI (when `DEBUG=True`)
- Test all endpoints directly
- Available at: `https://your-app-runner-url/docs`

### **Health Check**

```http
GET /health
```

**Response:**

```json
{
  "status": "healthy",
  "service": "detour-microservices",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 📁 Project Structure

```
Detour-Microservices/
├── app/
│   ├── shared/           # Shared services
│   │   ├── database.py   # Supabase client
│   │   └── auth.py       # JWT authentication
│   ├── auth/            # Authentication microservice
│   │   ├── router.py    # Auth endpoints
│   │   ├── service.py   # Auth business logic
│   │   └── schemas.py   # Pydantic models
│   ├── email/           # Email microservice
│   │   ├── router.py    # Email endpoints
│   │   └── service.py   # AWS SES service
│   ├── sms/             # SMS microservice
│   │   ├── router.py    # SMS endpoints
│   │   ├── service.py   # WinSMS service
│   │   └── otp_service.py  # OTP generation
│   ├── main.py          # FastAPI app
│   └── config.py        # Configuration
├── run.py              # Entry point
├── requirements.txt    # Dependencies
└── .env               # Environment variables
```

## 🔐 Security Notes

1. **Password Security**:

   - Passwords hashed with bcrypt
   - Auto-truncated to 72 characters (bcrypt limit)
   - Never stored in plain text
2. **JWT Tokens**:

   - Email verification tokens: 24-hour expiry
   - Access tokens: 24-hour expiry
   - Signed with HS256 algorithm
3. **Environment Variables**:

   - Never commit `.env` to version control
   - Use App Runner secrets for production

## 🐛 Troubleshooting

### **Email Not Sending**

1. Check AWS SES permissions in App Runner IAM role
2. Verify sender email in AWS SES console
3. Check App Runner logs for email service errors
4. Test with `/api/email/test-email` endpoint

### **SMS Not Sending**

1. Verify WinSMS credentials in `.env`
2. Check SMS credits in WinSMS account
3. Test with `/api/sms/test-sms` endpoint
4. Phone numbers must be South African format: `27XXXXXXXXX`

### **Database Errors**

1. Verify Supabase URL and keys
2. Check if tables exist: `users`
3. Ensure service role has write permissions

### **Common HTTP Errors**

- `404`: Endpoint doesn't exist
- `422`: Validation error (check request format)
- `500`: Server error (check App Runner logs)

## 📊 Monitoring

### **Logs Location**

- **App Runner**: AWS Console → App Runner → Logs
- **Local**: Console output and `logs/` directory
- **Email logs**: `logs/email_debug.log`
- **SMS logs**: `logs/sms_debug.log`

### **Health Checks**

```bash
# API health
curl https://your-app-runner-url/health

# Service status
curl https://your-app-runner-url/api/email/test-email
curl https://your-app-runner-url/api/sms/test-sms
```

## 🚢 Deployment Checklist

- [ ] AWS SES sender email verified
- [ ] Supabase tables created (`users`)
- [ ] Environment variables set in App Runner
- [ ] IAM role with SES permissions attached to App Runner
- [ ] CORS configured for mobile app domains
- [ ] SSL certificate valid (auto-managed by App Runner)

## 📞 Support

**Issues**: Check App Runner logs first
**Email**: justice@intermediateds.co.za
**API Docs**: `https://your-app-runner-url/docs`

---

**Version**: 1.0.0
**Last Updated**: December 2024
**Status**: ✅ Production Ready
