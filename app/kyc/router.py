"""KYC microservice router"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional
from app.kyc.service import kyc_service
from app.auth.schemas import SuccessResponse
from app.kyc.schemas import KYCSubmitRequest, KYCListResponse, KYCVerifyRequest, KYCStatus
from app.kyc.admin_auth import verify_admin_token
from app.shared.database import database_service
from app.email.service import email_service
from app.wallet.service import wallet_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["kyc"])

# User endpoints
@router.post("/submit", response_model=SuccessResponse)
async def submit_kyc(
    user_id: str,
    kyc_data: KYCSubmitRequest,
    background_tasks: BackgroundTasks
):
    """Submit KYC information"""
    result = kyc_service.submit_kyc(user_id, kyc_data.dict())
    if result["success"]:
        return SuccessResponse(
            success=True,
            message=result["message"],
            data={"kyc_id": result.get("kyc_id")}
        )
    return SuccessResponse(success=False, message=result["message"])

@router.get("/status/{user_id}", response_model=SuccessResponse)
async def get_kyc_status(user_id: str):
    """Get KYC status for user"""
    kyc = kyc_service.get_kyc_by_user_id(user_id)
    if not kyc:
        return SuccessResponse(success=False, message="KYC not found")
    
    return SuccessResponse(
        success=True,
        message="KYC status retrieved",
        data=kyc
    )

# Admin endpoints (protected)
@router.get("/admin/list", response_model=KYCListResponse)
async def list_all_kyc(
    status: Optional[str] = None,
    admin_id: str = Depends(verify_admin_token)
):
    """List all KYC records (admin only)"""
    kycs = kyc_service.get_all_kyc(status)
    stats = kyc_service.get_kyc_stats()
    
    return KYCListResponse(
        total=stats["total"],
        pending=stats["pending"],
        verified=stats["verified"],
        rejected=stats["rejected"],
        kycs=kycs
    )

@router.get("/admin/details/{kyc_id}", response_model=SuccessResponse)
async def get_kyc_details(
    kyc_id: str,
    admin_id: str = Depends(verify_admin_token)
):
    """Get detailed KYC information (admin only)"""
    try:
        endpoint = f"/rest/v1/kyc_information?id=eq.{kyc_id}"
        response = database_service.supabase.make_request(
            "GET", endpoint, headers=database_service.supabase.service_headers
        )
        
        if not response:
            return SuccessResponse(success=False, message="KYC not found")
        
        # Get user details
        kyc = response[0]
        user = database_service.get_user_by_id(kyc['user_id'])
        
        return SuccessResponse(
            success=True,
            message="KYC details retrieved",
            data={
                "kyc": kyc,
                "user": user
            }
        )
    except Exception as e:
        return SuccessResponse(success=False, message=str(e))

@router.post("/admin/verify", response_model=SuccessResponse)
async def verify_kyc(
    request: KYCVerifyRequest,
    background_tasks: BackgroundTasks,
    admin_id: str = Depends(verify_admin_token)
):
    """Verify KYC and create wallet (admin only)"""
    try:
        # Update KYC status
        updates = {
            'kyc_status': request.kyc_status.value,
            'bav_status': request.bav_status.value,
            'admin_notes': request.admin_notes
        }
        
        success = kyc_service.update_kyc_status(request.kyc_id, updates)
        if not success:
            return SuccessResponse(success=False, message="Failed to update KYC")
        
        # If verified, create wallet and send welcome email
        if request.kyc_status == KYCStatus.VERIFIED:
            # Get KYC info
            kyc = kyc_service.get_kyc_by_user_id(
                request.kyc_id.split('_')[0]  # Extract user_id from kyc_id
            )
            
            if kyc:
                user_id = kyc['user_id']
                user = database_service.get_user_by_id(user_id)
                
                # Create wallet
                wallet_result = wallet_service.create_wallet(user_id)
                
                # Send welcome email
                background_tasks.add_task(
                    send_welcome_email,
                    user['email'],
                    user['full_name'],
                    wallet_result.get('wallet_number', '')
                )
                
                # Log verification
                log_kyc_verification(admin_id, user_id, request.kyc_status.value)
        
        return SuccessResponse(
            success=True,
            message=f"KYC {request.kyc_status.value} successfully"
        )
        
    except Exception as e:
        return SuccessResponse(success=False, message=str(e))

def send_welcome_email(email: str, name: str, wallet_number: str):
    """Send welcome email with wallet information"""
    subject = "Welcome to Detour - Your Driver Wallet is Ready! 🚗"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #2AB576; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 30px; }}
            .wallet-box {{ background: #f8f9fa; border: 2px solid #2AB576; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            .button {{ background: #2AB576; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Welcome to Detour!</h1>
                <p>You're Now a Verified Driver</p>
            </div>
            <div class="content">
                <h2>Hi {name},</h2>
                <p>Congratulations! Your KYC verification has been <strong>approved</strong>.</p>
                
                <div class="wallet-box">
                    <h3>💰 Your Driver Wallet</h3>
                    <p><strong>Wallet Number:</strong> {wallet_number}</p>
                    <p><strong>Initial Balance:</strong> R 0.00</p>
                    <p><strong>Status:</strong> Active</p>
                </div>
                
                <p>You can now start earning as a Detour driver!</p>
                
                <h3>📱 Next Steps:</h3>
                <ul>
                    <li>Access your wallet from the Dashboard</li>
                    <li>Check available rides in your area</li>
                    <li>Start accepting ride requests</li>
                </ul>
                
                <p><strong>Want more benefits?</strong> Subscribe to premium features:</p>
                <a href="detourui://dashboard/subscription" class="button">View Subscription Plans</a>
                
                <p style="margin-top: 30px;">Happy driving! 🚗</p>
                <p><em>The Detour Team</em></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
    Welcome to Detour - Your Driver Wallet is Ready!
    
    Hi {name},
    
    Congratulations! Your KYC verification has been approved.
    
    Your Driver Wallet:
    - Wallet Number: {wallet_number}
    - Initial Balance: R 0.00
    - Status: Active
    
    You can now start earning as a Detour driver!
    
    Next Steps:
    1. Access your wallet from the Dashboard
    2. Check available rides in your area
    3. Start accepting ride requests
    
    Want more benefits? Subscribe to premium features.
    Go to Subscription in your dashboard.
    
    Happy driving!
    The Detour Team
    """
    
    email_service.send_custom_email(email, subject, html_body, text_body)
    email_service.send_wallet_welcome_email(email, name, wallet_number)

def log_kyc_verification(admin_id: str, user_id: str, status: str):
    """Log KYC verification for audit trail"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "admin_id": admin_id,
        "user_id": user_id,
        "action": f"kyc_{status}",
        "message": f"KYC {status} by admin {admin_id}"
    }
    
    try:
        with open('logs/kyc_audit.log', 'a') as f:
            import json
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        logger.error(f"Failed to log KYC verification: {e}")