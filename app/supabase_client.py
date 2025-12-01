# app/supabase_client.py - REPLACE WITH THIS
import requests
import json
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class SupabaseClient:
    def __init__(self):
        self.supabase_url = settings.supabase_url
        self.anon_key = settings.supabase_anon_key
        self.service_key = settings.supabase_service_role
        
        # Headers for different authentication levels
        self.anon_headers = {
            "Authorization": f"Bearer {self.anon_key}",
            "apikey": self.anon_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        self.service_headers = {
            "Authorization": f"Bearer {self.service_key}",
            "apikey": self.service_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        logger.info(f"Supabase HTTP client initialized for: {self.supabase_url}")
    
    def make_request(self, method, endpoint, data=None, headers=None):
        """Make HTTP request to Supabase"""
        url = f"{self.supabase_url}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=data)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data)
            elif method == "PATCH":
                response = requests.patch(url, headers=headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Supabase request failed: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            raise
    
    # User operations
    def insert_user(self, user_data, use_service_key=True):
        """Insert a new user"""
        endpoint = "/rest/v1/users"
        headers = self.service_headers if use_service_key else self.anon_headers
        return self.make_request("POST", endpoint, user_data, headers)
    
    def get_user_by_email(self, email, use_service_key=False):
        """Get user by email"""
        endpoint = "/rest/v1/users"
        params = {"email": f"eq.{email}"}
        headers = self.service_headers if use_service_key else self.anon_headers
        response = self.make_request("GET", endpoint, params, headers)
        return response[0] if response else None
    
    def get_user_by_id(self, user_id, use_service_key=False):
        """Get user by ID"""
        endpoint = f"/rest/v1/users?id=eq.{user_id}"
        headers = self.service_headers if use_service_key else self.anon_headers
        response = self.make_request("GET", endpoint, headers=headers)
        return response[0] if response else None
    
    def update_user(self, user_id, updates, use_service_key=True):
        """Update user fields"""
        endpoint = f"/rest/v1/users?id=eq.{user_id}"
        headers = self.service_headers if use_service_key else self.anon_headers
        return self.make_request("PATCH", endpoint, updates, headers)
    
    def check_email_exists(self, email, use_service_key=False):
        """Check if email exists"""
        endpoint = "/rest/v1/users"
        params = {"email": f"eq.{email}", "select": "id"}
        headers = self.service_headers if use_service_key else self.anon_headers
        response = self.make_request("GET", endpoint, params, headers)
        return len(response) > 0

# Create global instance
supabase_client = SupabaseClient()

def get_supabase():
    """Dependency for FastAPI to get Supabase client"""
    return supabase_client

def get_supabase_service():
    """Dependency for FastAPI to get Supabase service client"""
    return supabase_client