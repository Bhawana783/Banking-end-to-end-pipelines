"""
Monitoring Dashboard - Real-time monitoring and metrics for the banking pipeline
"""

import time
import sys
import os
import json
from datetime import datetime, timedelta
from collections import deque

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseHealth, DatabaseOperations, get_db_cursor
from logger import get_logger

logger = get_logger("monitoring")


class PipelineMetrics:
    """Tracks pipeline metrics over time."""
    
    def __init__(self, window_size: int = 60):
        self.window_size = window_size
        self.timestamps = deque(maxlen=window_size)
        self.customer_counts = deque(maxlen=window_size)
        self.account_counts = deque(maxlen=window_size)
        self.transaction_counts = deque(maxlen=window_size)
        self.total_balances = deque(maxlen=window_size)
        self.last_update = None
    
    def collect(self):
        """Collect current metrics."""
        timestamp = datetime.now()
        
        customers = DatabaseOperations.get_customer_count()
        accounts = DatabaseOperations.get_account_count()
        transactions = DatabaseOperations.get_transaction_count()
        total_balance = DatabaseOperations.get_total_balance()
        
        self.timestamps.append(timestamp)
        self.customer_counts.append(customers)
        self.account_counts.append(accounts)
        self.transaction_counts.append(transactions)
        self.total_balances.append(total_balance)
        
        self.last_update = timestamp
    
    def get_rate_of_change(self, metric_deque):
        """Calculate rate of change (items per minute)."""
        if len(metric_deque) < 2:
            return 0
        
        time_diff = (self.timestamps[-1] - self.timestamps[0]).total_seconds() / 60
        if time_diff == 0:
            return 0
        
        count_diff = metric_deque[-1] - metric_deque[0]
        return count_diff / time_diff
    
    def get_summary(self) -> dict:
        """Get metrics summary."""
        return {
            "timestamp": datetime.now().isoformat(),
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "current": {
                "customers": self.customer_counts[-1] if self.customer_counts else 0,
                "accounts": self.account_counts[-1] if self.account_counts else 0,
                "transactions": self.transaction_counts[-1] if self.transaction_counts else 0,
                "total_balance": self.total_balances[-1] if self.total_balances else 0,
            },
            "rates": {
                "customers_per_minute": round(self.get_rate_of_change(self.customer_counts), 2),
                "accounts_per_minute": round(self.get_rate_of_change(self.account_counts), 2),
                "transactions_per_minute": round(self.get_rate_of_change(self.transaction_counts), 2),
            },
            "history_points": len(self.timestamps)
        }


