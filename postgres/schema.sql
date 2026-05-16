-- Banking OLTP Schema with Indexes and Constraints
-- Designed for CDC with Debezium

-- Enable UUID extension if needed
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- CUSTOMERS TABLE
-- ============================================================================
-- Banking OLTP initial schema (simplified)


CREATE TABLE IF NOT EXISTS customers (
	id SERIAL PRIMARY KEY,
	first_name VARCHAR(100) NOT NULL,
	last_name VARCHAR(100) NOT NULL,
	email VARCHAR(255) NOT NULL UNIQUE,
	phone VARCHAR(20),
	address TEXT,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
	is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_created_at ON customers(created_at);
CREATE INDEX idx_customers_is_active ON customers(is_active);

-- ============================================================================
-- ACCOUNTS TABLE
-- ============================================================================


CREATE TABLE IF NOT EXISTS accounts (
	id SERIAL PRIMARY KEY,
	customer_id INT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
	account_type VARCHAR(50) NOT NULL,
	balance NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (balance >= 0),
	currency CHAR(3) NOT NULL DEFAULT 'USD',
	account_number VARCHAR(20) UNIQUE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
	is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_accounts_customer_id ON accounts(customer_id);
CREATE INDEX idx_accounts_account_type ON accounts(account_type);
CREATE INDEX idx_accounts_currency ON accounts(currency);
CREATE INDEX idx_accounts_created_at ON accounts(created_at);
CREATE INDEX idx_accounts_is_active ON accounts(is_active);

-- ============================================================================
-- TRANSACTIONS TABLE
-- ============================================================================


CREATE TABLE IF NOT EXISTS transactions (
	id BIGSERIAL PRIMARY KEY,
	account_id INT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
	txn_type VARCHAR(50) NOT NULL,
	amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
	related_account_id INT NULL REFERENCES accounts(id) ON DELETE SET NULL,
	status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED',
	description TEXT,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Key indexes for performance
CREATE INDEX idx_transactions_account_id ON transactions(account_id);
CREATE INDEX idx_transactions_related_account_id ON transactions(related_account_id);
CREATE INDEX idx_transactions_account_created ON transactions(account_id, created_at);
CREATE INDEX idx_transactions_txn_type ON transactions(txn_type);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_created_at ON transactions(created_at);

-- ============================================================================
-- AUDIT LOG TABLE (Optional - for tracking changes)
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
	id BIGSERIAL PRIMARY KEY,
	table_name VARCHAR(100) NOT NULL,
	operation VARCHAR(10) NOT NULL,
	record_id INT NOT NULL,
	old_values JSONB,
	new_values JSONB,
	changed_by VARCHAR(255),
	changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_log_table_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_log_changed_at ON audit_log(changed_at);

-- ============================================================================
-- DATA QUALITY CONSTRAINTS
-- ============================================================================

-- Check transaction types
ALTER TABLE transactions ADD CONSTRAINT chk_valid_txn_type 
CHECK (txn_type IN ('DEPOSIT', 'WITHDRAWAL', 'TRANSFER'));

-- Check transaction status
ALTER TABLE transactions ADD CONSTRAINT chk_valid_status 
CHECK (status IN ('PENDING', 'COMPLETED', 'FAILED', 'REVERSED'));

-- Check account types
ALTER TABLE accounts ADD CONSTRAINT chk_valid_account_type 
CHECK (account_type IN ('SAVINGS', 'CHECKING', 'MONEY_MARKET', 'CREDIT'));

-- Check currency codes
ALTER TABLE accounts ADD CONSTRAINT chk_valid_currency 
CHECK (currency IN ('USD', 'EUR', 'GBP', 'CAD', 'AUD'));


-- Simple indexed columns for performance in queries