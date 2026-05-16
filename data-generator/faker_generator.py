"""
Banking Data Generator - Generates realistic banking data using Faker
Supports continuous generation or single run mode
"""

import time
import sys
import os
import argparse
from decimal import Decimal, ROUND_DOWN
from faker import Faker
import random

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import data_generator_config, postgres_config
from database import DatabaseConnectionPool, get_db_cursor, DatabaseInitializer
from validation import DataValidator, quality_checker
from logger import get_logger, LogContext

logger = get_logger("data_generator")
fake = Faker()


class BankingDataGenerator:
    """Generates realistic banking data."""
    
    ACCOUNT_TYPES = ["SAVINGS", "CHECKING", "MONEY_MARKET", "CREDIT"]
    TRANSACTION_TYPES = ["DEPOSIT", "WITHDRAWAL", "TRANSFER"]
    
    def __init__(self):
        self.iteration = 0
        self.total_customers = 0
        self.total_accounts = 0
        self.total_transactions = 0
        DatabaseConnectionPool.initialize()
    
    @staticmethod
    def random_money(min_val: float, max_val: float) -> Decimal:
        """Generate random money amount."""
        val = Decimal(str(random.uniform(min_val, max_val)))
        return val.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    
    @staticmethod
    def random_phone() -> str:
        """Generate random phone number."""
        return fake.phone_number()[:15]
    
    @staticmethod
    def random_address() -> str:
        """Generate random address."""
        return fake.address()[:255]
    
    def generate_customers(self, count: int) -> list:
        """Generate customer records."""
        customers = []
        try:
            with get_db_cursor() as cursor:
                for _ in range(count):
                    first_name = fake.first_name()
                    last_name = fake.last_name()
                    email = fake.unique.email()
                    
                    customer_data = {
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': email
                    }
                    
                    # Validate before insertion
                    is_valid, errors = DataValidator.validate_customer(customer_data)
                    if not is_valid:
                        logger.warning(f"Invalid customer data: {errors}")
                        quality_checker.check_record("customer", customer_data)
                        continue
                    
                    try:
                        cursor.execute(
                            "INSERT INTO customers (first_name, last_name, email) "
                            "VALUES (%s, %s, %s) RETURNING id",
                            (first_name, last_name, email),
                        )
                        customer_id = cursor.fetchone()[0]
                        customers.append(customer_id)
                        quality_checker.valid_records += 1
                    except Exception as e:
                        if "unique constraint" in str(e).lower():
                            logger.debug(f"Duplicate email: {email}")
                        else:
                            logger.error(f"Error inserting customer: {e}")
        
        except Exception as e:
            logger.error(f"Error generating customers: {e}")
        
        return customers
    
    def generate_accounts(self, customers: list) -> list:
        """Generate account records."""
        accounts = []
        try:
            with get_db_cursor() as cursor:
                for customer_id in customers:
                    for _ in range(data_generator_config.ACCOUNTS_PER_CUSTOMER):
                        account_type = random.choice(self.ACCOUNT_TYPES)
                        initial_balance = self.random_money(
                            data_generator_config.MIN_INITIAL_BALANCE,
                            data_generator_config.MAX_INITIAL_BALANCE
                        )
                        
                        account_data = {
                            'customer_id': customer_id,
                            'account_type': account_type,
                            'balance': float(initial_balance),
                            'currency': data_generator_config.CURRENCY
                        }
                        
                        # Validate before insertion
                        is_valid, errors = DataValidator.validate_account(account_data)
                        if not is_valid:
                            logger.warning(f"Invalid account data: {errors}")
                            quality_checker.check_record("account", account_data)
                            continue
                        
                        try:
                            cursor.execute(
                                "INSERT INTO accounts (customer_id, account_type, balance, currency) "
                                "VALUES (%s, %s, %s, %s) RETURNING id",
                                (customer_id, account_type, initial_balance, data_generator_config.CURRENCY),
                            )
                            account_id = cursor.fetchone()[0]
                            accounts.append(account_id)
                            quality_checker.valid_records += 1
                        except Exception as e:
                            logger.error(f"Error inserting account: {e}")
        
        except Exception as e:
            logger.error(f"Error generating accounts: {e}")
        
        return accounts
    
    def generate_transactions(self, accounts: list) -> int:
        """Generate transaction records."""
        count = 0
        try:
            with get_db_cursor() as cursor:
                for _ in range(data_generator_config.TRANSACTIONS_PER_ITERATION):
                    account_id = random.choice(accounts)
                    txn_type = random.choice(self.TRANSACTION_TYPES)
                    amount = self.random_money(
                        data_generator_config.MIN_TRANSACTION_AMOUNT,
                        data_generator_config.MAX_TRANSACTION_AMOUNT
                    )
                    related_account = None
                    
                    if txn_type == "TRANSFER" and len(accounts) > 1:
                        related_account = random.choice([a for a in accounts if a != account_id])
                    
                    transaction_data = {
                        'account_id': account_id,
                        'txn_type': txn_type,
                        'amount': float(amount),
                        'related_account_id': related_account,
                        'status': 'COMPLETED'
                    }
                    
                    # Validate before insertion
                    is_valid, errors = DataValidator.validate_transaction(transaction_data)
                    if not is_valid:
                        logger.warning(f"Invalid transaction data: {errors}")
                        quality_checker.check_record("transaction", transaction_data)
                        continue
                    
                    try:
                        cursor.execute(
                            "INSERT INTO transactions (account_id, txn_type, amount, related_account_id, status) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            (account_id, txn_type, amount, related_account, 'COMPLETED'),
                        )
                        count += 1
                        quality_checker.valid_records += 1
                    except Exception as e:
                        logger.error(f"Error inserting transaction: {e}")
        
        except Exception as e:
            logger.error(f"Error generating transactions: {e}")
        
        return count
    
    def run_iteration(self):
        """Run one generation iteration."""
        self.iteration += 1
        
        with LogContext(logger, "Data Generation Iteration", iteration=self.iteration):
            try:
                # Generate customers
                customers = self.generate_customers(data_generator_config.NUM_CUSTOMERS)
                self.total_customers += len(customers)
                
                # Generate accounts
                accounts = self.generate_accounts(customers)
                self.total_accounts += len(accounts)
                
                # Generate transactions
                txn_count = self.generate_transactions(accounts)
                self.total_transactions += txn_count
                
                logger.info(
                    f"✅ Iteration {self.iteration} - "
                    f"Customers: {len(customers)}, "
                    f"Accounts: {len(accounts)}, "
                    f"Transactions: {txn_count} | "
                    f"Total - C: {self.total_customers}, A: {self.total_accounts}, T: {self.total_transactions}"
                )
            
            except Exception as e:
                logger.error(f"Error in iteration {self.iteration}: {e}")
                raise
    
    def run(self, loop_enabled: bool = True):
        """Run the generator."""
        try:
            DatabaseInitializer.wait_for_database()
            
            logger.info(f"Starting data generator (loop_enabled={loop_enabled})")
            logger.info(f"Config - Customers/iter: {data_generator_config.NUM_CUSTOMERS}, "
                       f"Accounts/cust: {data_generator_config.ACCOUNTS_PER_CUSTOMER}, "
                       f"Transactions/iter: {data_generator_config.TRANSACTIONS_PER_ITERATION}")
            
            while True:
                self.run_iteration()
                
                if not loop_enabled:
                    logger.info("Single run mode - exiting")
                    break
                
                sleep_time = data_generator_config.SLEEP_SECONDS
                logger.debug(f"Sleeping for {sleep_time} seconds before next iteration...")
                time.sleep(sleep_time)
        
        except KeyboardInterrupt:
            logger.info("Generator interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error in generator: {e}")
            raise
        finally:
            report = quality_checker.get_quality_report()
            logger.info(f"Quality Report: {report}")
            DatabaseConnectionPool.close_all()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Banking Data Generator")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single iteration and exit"
    )
    args = parser.parse_args()
    
    generator = BankingDataGenerator()
    generator.run(loop_enabled=not args.once)


if __name__ == "__main__":
    main()
