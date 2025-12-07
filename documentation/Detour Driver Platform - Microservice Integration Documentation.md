# Detour Driver Platform - Microservice Integration Documentation

## Overview

This documentation provides a comprehensive guide for frontend developers integrating with the Detour driver platform microservices. It covers API endpoints, request/response formats, and frontend navigation flows.

## Table of Contents

1. [Authentication Microservice](#authentication-microservice)
2. [Email Microservice](#email-microservice)
3. [KYC Microservice](#kyc-microservice)
4. [OTP/SMS Microservice](#otpsms-microservice)
5. [Wallet Microservice](#wallet-microservice)
6. [Subscription Microservice](#subscription-microservice)
7. [Workflow Diagrams](#workflow-diagrams)
8. [Frontend Storage Requirements](#frontend-storage-requirements)

---

## Authentication Microservice

**Base Path:** `/api/auth/*`

### 1. Register User

**Endpoint:** `POST /api/auth/register`

**Used in:** Signup Screen

**Request:**

```json
{
  "full_name": "John Driver",
  "email": "driver@mail.com",
  "password": "123456",
  "phone_number": "0721234567",
  "terms_agreed": true
}
```

**Response:**

```json
{
  "success": true,
  "message": "Account created. Please verify your email.",
  "data": {
    "user_id": "uuid",
    "email": "driver@mail.com",
    "email_verified": false
  }
}
```

**Frontend Action:** Show "Verify your email" screen

### 2. Login User

**Endpoint:** `POST /api/auth/login`

**Used in:** Login Screen

**Request:**

```json
{
  "email": "driver@mail.com",
  "password": "123456"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "token": "jwt-token-here",
    "user": {
      "id": "uuid",
      "full_name": "John Driver",
      "email_verified": true,
      "is_kyc_verified": false
    }
  }
}
```

**Frontend Navigation:**

- `email_verified == false` → Redirect to verify email screen
- `is_kyc_verified == false` → Redirect to KYC onboarding
- Both verified → Dashboard

### 3. Verify Email

**Endpoint:** `GET /api/auth/verify-email?token=xxx`

**Used in:** Email link → opens browser

**Request:** None (link clicked from email)

**Response:**

```json
{
  "success": true,
  "message": "Email verified successfully"
}
```

### 4. Request Phone OTP

**Endpoint:** `POST /api/auth/phone/send-otp`

**Used in:** Phone Verification Screen (KYC step)

**Request:**

```json
{
  "user_id": "uuid",
  "phone_number": "0721234567"
}
```

**Response:**

```json
{
  "success": true,
  "message": "OTP sent successfully",
  "data": {
    "expires_in": 300
  }
}
```

### 5. Verify Phone OTP

**Endpoint:** `POST /api/auth/phone/verify`

**Used in:** Phone OTP Screen

**Request:**

```json
{
  "user_id": "uuid",
  "otp": "123456"
}
```

**Response (Success):**

```json
{
  "success": true,
  "message": "Phone number verified"
}
```

**Response (Failure):**

- Invalid OTP: `"Invalid OTP"`
- Expired OTP: `"OTP expired"`
- Too many attempts: `"Too many failed attempts. Please request a new OTP."`

### 6. Refresh Token

**Endpoint:** `POST /api/auth/refresh`

**Used in:** App background token management

**Request:**

```json
{
  "refresh_token": "some-refresh-token"
}
```

**Response:**

```json
{
  "success": true,
  "token": "new-jwt-token"
}
```

---

## Email Microservice

**Base Path:** `/api/email/*`

### 1. Send Generic Email

**Endpoint:** `POST /api/email/send`

**Used in:** Admin/testing integrations

**Request:**

```json
{
  "to": "driver@mail.com",
  "subject": "Test Email",
  "html_content": "<p>Hello Driver!</p>"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Email processed",
  "data": {
    "simulated": false
  }
}
```

### 2. Test Email Endpoint

**Endpoint:** `GET /api/email/test`

**Used in:** Developer/admin panel testing

**Response:**

```json
{
  "success": true,
  "message": "Email test executed",
  "data": {
    "status": "sent"
  }
}
```

### Email Events Triggered by Other Services

- **Account Verification:** Triggered by `/api/auth/register`
- **Subscription Confirmation:** Triggered by `/api/subscriptions/activate`
- **KYC Approved:** Triggered by admin verification
- **Wallet Creation:** Triggered after KYC approval
- **Failed Payments:** Triggered by billing cronjob

**Frontend Note:** The frontend never sends emails directly; emails are triggered automatically through backend workflows.

---

## KYC Microservice

**Base Path:** `/api/kyc/*`

### 1. Submit KYC Information

**Endpoint:** `POST /api/kyc/submit`

**Used in:** KYC Form Screen

**Request:**

```json
{
  "user_id": "uuid",
  "id_number": "0101015800082",
  "first_name": "John",
  "last_name": "Driver",
  "date_of_birth": "1990-01-01",
  "phone_number": "0721234567",
  "address": "123 Main Street, Soweto",
  "proof_of_address_url": "https://bucket/file1.png",
  "id_document_url": "https://bucket/file2.png",
  "selfie_url": "https://bucket/file3.png",
  "bank_account_number": "123456789",
  "bank_name": "FNB"
}
```

**Response:**

```json
{
  "success": true,
  "message": "KYC submitted successfully. Please wait for approval.",
  "data": {
    "kyc_status": "pending"
  }
}
```

### 2. Check KYC Status

**Endpoint:** `GET /api/kyc/status/{user_id}`

**Used in:** App startup, dashboard load

**Response:**

```json
{
  "success": true,
  "data": {
    "kyc_status": "pending",
    "bav_status": "pending",
    "phone_verified": true,
    "is_ready_for_wallet": false
  }
}
```

**Status Mapping:**

| Status       | Frontend Action           |
| ------------ | ------------------------- |
| `null`     | Start KYC flow            |
| `pending`  | Show waiting screen       |
| `rejected` | Show rejection + resubmit |
| `approved` | Continue to wallet        |

### 3. Admin Verification

**Endpoint:** `POST /api/kyc/admin/verify`

**Note:** Admin dashboard only - triggers wallet creation automatically

---

## OTP/SMS Microservice

**Base Path:** `/api/auth/phone/*`

### 1. Send OTP

**Endpoint:** `POST /api/auth/phone/send-otp`

**Used in:** Phone Verification Screen

**Request:**

```json
{
  "user_id": "uuid",
  "phone_number": "0721234567"
}
```

**Response:**

```json
{
  "success": true,
  "message": "OTP sent successfully",
  "data": {
    "expires_in": 300
  }
}
```

### 2. Verify OTP

**Endpoint:** `POST /api/auth/phone/verify`

**Used in:** OTP Entry Screen

**Request:**

```json
{
  "user_id": "uuid",
  "otp": "123456"
}
```

**Success Response:**

```json
{
  "success": true,
  "message": "Phone number verified"
}
```

**Frontend Flow:**

- Success → Redirect to KYC Form
- Failure → Show error, allow retry
- Expired → Enable "Resend OTP"

**Resend OTP:** Call `/api/auth/phone/send-otp` again

---

## Wallet Microservice

**Base Path:** `/api/wallet/*`

### 1. Get User Wallet

**Endpoint:** `GET /api/wallet/user/{user_id}`

**Used in:** App startup, dashboard load

**Response (Wallet exists):**

```json
{
  "success": true,
  "message": "Wallet retrieved",
  "data": {
    "has_wallet": true,
    "wallet": {
      "id": "uuid",
      "user_id": "uuid",
      "wallet_number": "WLT-ABC123",
      "balance": 0,
      "currency": "ZAR",
      "status": "active"
    }
  }
}
```

**Response (No wallet):**

```json
{
  "success": true,
  "data": {
    "has_wallet": false
  }
}
```

### 2. Get Wallet Balance

**Endpoint:** `GET /api/wallet/{wallet_id}/balance`

**Used in:** Wallet home, dashboard widget

**Response:**

```json
{
  "success": true,
  "message": "Balance retrieved",
  "data": {
    "wallet_id": "uuid",
    "wallet_number": "WLT-ABC123",
    "balance": 450.00,
    "currency": "ZAR",
    "last_updated": "2025-12-05T12:00:00Z"
  }
}
```

### 3. Withdraw Funds

**Endpoint:** `POST /api/wallet/{wallet_id}/withdraw`

**Used in:** Cashout Screen

**Request:**

```json
{
  "amount": 300,
  "description": "Cashout to card"
}
```

**Success Response:**

```json
{
  "success": true,
  "message": "Withdrawal successful",
  "data": {
    "new_balance": 150,
    "transaction": {
      "id": "tx-uuid",
      "amount": 300,
      "transaction_type": "withdrawal"
    }
  }
}
```

### 4. Get Transaction History

**Endpoint:** `GET /api/wallet/{wallet_id}/transactions?limit=50&offset=0`

**Used in:** Wallet Transaction List

**Response:**

```json
{
  "success": true,
  "message": "Transactions retrieved",
  "data": {
    "wallet_id": "uuid",
    "current_balance": 150,
    "total_transactions": 5,
    "transactions": [
      {
        "id": "uuid",
        "transaction_type": "deposit",
        "amount": 500,
        "currency": "ZAR",
        "reference": "TX-AB1234",
        "description": "Subscription weekly payment",
        "status": "completed"
      }
    ]
  }
}
```

**Wallet Creation Note:** Wallet is automatically created when KYC is approved by admin.

---

## Subscription Microservice

**Base Path:** `/api/subscriptions/*`

### 1. Get Available Packages

**Endpoint:** `GET /api/subscriptions/packages`

**Used in:** Subscription Selection Screen

**Response:**

```json
{
  "success": true,
  "message": "Subscription packages retrieved",
  "data": {
    "packages": [
      {
        "id": "uuid",
        "name": "On-The-Go",
        "price": 75,
        "period": "Weekly for 12 Months",
        "description": "Entry level Uber drivers",
        "benefits": ["Fuel Advance", "Emergency Service"],
        "weekly_advance_limit": 500,
        "advance_percentage": 20,
        "auto_repay_rate": 20
      }
    ]
  }
}
```

### 2. Activate Subscription

**Endpoint:** `POST /api/subscriptions/activate`

**Used in:** Plan Confirmation Screen

**Request:**

```json
{
  "user_id": "uuid",
  "package_id": "uuid"
}
```

**Success Response:**

```json
{
  "success": true,
  "message": "Subscription activated",
  "data": {
    "id": "sub-uuid",
    "user_id": "uuid",
    "package_id": "uuid",
    "is_active": true
  }
}
```

**Insufficient Funds Response:**

```json
{
  "success": false,
  "message": "Insufficient wallet balance"
}
```

### 3. Cancel Subscription

**Endpoint:** `POST /api/subscriptions/cancel`

**Used in:** Cancel Subscription Screen

**Request:**

```json
{
  "user_id": "uuid",
  "reason": "Too expensive"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Subscription cancelled"
}
```

### 4. Get Subscription Limits

**Endpoint:** `GET /api/subscriptions/limits/{user_id}`

**Used in:** Advance Screen, Dashboard

**Response:**

```json
{
  "success": true,
  "message": "Advance limits retrieved",
  "data": {
    "weekly_limit": 500,
    "used": 200,
    "available": 300,
    "outstanding_count": 1,
    "subscription_package": {
      "id": "uuid",
      "name": "On-The-Go",
      "weekly_advance_limit": 500
    }
  }
}
```

### 5. Cron Billing

**Endpoint:** `GET /api/subscriptions/cron/bill`

**Note:** Backend cronjob only - not called by frontend

---

## Workflow Diagrams

### Onboarding Flow

```
Signup → Email Verification → Login → Phone OTP → KYC Submission → Admin Approval → Wallet Creation → Subscription Activation
```

### Email Verification Flow

```
POST /api/auth/register → Email sent → User clicks link → GET /api/auth/verify-email → email_verified = true → Login allowed
```

### KYC Flow

```
User submits KYC → status = pending → Admin approves → Wallet created → User can subscribe
```

### Subscription Flow

```
User selects plan → Check wallet balance → POST /api/subscriptions/activate → Wallet debited → Benefits activated → Weekly billing begins
```

---

## Frontend Storage Requirements

After successful login, store in secure storage:

```json
{
  "token": "jwt-token",
  "user_id": "uuid",
  "email_verified": true,
  "phone_verified": false,
  "kyc_verified": false,
  "has_wallet": false,
  "has_subscription": false,
  "wallet_id": "uuid-or-null",
  "subscription_id": "uuid-or-null"
}
```

## Frontend Screen Navigation Logic

| Condition                     | Redirect To                 |
| ----------------------------- | --------------------------- |
| `email_verified == false`   | Email Verification Screen   |
| `phone_verified == false`   | Phone OTP Screen            |
| `kyc_verified == false`     | KYC Form Screen             |
| `has_wallet == false`       | Waiting for Approval Screen |
| `has_subscription == false` | Subscription Plans Screen   |
| All verified                  | Dashboard                   |

## Integration Notes

1. **Image Uploads:** Upload images to storage service first, then send URLs to KYC endpoint
2. **Token Management:** Store JWT securely and include in Authorization header for subsequent requests
3. **Error Handling:** Implement comprehensive error handling for network failures and API errors
4. **Loading States:** Show appropriate loading indicators during API calls
5. **Data Refresh:** Implement pull-to-refresh or periodic data refresh for wallet balance and transactions
6. **Offline Support:** Cache essential data and queue actions for when connectivity is restored

## Version Information

This documentation covers Sprint 1 implementation. Subsequent sprints will include Advances, Transactions, and Buying/Payment microservices.