class PipelineMonitor:
    """Monitors the entire banking pipeline."""
    
    def __init__(self, interval: int = 30):
        self.interval = interval
        self.metrics = PipelineMetrics()
        self.start_time = datetime.now()
    
    def print_header(self):
        """Print dashboard header."""
        print("\n" + "=" * 100)
        print("🏦 BANKING DATA PIPELINE - MONITORING DASHBOARD")
        print("=" * 100)
    
    def print_database_status(self):
        """Print database status."""
        print("\n📊 DATABASE STATUS")
        print("-" * 100)
        
        try:
            is_healthy = DatabaseHealth.is_healthy()
            counts = DatabaseHealth.get_table_counts()
            size = DatabaseHealth.get_database_size()
            
            status_emoji = "✅" if is_healthy else "❌"
            print(f"{status_emoji} Health: {'Healthy' if is_healthy else 'Unhealthy'}")
            print(f"📦 Size: {size}")
            print(f"   Customers: {counts.get('customers', 0):,}")
            print(f"   Accounts: {counts.get('accounts', 0):,}")
            print(f"   Transactions: {counts.get('transactions', 0):,}")
        
        except Exception as e:
            print(f"❌ Error reading database: {e}")
    
    def print_metrics(self):
        """Print current metrics."""
        print("\n📈 PIPELINE METRICS")
        print("-" * 100)
        
        try:
            self.metrics.collect()
            summary = self.metrics.get_summary()
            
            current = summary.get("current", {})
            rates = summary.get("rates", {})
            
            print(f"Last Update: {summary.get('last_update', 'N/A')}")
            print(f"\nData Volume:")
            print(f"  📱 Customers: {current.get('customers', 0):,} "
                  f"(+{rates.get('customers_per_minute', 0):.1f}/min)")
            print(f"  💳 Accounts: {current.get('accounts', 0):,} "
                  f"(+{rates.get('accounts_per_minute', 0):.1f}/min)")
            print(f"  💰 Transactions: {current.get('transactions', 0):,} "
                  f"(+{rates.get('transactions_per_minute', 0):.1f}/min)")
            print(f"  💵 Total Balance: ${current.get('total_balance', 0):,.2f}")
        
        except Exception as e:
            print(f"❌ Error collecting metrics: {e}")
    
    def print_data_quality(self):
        """Print data quality information."""
        print("\n🔍 DATA QUALITY")
        print("-" * 100)
        
        try:
            with get_db_cursor() as cursor:
                # Check for NULL values
                cursor.execute("""
                    SELECT COUNT(*) FROM customers WHERE first_name IS NULL OR last_name IS NULL OR email IS NULL
                """)
                null_customers = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM accounts WHERE balance < 0
                """)
                negative_balances = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM transactions WHERE status NOT IN ('COMPLETED', 'PENDING', 'FAILED', 'REVERSED')
                """)
                invalid_txns = cursor.fetchone()[0]
                
                issues = null_customers + negative_balances + invalid_txns
                
                if issues == 0:
                    print("✅ No data quality issues detected")
                else:
                    if null_customers > 0:
                        print(f"⚠️  NULL values in customers: {null_customers}")
                    if negative_balances > 0:
                        print(f"⚠️  Negative balances: {negative_balances}")
                    if invalid_txns > 0:
                        print(f"⚠️  Invalid transaction statuses: {invalid_txns}")
        
        except Exception as e:
            print(f"❌ Error checking data quality: {e}")
    
    def print_statistics(self):
        """Print statistical information."""
        print("\n📊 STATISTICS")
        print("-" * 100)
        
        try:
            with get_db_cursor() as cursor:
                # Average balance per account
                cursor.execute("""
                    SELECT AVG(balance), MIN(balance), MAX(balance) FROM accounts
                """)
                avg_bal, min_bal, max_bal = cursor.fetchone()
                print(f"Account Balance Statistics:")
                print(f"  Average: ${avg_bal:,.2f}" if avg_bal else "  Average: N/A")
                print(f"  Min: ${min_bal:,.2f}" if min_bal else "  Min: N/A")
                print(f"  Max: ${max_bal:,.2f}" if max_bal else "  Max: N/A")
                
                # Transaction statistics
                cursor.execute("""
                    SELECT AVG(amount), COUNT(*) FROM transactions
                """)
                avg_txn, txn_count = cursor.fetchone()
                print(f"\nTransaction Statistics:")
                print(f"  Average Amount: ${avg_txn:,.2f}" if avg_txn else "  Average Amount: N/A")
                print(f"  Total Count: {txn_count:,}")
                
                # Customers per account
                cursor.execute("""
                    SELECT AVG(acc_count) FROM (
                        SELECT customer_id, COUNT(*) as acc_count FROM accounts GROUP BY customer_id
                    ) sub
                """)
                avg_accounts = cursor.fetchone()[0]
                print(f"\nAverage Accounts per Customer: {avg_accounts:.2f}" if avg_accounts else "N/A")
        
        except Exception as e:
            print(f"❌ Error collecting statistics: {e}")
    
    def print_footer(self):
        """Print dashboard footer."""
        uptime = datetime.now() - self.start_time
        print("\n" + "=" * 100)
        print(f"⏱️  Uptime: {uptime}")
        print(f"⏰ Last Refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔄 Refresh Interval: {self.interval} seconds")
        print("=" * 100)
    
    def run(self, iterations: int = None):
        """Run monitoring loop."""
        try:
            iteration = 0
            while True:
                self.print_header()
                self.print_database_status()
                self.print_metrics()
                self.print_data_quality()
                self.print_statistics()
                self.print_footer()
                
                iteration += 1
                if iterations and iteration >= iterations:
                    break
                
                print(f"\n⏳ Waiting {self.interval} seconds until next refresh... (Press Ctrl+C to exit)")
                time.sleep(self.interval)
        
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in monitoring: {e}")
            raise


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Banking Pipeline Monitor")
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Refresh interval in seconds (default: 30)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Display metrics once and exit"
    )
    
    args = parser.parse_args()
    
    monitor = PipelineMonitor(interval=args.interval)
    iterations = 1 if args.once else None
    monitor.run(iterations=iterations)


if __name__ == "__main__":
    main()
