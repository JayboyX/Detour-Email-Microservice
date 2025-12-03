"""
KYC Service
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.shared.database import database_service
from app.email.service import email_service
from app.kyc.schemas import KYCStatus, BAVStatus

logger = logging.getLogger(__name__)

class KYCService:
    def __init__(self):
        self.supabase = database_service.supabase
    
    def submit_kyc(self, user_id: str, kyc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit KYC information"""
        try:
            kyc_record = {
                'user_id': user_id,
                **kyc_data,
                'kyc_status': 'pending',
                'bav_status': 'pending',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            endpoint = "/rest/v1/kyc_information"
            response = self.supabase.make_request(
                "POST", endpoint, kyc_record, self.supabase.service_headers
            )
            
            return {
                "success": True,
                "message": "KYC submitted successfully",
                "kyc_id": response[0]['id'] if response else None
            }
            
        except Exception as e:
            logger.error(f"Error submitting KYC: {e}")
            return {"success": False, "message": str(e)}
    
    def get_kyc_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get KYC information by user ID"""
        try:
            endpoint = f"/rest/v1/kyc_information?user_id=eq.{user_id}"
            response = self.supabase.make_request(
                "GET", endpoint, headers=self.supabase.anon_headers
            )
            return response[0] if response else None
        except Exception as e:
            logger.error(f"Error getting KYC: {e}")
            return None
    
    def get_all_kyc(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all KYC records (admin only)"""
        try:
            endpoint = "/rest/v1/kyc_information"
            if status:
                endpoint = f"/rest/v1/kyc_information?kyc_status=eq.{status}"
            
            response = self.supabase.make_request(
                "GET", endpoint, headers=self.supabase.service_headers
            )
            return response if response else []
        except Exception as e:
            logger.error(f"Error getting all KYC: {e}")
            return []
    
    def update_kyc_status(self, kyc_id: str, updates: Dict[str, Any]) -> bool:
        """Update KYC status (admin only)"""
        try:
            updates['updated_at'] = datetime.utcnow().isoformat()
            endpoint = f"/rest/v1/kyc_information?id=eq.{kyc_id}"
            
            response = self.supabase.make_request(
                "PATCH", endpoint, updates, self.supabase.service_headers
            )
            return bool(response)
        except Exception as e:
            logger.error(f"Error updating KYC status: {e}")
            return False
    
    def get_kyc_stats(self) -> Dict[str, Any]:
        """Get KYC statistics"""
        try:
            all_kyc = self.get_all_kyc()
            stats = {
                "total": len(all_kyc),
                "pending": sum(1 for k in all_kyc if k.get('kyc_status') == 'pending'),
                "verified": sum(1 for k in all_kyc if k.get('kyc_status') == 'verified'),
                "rejected": sum(1 for k in all_kyc if k.get('kyc_status') == 'rejected')
            }
            return stats
        except Exception as e:
            logger.error(f"Error getting KYC stats: {e}")
            return {"total": 0, "pending": 0, "verified": 0, "rejected": 0}

# Create instance
kyc_service = KYCService()