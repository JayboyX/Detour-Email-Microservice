"""
Wallet Service for Detour Drivers
"""
import logging
import uuid
import random
import string
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.shared.database import database_service

logger = logging.getLogger(__name__)

class WalletService:
    def __init__(self):
        self.supabase = database_service.supabase
    
    def generate_wallet_number(self) -> str:
        """Generate unique wallet number: WLT-XXXXXX"""
        while True:
            random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            wallet_number = f"WLT-{random_chars}"
            
            # Check if unique
            existing = self.get_wallet_by_number(wallet_number)
            if not existing:
                return wallet_number
    
    def create_wallet(self, user_id: str) -> Dict[str, Any]:
        """Create a new wallet for user"""
        try:
            # Check if user already has a wallet
            existing_wallet = self.get_wallet_by_user_id(user_id)
            if existing_wallet:
                return {
                    "success": False,
                    "message": "User already has a wallet",
                    "wallet": existing_wallet
                }
            
            wallet_number = self.generate_wallet_number()
            wallet_data = {
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'wallet_number': wallet_number,
                'balance': 0.00,
                'currency': 'ZAR',
                'status': 'active',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            endpoint = "/rest/v1/wallets"
            response = self.supabase.make_request(
                "POST", endpoint, wallet_data, self.supabase.service_headers
            )
            
            if response:
                # Log wallet creation
                self.log_wallet_creation(user_id, wallet_number)
                
                # Create initial transaction record
                self.create_transaction(
                    wallet_id=response[0]['id'],
                    transaction_type='deposit',  # or 'payment' or 'refund'
                    amount=0.00,
                    description='Wallet account opened'
                )
                
                return {
                    "success": True,
                    "message": "Wallet created successfully",
                    "wallet": response[0]
                }
            else:
                return {"success": False, "message": "Failed to create wallet"}
                
        except Exception as e:
            logger.error(f"Error creating wallet: {e}")
            return {"success": False, "message": str(e)}
    
    def get_wallet_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get wallet by user ID"""
        try:
            endpoint = f"/rest/v1/wallets?user_id=eq.{user_id}"
            response = self.supabase.make_request(
                "GET", endpoint, headers=self.supabase.anon_headers
            )
            return response[0] if response else None
        except Exception as e:
            logger.error(f"Error getting wallet: {e}")
            return None
    
    def get_wallet_by_number(self, wallet_number: str) -> Optional[Dict[str, Any]]:
        """Get wallet by wallet number"""
        try:
            endpoint = f"/rest/v1/wallets?wallet_number=eq.{wallet_number}"
            response = self.supabase.make_request(
                "GET", endpoint, headers=self.supabase.anon_headers
            )
            return response[0] if response else None
        except Exception as e:
            logger.error(f"Error getting wallet by number: {e}")
            return None
    
    def get_wallet_by_id(self, wallet_id: str) -> Optional[Dict[str, Any]]:
        """Get wallet by ID"""
        try:
            endpoint = f"/rest/v1/wallets?id=eq.{wallet_id}"
            response = self.supabase.make_request(
                "GET", endpoint, headers=self.supabase.anon_headers
            )
            return response[0] if response else None
        except Exception as e:
            logger.error(f"Error getting wallet by ID: {e}")
            return None
    
    def update_wallet_balance(self, wallet_id: str, amount: float, transaction_type: str) -> Dict[str, Any]:
        """Update wallet balance with transaction"""
        try:
            wallet = self.get_wallet_by_id(wallet_id)
            if not wallet:
                return {"success": False, "message": "Wallet not found"}
            
            new_balance = float(wallet['balance']) + amount
            
            # Don't allow negative balance for non-credit transactions
            if new_balance < 0 and transaction_type not in ['credit', 'refund']:
                return {"success": False, "message": "Insufficient funds"}
            
            updates = {
                'balance': new_balance,
                'updated_at': datetime.utcnow().isoformat(),
                'last_transaction_at': datetime.utcnow().isoformat()
            }
            
            endpoint = f"/rest/v1/wallets?id=eq.{wallet_id}"
            response = self.supabase.make_request(
                "PATCH", endpoint, updates, self.supabase.service_headers
            )
            
            if response:
                return {
                    "success": True,
                    "message": "Balance updated",
                    "new_balance": new_balance,
                    "wallet": response[0]
                }
            else:
                return {"success": False, "message": "Failed to update balance"}
                
        except Exception as e:
            logger.error(f"Error updating balance: {e}")
            return {"success": False, "message": str(e)}
    
    def create_transaction(self, wallet_id: str, transaction_type: str, 
                          amount: float, description: str = "", 
                          reference: str = "", metadata: Dict = None) -> Dict[str, Any]:
        """Create a wallet transaction"""
        try:
            # Map transaction type to status
            status_mapping = {
                'deposit': 'completed',
                'withdrawal': 'pending',
                'transfer': 'pending',
                'payment': 'pending',
                'refund': 'completed',
                'account_opening': 'completed'
            }
            
            transaction_data = {
                'id': str(uuid.uuid4()),
                'wallet_id': wallet_id,
                'transaction_type': transaction_type,
                'amount': amount,
                'currency': 'ZAR',
                'reference': reference or f"TX-{str(uuid.uuid4())[:8].upper()}",
                'description': description,
                'status': status_mapping.get(transaction_type, 'pending'),
                'metadata': metadata or {},
                'created_at': datetime.utcnow().isoformat()
            }
            
            endpoint = "/rest/v1/wallet_transactions"
            response = self.supabase.make_request(
                "POST", endpoint, transaction_data, self.supabase.service_headers
            )
            
            if response:
                return {
                    "success": True,
                    "message": "Transaction created",
                    "transaction": response[0]
                }
            else:
                return {"success": False, "message": "Failed to create transaction"}
                
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            return {"success": False, "message": str(e)}
    
    def get_transactions(self, wallet_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get wallet transactions"""
        try:
            endpoint = f"/rest/v1/wallet_transactions?wallet_id=eq.{wallet_id}&order=created_at.desc&limit={limit}&offset={offset}"
            response = self.supabase.make_request(
                "GET", endpoint, headers=self.supabase.anon_headers
            )
            return response if response else []
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []
    
    def deposit_funds(self, wallet_id: str, amount: float, description: str = "") -> Dict[str, Any]:
        """Deposit funds into wallet"""
        try:
            if amount <= 0:
                return {"success": False, "message": "Amount must be positive"}
            
            # Update balance
            balance_result = self.update_wallet_balance(wallet_id, amount, 'deposit')
            if not balance_result["success"]:
                return balance_result
            
            # Create transaction
            transaction_result = self.create_transaction(
                wallet_id=wallet_id,
                transaction_type='deposit',
                amount=amount,
                description=description or f"Deposit: R {amount:.2f}"
            )
            
            return {
                "success": True,
                "message": "Deposit successful",
                "new_balance": balance_result["new_balance"],
                "transaction": transaction_result.get("transaction")
            }
            
        except Exception as e:
            logger.error(f"Error depositing funds: {e}")
            return {"success": False, "message": str(e)}
    
    def withdraw_funds(self, wallet_id: str, amount: float, description: str = "") -> Dict[str, Any]:
        """Withdraw funds from wallet"""
        try:
            if amount <= 0:
                return {"success": False, "message": "Amount must be positive"}
            
            # Update balance (negative amount for withdrawal)
            balance_result = self.update_wallet_balance(wallet_id, -amount, 'withdrawal')
            if not balance_result["success"]:
                return balance_result
            
            # Create transaction
            transaction_result = self.create_transaction(
                wallet_id=wallet_id,
                transaction_type='withdrawal',
                amount=amount,
                description=description or f"Withdrawal: R {amount:.2f}"
            )
            
            return {
                "success": True,
                "message": "Withdrawal successful",
                "new_balance": balance_result["new_balance"],
                "transaction": transaction_result.get("transaction")
            }
            
        except Exception as e:
            logger.error(f"Error withdrawing funds: {e}")
            return {"success": False, "message": str(e)}
    
    def log_wallet_creation(self, user_id: str, wallet_number: str):
        """Log wallet creation for audit trail"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "wallet_number": wallet_number,
            "event": "wallet_created"
        }
        
        try:
            with open('logs/wallet_creation.log', 'a') as f:
                import json
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to log wallet creation: {e}")

# Create instance
wallet_service = WalletService()