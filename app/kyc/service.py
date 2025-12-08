"""
KYC Service — Full Auto-Mode
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
        """
        Creates a new KYC record with:
            kyc_status = pending
            bav_status = pending
        Cron will auto-verify both fields.
        """

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
            logger.error(f"[KYC] Submit error: {e}")
            return {"success": False, "message": "Failed to submit KYC"}

    # ---------------------------------------------------------
    # Get KYC by user ID
    # ---------------------------------------------------------
    def get_kyc_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.supabase.make_request(
                "GET",
                f"/rest/v1/kyc_information?user_id=eq.{user_id}",
                self.supabase.anon_headers,
            )
            return response[0] if response else None

        except Exception as e:
            logger.error(f"[KYC] Load error user {user_id}: {e}")
            return None

    # ---------------------------------------------------------
    # Get KYC by KYC ID
    # ---------------------------------------------------------
    def get_kyc_by_id(self, kyc_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.supabase.make_request(
                "GET",
                f"/rest/v1/kyc_information?id=eq.{kyc_id}",
                self.supabase.service_headers,
            )
            return response[0] if response else None

        except Exception as e:
            logger.error(f"[KYC] Load error kyc_id {kyc_id}: {e}")
            return None

    # ---------------------------------------------------------
    # Get All KYC Records (Admin)
    # ---------------------------------------------------------
    def get_all_kyc(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            endpoint = "/rest/v1/kyc_information"
            if status:
                endpoint += f"?kyc_status=eq.{status}"

            response = self.supabase.make_request(
                "GET",
                endpoint,
                self.supabase.service_headers,
            )

            return response or []

        except Exception as e:
            logger.error(f"[KYC] Get all error: {e}")
            return []

    # ---------------------------------------------------------
    # Update KYC Record (used by admin OR cron)
    # ---------------------------------------------------------
    def update_kyc_status(self, kyc_id: str, updates: Dict[str, Any]) -> bool:
        """
        Updates KYC fields such as:
            kyc_status
            bav_status
            admin_notes
        """

        try:
            updates["updated_at"] = datetime.utcnow().isoformat()

            response = self.supabase.make_request(
                "PATCH",
                f"/rest/v1/kyc_information?id=eq.{kyc_id}",
                updates,
                self.supabase.service_headers,
            )

            return bool(response)

        except Exception as e:
            logger.error(f"[KYC] Update error kyc_id {kyc_id}: {e}")
            return False

    # ---------------------------------------------------------
    # KYC Stats for Admin Dashboard
    # ---------------------------------------------------------
    def get_kyc_stats(self) -> Dict[str, Any]:
        try:
            all_records = self.get_all_kyc()

            return {
                "total": len(all_records),
                "pending": sum(1 for k in all_records if k["kyc_status"] == "pending"),
                "verified": sum(1 for k in all_records if k["kyc_status"] == "verified"),
                "rejected": sum(1 for k in all_records if k["kyc_status"] == "rejected"),
            }

        except Exception as e:
            logger.error(f"[KYC] Stats error: {e}")
            return {"total": 0, "pending": 0, "verified": 0, "rejected": 0}

    # ---------------------------------------------------------
    # AUTO MODE FETCH — USED BY CRON EVERY 2 MINUTES
    # ---------------------------------------------------------
    def get_pending_for_auto_verify(self) -> List[Dict[str, Any]]:
        """
        AUTO-MODE:
        - Fetch ALL pending KYC records
        - Ignore BAV completely (auto-set to verified)
        """

        try:
            response = self.supabase.make_request(
                "GET",
                "/rest/v1/kyc_information?kyc_status=eq.pending",
                self.supabase.service_headers,
            )

            return response or []

        except Exception as e:
            logger.error(f"[KYC] Auto verify fetch error: {e}")
            return []


kyc_service = KYCService()
