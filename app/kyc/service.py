"""
KYC Service
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.shared.database import database_service
from app.kyc.schemas import KYCStatus, BAVStatus

logger = logging.getLogger(__name__)


class KYCService:
    def __init__(self):
        self.supabase = database_service.supabase

    # ---------------------------------------------------------
    # Create / Submit KYC
    # ---------------------------------------------------------
    def submit_kyc(self, user_id: str, kyc_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            record = {
                "user_id": user_id,
                **kyc_data,
                "kyc_status": KYCStatus.PENDING.value,
                "bav_status": BAVStatus.PENDING.value,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = self.supabase.make_request(
                "POST",
                "/rest/v1/kyc_information",
                record,
                self.supabase.service_headers,
            )

            return {
                "success": True,
                "message": "KYC submitted successfully",
                "kyc_id": response[0]["id"] if response else None,
            }

        except Exception as e:
            logger.error(f"Submit KYC error: {e}")
            return {"success": False, "message": str(e)}

    # ---------------------------------------------------------
    # Get KYC Record
    # ---------------------------------------------------------
    def get_kyc_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            endpoint = f"/rest/v1/kyc_information?user_id=eq.{user_id}"
            response = self.supabase.make_request(
                "GET", endpoint, headers=self.supabase.anon_headers
            )
            return response[0] if response else None
        except Exception as e:
            logger.error(f"Get KYC error: {e}")
            return None

    # ---------------------------------------------------------
    # Admin: Get All
    # ---------------------------------------------------------
    def get_all_kyc(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            endpoint = "/rest/v1/kyc_information"
            if status:
                endpoint = f"{endpoint}?kyc_status=eq.{status}"

            response = self.supabase.make_request(
                "GET", endpoint, headers=self.supabase.service_headers
            )
            return response or []
        except Exception as e:
            logger.error(f"Get all KYC error: {e}")
            return []

    # ---------------------------------------------------------
    # Admin: Update
    # ---------------------------------------------------------
    def update_kyc_status(self, kyc_id: str, updates: Dict[str, Any]) -> bool:
        try:
            updates["updated_at"] = datetime.utcnow().isoformat()

            endpoint = f"/rest/v1/kyc_information?id=eq.{kyc_id}"
            response = self.supabase.make_request(
                "PATCH", endpoint, updates, self.supabase.service_headers
            )
            return bool(response)
        except Exception as e:
            logger.error(f"Update KYC error: {e}")
            return False

    # ---------------------------------------------------------
    # Admin: Stats
    # ---------------------------------------------------------
    def get_kyc_stats(self) -> Dict[str, Any]:
        try:
            all_kyc = self.get_all_kyc()
            return {
                "total": len(all_kyc),
                "pending": sum(1 for k in all_kyc if k.get("kyc_status") == "pending"),
                "verified": sum(1 for k in all_kyc if k.get("kyc_status") == "verified"),
                "rejected": sum(1 for k in all_kyc if k.get("kyc_status") == "rejected"),
            }
        except Exception as e:
            logger.error(f"KYC stats error: {e}")
            return {"total": 0, "pending": 0, "verified": 0, "rejected": 0}


kyc_service = KYCService()
