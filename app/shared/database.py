"""
Shared database service for all microservices
Combines supabase_client.py and database_service.py
"""
import requests
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from app.config import settings

logger = logging.getLogger(__name__)

# ============================================================
# SUPABASE CLIENT
# ============================================================
class SupabaseClient:
    def __init__(self):
        self.supabase_url = settings.supabase_url
        self.anon_key = settings.supabase_anon_key
        self.service_key = settings.supabase_service_role
        
        # Default anon headers
        self.anon_headers = {
            "Authorization": f"Bearer {self.anon_key}",
            "apikey": self.anon_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

        # Default service-role headers
        self.service_headers = {
            "Authorization": f"Bearer {self.service_key}",
            "apikey": self.service_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    # ------------------------------------------------------------
    # FIXED make_request() — NO MORE BROKEN GET REQUESTS
    # ------------------------------------------------------------
    def make_request(self, method, endpoint, data=None, headers=None):
        """
        Unified Supabase request wrapper.
        FIXED:
            - GET no longer pushes headers into query params
            - Headers remain headers
            - Query string must be included in endpoint, not data
        """
        url = f"{self.supabase_url}{endpoint}"

        try:
            if method == "GET":
                # IMPORTANT FIX: do NOT pass params=data
                response = requests.get(url, headers=headers)

            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)

            elif method == "PATCH":
                response = requests.patch(url, headers=headers, json=data)

            else:
                raise ValueError(f"Unsupported method: {method}")

            # Raise errors for any non-2xx status
            response.raise_for_status()

            # Return JSON safely
            return response.json() if response.content else {}

        except requests.exceptions.RequestException as e:
            logger.error(f"Supabase request failed: {e} | URL: {url}")
            raise


    # ============================================================
    # USER OPERATIONS
    # ============================================================
    def insert_user(self, user_data, use_service_key=True):
        endpoint = "/rest/v1/users"
        headers = self.service_headers if use_service_key else self.anon_headers
        return self.make_request("POST", endpoint, user_data, headers)


    def get_user_by_email(self, email, use_service_key=False):
        endpoint = f"/rest/v1/users?email=eq.{email}"
        headers = self.service_headers if use_service_key else self.anon_headers

        response = self.make_request("GET", endpoint, headers=headers)
        return response[0] if response else None


    def get_user_by_id(self, user_id, use_service_key=False):
        endpoint = f"/rest/v1/users?id=eq.{user_id}"
        headers = self.service_headers if use_service_key else self.anon_headers

        response = self.make_request("GET", endpoint, headers=headers)
        return response[0] if response else None


    def update_user(self, user_id, updates, use_service_key=True):
        endpoint = f"/rest/v1/users?id=eq.{user_id}"
        headers = self.service_headers if use_service_key else self.anon_headers

        return self.make_request("PATCH", endpoint, updates, headers)


    def check_email_exists(self, email, use_service_key=False):
        endpoint = f"/rest/v1/users?email=eq.{email}&select=id"
        headers = self.service_headers if use_service_key else self.anon_headers

        response = self.make_request("GET", endpoint, headers=headers)
        return len(response) > 0


# ============================================================
# DATABASE SERVICE LAYER
# ============================================================
class DatabaseService:
    def __init__(self, supabase_client: SupabaseClient):
        self.supabase = supabase_client

    # ------------------------------------------------------------
    # CREATE USER
    # ------------------------------------------------------------
    def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            from app.shared.auth import auth_service
            hashed_password = auth_service.get_password_hash(user_data['password'])

            user_record = {
                'id': str(uuid.uuid4()),
                'full_name': user_data['full_name'],
                'email': user_data['email'].lower(),
                'password_hash': hashed_password,
                'terms_agreed': user_data['terms_agreed'],
                'email_verified': False,
                'created_at': datetime.utcnow().isoformat()
            }

            if 'phone_number' in user_data and user_data['phone_number']:
                user_record['phone_number'] = user_data['phone_number']

            response = self.supabase.insert_user(user_record, use_service_key=True)

            return response[0] if response else None

        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    # ------------------------------------------------------------
    # GETTERS
    # ------------------------------------------------------------
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            return self.supabase.get_user_by_email(email, use_service_key=False)
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self.supabase.get_user_by_id(user_id, use_service_key=False)
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None

    # ------------------------------------------------------------
    # UPDATES
    # ------------------------------------------------------------
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        try:
            processed_updates = {}

            for key, value in updates.items():
                processed_updates[key] = (
                    value.isoformat() if isinstance(value, datetime) else value
                )

            response = self.supabase.update_user(
                user_id, processed_updates, use_service_key=True
            )
            return bool(response)

        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False

    def verify_email(self, user_id: str) -> bool:
        return self.update_user(
            user_id,
            {
                'email_verified': True,
                'verification_token': None,
                'token_expires_at': None
            }
        )

    def set_verification_token(self, user_id: str, token: str, expires_at: datetime) -> bool:
        return self.update_user(
            user_id,
            {
                'verification_token': token,
                'token_expires_at': expires_at.isoformat()
            }
        )

    def check_email_exists(self, email: str) -> bool:
        try:
            return self.supabase.check_email_exists(email, use_service_key=False)
        except Exception as e:
            logger.error(f"Error checking email existence: {e}")
            return False


# ============================================================
# Global instances
# ============================================================
supabase_client = SupabaseClient()
database_service = DatabaseService(supabase_client)
