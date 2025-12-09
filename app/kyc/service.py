"""
KYC Service — Full Auto-Mode + Admin Revoke Support
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
            logger.error(f"[KYC] Submit error: {e}")
            return {"success": False, "message": "Failed to submit KYC"}

    # ---------------------------------------------------------
    # Getters
    # ---------------------------------------------------------
    def get_kyc_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.supabase.make_request(
                "GET",
                f"/rest/v1/kyc_information?user_id=eq.{user_id}",
                self.supabase.anon_headers,  # CHANGED: Use anon_headers for public access
            )
            return response[0] if response else None
        except Exception as e:
            logger.error(f"[KYC] Load error user {user_id}: {e}")
            return None

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
    # Update KYC Record
    # ---------------------------------------------------------
    def update_kyc_status(self, kyc_id: str, updates: Dict[str, Any]) -> bool:
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
    # Admin Revoke KYC — MAIN NEW SERVICE METHOD
    # ---------------------------------------------------------
    def revoke(self, kyc_id: str, reason: str) -> Dict[str, Any]:
        """
        Perform a full KYC revocation. This is called by the router.
        Steps:
            - KYC → rejected
            - BAV → failed
            - User → is_kyc_verified = false
            - Wallet → suspended
        """

        try:
            # 1️⃣ Load KYC record
            kyc_record = self.get_kyc_by_id(kyc_id)
            if not kyc_record:
                return {"success": False, "message": "KYC record not found"}

            user_id = kyc_record["user_id"]

            # 2️⃣ Update KYC fields
            updated = self.update_kyc_status(
                kyc_id,
                {
                    "kyc_status": KYCStatus.REJECTED.value,
                    "bav_status": BAVStatus.FAILED.value,
                    "admin_notes": reason,
                },
            )

            if not updated:
                return {"success": False, "message": "Failed updating KYC record"}

            # 3️⃣ Revoke user verification
            self.supabase.make_request(
                "PATCH",
                f"/rest/v1/users?id=eq.{user_id}",
                {"is_kyc_verified": False},
                self.supabase.service_headers,
            )

            # 4️⃣ Suspend wallet (if exists)
            wallet_data = self.supabase.make_request(
                "GET",
                f"/rest/v1/wallets?user_id=eq.{user_id}",
                self.supabase.service_headers,
            )

            if wallet_data:
                wallet_id = wallet_data[0]["id"]

                self.supabase.make_request(
                    "PATCH",
                    f"/rest/v1/wallets?id=eq.{wallet_id}",
                    {"status": "suspended"},
                    self.supabase.service_headers,
                )

            return {
                "success": True,
                "message": "KYC revoked successfully",
                "user_id": user_id,
            }

        except Exception as e:
            logger.error(f"[KYC] Revoke error: {e}")
            return {"success": False, "message": str(e)}

    # ---------------------------------------------------------
    # KYC Stats
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
    # AUTO VERIFY USED BY CRON EVERY 2 MINUTES
    # ---------------------------------------------------------
    def get_pending_for_auto_verify(self) -> List[Dict[str, Any]]:
        try:
            response = self.supabase.make_request(
                "GET",
                "/rest/v1/kyc_information?kyc_status=eq.pending",
                self.supabase.anon_headers,  # CHANGED: Use anon_headers for cron access
            )
            return response or []
        except Exception as e:
            logger.error(f"[KYC] Auto verify fetch error: {e}")
            return []


kyc_service = KYCService()