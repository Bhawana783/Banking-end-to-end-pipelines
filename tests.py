"""
Unit tests for the banking data pipeline
"""

import unittest
import sys
import os
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validation import DataValidator, DataQualityChecker
from config import (
    postgres_config, kafka_config, data_generator_config
)


class TestDataValidator(unittest.TestCase):
    """Test data validation logic."""
    
    def test_valid_customer(self):
        """Test valid customer data."""
        customer = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com'
        }
        is_valid, errors = DataValidator.validate_customer(customer)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_invalid_customer_missing_fields(self):
        """Test customer with missing fields."""
        customer = {
            'first_name': 'John',
            'last_name': 'Doe'
        }
        is_valid, errors = DataValidator.validate_customer(customer)
        self.assertFalse(is_valid)
        self.assertTrue(any('email' in error for error in errors))
    
    def test_invalid_customer_bad_email(self):
        """Test customer with invalid email."""
        customer = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'invalid-email'
        }
        is_valid, errors = DataValidator.validate_customer(customer)
        self.assertFalse(is_valid)
        self.assertTrue(any('email' in error.lower() for error in errors))
    
    def test_valid_account(self):
        """Test valid account data."""
        account = {
            'customer_id': 1,
            'account_type': 'SAVINGS',
            'balance': 1000.00,
            'currency': 'USD'
        }
        is_valid, errors = DataValidator.validate_account(account)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_invalid_account_negative_balance(self):
        """Test account with negative balance."""
        account = {
            'customer_id': 1,
            'account_type': 'SAVINGS',
            'balance': -100.00,
            'currency': 'USD'
        }
        is_valid, errors = DataValidator.validate_account(account)
        self.assertFalse(is_valid)
        self.assertTrue(any('negative' in error.lower() for error in errors))
    
    def test_invalid_account_type(self):
        """Test account with invalid type."""
        account = {
            'customer_id': 1,
            'account_type': 'INVALID_TYPE',
            'balance': 1000.00,
            'currency': 'USD'
        }
        is_valid, errors = DataValidator.validate_account(account)
        self.assertFalse(is_valid)
        self.assertTrue(any('account_type' in error.lower() for error in errors))
    
    def test_valid_transaction(self):
        """Test valid transaction data."""
        transaction = {
            'account_id': 1,
            'txn_type': 'DEPOSIT',
            'amount': 500.00,
            'status': 'COMPLETED'
        }
        is_valid, errors = DataValidator.validate_transaction(transaction)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_invalid_transaction_zero_amount(self):
        """Test transaction with zero amount."""
        transaction = {
            'account_id': 1,
            'txn_type': 'DEPOSIT',
            'amount': 0,
            'status': 'COMPLETED'
        }
        is_valid, errors = DataValidator.validate_transaction(transaction)
        self.assertFalse(is_valid)
        self.assertTrue(any('amount' in error.lower() for error in errors))
    
    def test_invalid_transfer_missing_related(self):
        """Test transfer without related account."""
        transaction = {
            'account_id': 1,
            'txn_type': 'TRANSFER',
            'amount': 100.00,
            'status': 'COMPLETED'
        }
        is_valid, errors = DataValidator.validate_transaction(transaction)
        self.assertFalse(is_valid)
        self.assertTrue(any('related_account' in error.lower() for error in errors))


class TestDataQualityChecker(unittest.TestCase):
    """Test data quality checking."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.checker = DataQualityChecker()
    
    def test_check_valid_record(self):
        """Test checking a valid record."""
        customer = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane@example.com'
        }
        result = self.checker.check_record("customer", customer)
        self.assertTrue(result)
        self.assertEqual(self.checker.valid_records, 1)
        self.assertEqual(self.checker.invalid_records, 0)
    
    def test_check_invalid_record(self):
        """Test checking an invalid record."""
        customer = {
            'first_name': 'Jane',
            'last_name': 'Smith'
            # Missing email
        }
        result = self.checker.check_record("customer", customer)
        self.assertFalse(result)
        self.assertEqual(self.checker.valid_records, 0)
        self.assertEqual(self.checker.invalid_records, 1)
    
    def test_quality_report(self):
        """Test quality report generation."""
        self.checker.valid_records = 90
        self.checker.invalid_records = 10
        
        report = self.checker.get_quality_report()
        
        self.assertEqual(report['total_records'], 100)
        self.assertEqual(report['valid_records'], 90)
        self.assertEqual(report['invalid_records'], 10)
        self.assertEqual(report['quality_score_percent'], 90.0)


class TestConfiguration(unittest.TestCase):
    """Test configuration loading."""
    
    def test_postgres_config_defaults(self):
        """Test PostgreSQL config defaults."""
        self.assertEqual(postgres_config.HOST, "postgres")
        self.assertEqual(postgres_config.PORT, 5432)
        self.assertEqual(postgres_config.DB, "banking")
    
    def test_kafka_config_defaults(self):
        """Test Kafka config defaults."""
        self.assertEqual(kafka_config.GROUP_ID, "banking-consumer-group")
        self.assertEqual(len(kafka_config.TOPICS), 3)
    
    def test_data_generator_config_defaults(self):
        """Test data generator config defaults."""
        self.assertGreater(data_generator_config.NUM_CUSTOMERS, 0)
        self.assertGreater(data_generator_config.ACCOUNTS_PER_CUSTOMER, 0)
        self.assertGreater(data_generator_config.TRANSACTIONS_PER_ITERATION, 0)
    
    def test_postgres_dsn(self):
        """Test PostgreSQL DSN generation."""
        dsn = postgres_config.get_dsn()
        self.assertIn("postgresql://", dsn)
        self.assertIn(postgres_config.HOST, dsn)
        self.assertIn(postgres_config.DB, dsn)


class TestDataGenerator(unittest.TestCase):
    """Test data generator logic."""
    
    def test_random_money_range(self):
        """Test random money generation is within range."""
        from data_generator.faker_generator import BankingDataGenerator
        
        for _ in range(100):
            amount = BankingDataGenerator.random_money(10.0, 100.0)
            self.assertGreaterEqual(amount, Decimal('10.00'))
            self.assertLessEqual(amount, Decimal('100.00'))
            # Check decimal places
            self.assertEqual(amount.as_tuple().exponent, -2)


if __name__ == "__main__":
    unittest.main()
