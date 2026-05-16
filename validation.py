"""
Data validation and quality checks for the banking pipeline.
"""

from typing import Dict, List, Any, Tuple
from decimal import Decimal
import re

from logger import get_logger

logger = get_logger("validation")


class DataValidator:
    """Validates banking data."""
    
    # Email pattern
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    # Valid transaction types
    VALID_TXN_TYPES = {"DEPOSIT", "WITHDRAWAL", "TRANSFER"}
    VALID_TXN_STATUS = {"PENDING", "COMPLETED", "FAILED", "REVERSED"}
    VALID_ACCOUNT_TYPES = {"SAVINGS", "CHECKING", "MONEY_MARKET", "CREDIT"}
    VALID_CURRENCIES = {"USD", "EUR", "GBP", "CAD", "AUD"}
    
    @staticmethod
    def validate_customer(customer_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate customer data."""
        errors = []
        
        # Check required fields
        if not customer_data.get('first_name'):
            errors.append("first_name is required and cannot be empty")
        if not customer_data.get('last_name'):
            errors.append("last_name is required and cannot be empty")
        
        email = customer_data.get('email', '').strip()
        if not email:
            errors.append("email is required and cannot be empty")
        elif not DataValidator.EMAIL_PATTERN.match(email):
            errors.append(f"Invalid email format: {email}")
        
        # Validate name length
        if customer_data.get('first_name') and len(customer_data['first_name']) > 100:
            errors.append("first_name cannot exceed 100 characters")
        if customer_data.get('last_name') and len(customer_data['last_name']) > 100:
            errors.append("last_name cannot exceed 100 characters")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_account(account_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate account data."""
        errors = []
        
        # Check required fields
        if 'customer_id' not in account_data or not account_data['customer_id']:
            errors.append("customer_id is required")
        elif not isinstance(account_data['customer_id'], int) or account_data['customer_id'] <= 0:
            errors.append("customer_id must be a positive integer")
        
        account_type = account_data.get('account_type', '').upper()
        if not account_type:
            errors.append("account_type is required")
        elif account_type not in DataValidator.VALID_ACCOUNT_TYPES:
            errors.append(f"Invalid account_type. Must be one of: {DataValidator.VALID_ACCOUNT_TYPES}")
        
        # Validate balance
        try:
            balance = Decimal(str(account_data.get('balance', 0)))
            if balance < 0:
                errors.append("balance cannot be negative")
        except (ValueError, TypeError):
            errors.append("balance must be a valid decimal number")
        
        # Validate currency
        currency = account_data.get('currency', 'USD').upper()
        if currency not in DataValidator.VALID_CURRENCIES:
            errors.append(f"Invalid currency. Must be one of: {DataValidator.VALID_CURRENCIES}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_transaction(transaction_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate transaction data."""
        errors = []
        
        # Check required fields
        if 'account_id' not in transaction_data or not transaction_data['account_id']:
            errors.append("account_id is required")
        elif not isinstance(transaction_data['account_id'], int) or transaction_data['account_id'] <= 0:
            errors.append("account_id must be a positive integer")
        
        txn_type = transaction_data.get('txn_type', '').upper()
        if not txn_type:
            errors.append("txn_type is required")
        elif txn_type not in DataValidator.VALID_TXN_TYPES:
            errors.append(f"Invalid txn_type. Must be one of: {DataValidator.VALID_TXN_TYPES}")
        
        # Validate amount
        try:
            amount = Decimal(str(transaction_data.get('amount', 0)))
            if amount <= 0:
                errors.append("amount must be greater than 0")
            if amount > Decimal('999999999.99'):
                errors.append("amount exceeds maximum allowed value")
        except (ValueError, TypeError):
            errors.append("amount must be a valid decimal number")
        
        # Validate status
        status = transaction_data.get('status', 'COMPLETED').upper()
        if status not in DataValidator.VALID_TXN_STATUS:
            errors.append(f"Invalid status. Must be one of: {DataValidator.VALID_TXN_STATUS}")
        
        # Validate transfer
        if txn_type == "TRANSFER":
            if not transaction_data.get('related_account_id'):
                errors.append("TRANSFER transaction requires related_account_id")
        
        return len(errors) == 0, errors


class DataQualityChecker:
    """Performs data quality checks on streaming data."""
    
    def __init__(self):
        self.valid_records = 0
        self.invalid_records = 0
        self.quality_issues = []
    
    def check_record(self, record_type: str, record_data: Dict[str, Any]) -> bool:
        """Check a record for quality issues."""
        try:
            if record_type == "customer":
                is_valid, errors = DataValidator.validate_customer(record_data)
            elif record_type == "account":
                is_valid, errors = DataValidator.validate_account(record_data)
            elif record_type == "transaction":
                is_valid, errors = DataValidator.validate_transaction(record_data)
            else:
                logger.warning(f"Unknown record type: {record_type}")
                return False
            
            if is_valid:
                self.valid_records += 1
            else:
                self.invalid_records += 1
                self.quality_issues.append({
                    "type": record_type,
                    "data": record_data,
                    "errors": errors
                })
                logger.warning(f"Invalid {record_type}: {errors}")
            
            return is_valid
        
        except Exception as e:
            logger.error(f"Error checking {record_type}: {e}")
            self.invalid_records += 1
            return False
    
    def get_quality_report(self) -> Dict[str, Any]:
        """Get data quality report."""
        total = self.valid_records + self.invalid_records
        quality_score = (
            (self.valid_records / total * 100) if total > 0 else 0
        )
        
        return {
            "total_records": total,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "quality_score_percent": round(quality_score, 2),
            "issues": self.quality_issues[-100:] if len(self.quality_issues) > 100 else self.quality_issues
        }
    
    def reset(self):
        """Reset quality checker state."""
        self.valid_records = 0
        self.invalid_records = 0
        self.quality_issues = []


# Global quality checker
quality_checker = DataQualityChecker()
