# 💳 Banking End-to-End Data Pipeline

A production-ready, real-time banking data engineering pipeline demonstrating Change Data Capture (CDC), event streaming, and data pipeline best practices. Built with modern data stack tools for portfolio demonstration.

## ✨ Key Features

- **Real-Time CDC**: Captures database changes using Debezium PostgreSQL connector
- **Event Streaming**: Apache Kafka for reliable event distribution
- **Data Validation**: Built-in data quality checks and validation rules
- **Monitoring**: Real-time dashboard and health checks
- **Error Handling**: Comprehensive logging and resilience patterns
- **Scalable Storage**: Parquet and JSON output formats with date partitioning
- **Docker-Ready**: Complete containerization with docker-compose
- **Production Patterns**: Circuit breakers, connection pooling, retry logic
- **Testing**: Unit tests and validation framework

## 🏗️ Architecture

```
┌─────────────────────┐
│   PostgreSQL OLTP   │
│  (Source System)    │
│  customers, accounts│
│  transactions       │
└──────────┬──────────┘
           │ WAL
           ▼
┌─────────────────────┐
│     Debezium CDC    │
│   Kafka Connect     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Apache Kafka      │
│   (Event Hub)       │
│  3 Topics per table │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐  ┌──────────┐
│Generator│  │ Consumer │
│ Faker   │  │ Parquet/ │
│         │  │   JSON   │
└─────────┘  └──────────┘
```

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Database | PostgreSQL 15 | OLTP source system |
| Streaming | Apache Kafka 7.4.1 | Event broker |
| CDC | Debezium 2.2 | Change Data Capture |
| Language | Python 3.11 | Pipeline orchestration |
| Data Format | Parquet/JSON | Data persistence |
| Containerization | Docker & Compose | Deployment |
| Validation | Pydantic-style | Data quality |
| Monitoring | Custom Dashboard | Real-time insights |

## 📋 Prerequisites

- **Docker & Docker Compose** (v1.29+)
- **Python 3.10+**
- **Git**
- **4GB RAM minimum** (8GB recommended)
- **10GB disk space**

## 🚀 Quick Start

### 1. **Clone & Setup**

```bash
cd Banking-end-to-end-pipelines

# For Linux/macOS
chmod +x startup.sh
./startup.sh

# For Windows
startup.bat
```

### 2. **Or Manual Setup**

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start Docker services
docker-compose up -d

# Run orchestrator
python orchestrator.py --startup
```

### 3. **Run Data Pipeline** (in separate terminals)

```bash
# Terminal 1: Generate data
python data-generator/faker_generator.py

# Terminal 2: Consume events
python consumer/kafka_consumer.py

# Terminal 3: Monitor
python monitoring.py --interval 30
```

## 📊 Data Model

### Customers Table
```sql
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    created_at TIMESTAMP
);
```

### Accounts Table
```sql
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers,
    account_type VARCHAR(50),  -- SAVINGS, CHECKING, MONEY_MARKET
    balance NUMERIC(18,2),
    currency CHAR(3),
    created_at TIMESTAMP
);
```

### Transactions Table
```sql
CREATE TABLE transactions (
    id BIGSERIAL PRIMARY KEY,
    account_id INT REFERENCES accounts,
    txn_type VARCHAR(50),  -- DEPOSIT, WITHDRAWAL, TRANSFER
    amount NUMERIC(18,2),
    related_account_id INT,
    status VARCHAR(20),
    created_at TIMESTAMP
);
```

## 🎯 Configuration

### Environment Variables (.env)

```bash
# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=banking
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Kafka
KAFKA_BOOTSTRAP=kafka:9092
KAFKA_GROUP=banking-consumer-group

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs

# Data Generation
NUM_CUSTOMERS=50
ACCOUNTS_PER_CUSTOMER=3
NUM_TRANSACTIONS=100
GENERATOR_SLEEP_SECONDS=5

# Consumer
CONSUMER_OUTPUT_DIR=data
CONSUMER_USE_PARQUET=true
CONSUMER_BATCH_SIZE=100
CONSUMER_FLUSH_INTERVAL=60
```

## 🔧 Usage Examples

### Generate Data Once
```bash
python data-generator/faker_generator.py --once
```

### Register Connector with Force
```bash
python kafka-debezium/register_connector.py --force
```

### Check Connector Status
```bash
python kafka-debezium/register_connector.py --check
```

### Run Health Check
```bash
python orchestrator.py --health
```

### Monitor with Custom Interval
```bash
python monitoring.py --interval 60
```

### Run Unit Tests
```bash
python -m pytest tests.py -v
# or
python tests.py
```

## 📁 Project Structure

```
Banking-end-to-end-pipelines/
├── config.py                    # Centralized configuration
├── database.py                  # DB utilities & connection pooling
├── logger.py                    # Structured logging
├── validation.py                # Data validation & quality checks
├── orchestrator.py              # Pipeline orchestration
├── monitoring.py                # Real-time monitoring dashboard
├── tests.py                     # Unit tests
│
├── data-generator/
│   └── faker_generator.py       # Generate realistic banking data
│
├── consumer/
│   └── kafka_consumer.py        # Consume Kafka events & persist
│
├── kafka-debezium/
│   └── register_connector.py    # CDC connector management
│
├── postgres/
│   └── schema.sql               # Database schema
│
├── docker-compose.yml           # Container orchestration
├── Dockerfile                   # Python app image
├── requirements.txt             # Python dependencies
├── startup.sh                   # Linux/macOS startup
├── startup.bat                  # Windows startup
└── README.md                    # This file
```

## 🚦 Service URLs

| Service | URL | User/Pass |
|---------|-----|-----------|
| Kafka Connect | http://localhost:8083 | - |
| PostgreSQL | localhost:5432 | postgres/postgres |
| Kafka Broker | localhost:9092 (internal) | - |
| Kafka Broker | localhost:29092 (host) | - |
| Zookeeper | localhost:2181 | - |

## 📊 Monitoring Dashboard

The monitoring tool provides real-time insights:

```bash
python monitoring.py
```

Displays:
- ✅ Database health status
- 📈 Data volume trends (customers, accounts, transactions)
- 💰 Total balance
- 📊 Processing rates (records/minute)
- 🔍 Data quality scores
- 📋 Statistical summaries

## 🔍 Data Quality Checks

Automatic validation for:

- **Email Format**: RFC-compliant email validation
- **Account Balance**: Non-negative validation
- **Transaction Amounts**: Positive values check
- **Transaction Types**: Enum validation (DEPOSIT, WITHDRAWAL, TRANSFER)
- **Account Types**: Valid types (SAVINGS, CHECKING, MONEY_MARKET, CREDIT)
- **Required Fields**: Completeness checks

## 🐛 Troubleshooting

### Docker Services Won't Start
```bash
# Check Docker daemon
docker ps

# View logs
docker-compose logs -f

# Restart services
docker-compose restart
```

### Database Connection Error
```bash
# Wait for PostgreSQL to be ready
python -c "from database import DatabaseInitializer; DatabaseInitializer.wait_for_database()"
```

### Kafka Consumer Lag
```bash
# Check consumer group status
python monitoring.py --once

# Reset consumer offset
python consumer/kafka_consumer.py  # Starts from 'earliest'
```

### Connector Not Registering
```bash
python kafka-debezium/register_connector.py --force
# Check status
python kafka-debezium/register_connector.py --check
```

## 📈 Performance Tips

1. **Batch Size**: Increase `CONSUMER_BATCH_SIZE` for higher throughput
2. **Flush Interval**: Adjust `CONSUMER_FLUSH_INTERVAL` based on data volume
3. **Connection Pool**: Tune `POSTGRES_MAX_POOL_SIZE` for concurrent operations
4. **Generator Rate**: Modify `GENERATOR_SLEEP_SECONDS` and data volumes

## 🧪 Testing

```bash
# Run all tests
python -m unittest tests.py -v

# Run specific test class
python -m unittest tests.TestDataValidator -v

# Run with pytest (if installed)
pip install pytest
pytest tests.py -v --tb=short
```

## 📚 Key Concepts Demonstrated

### 1. **Change Data Capture (CDC)**
- Captures INSERT, UPDATE, DELETE events from PostgreSQL WAL
- Debezium streams changes in real-time to Kafka

### 2. **Event-Driven Architecture**
- Decoupled producer (PostgreSQL) and consumer (Data pipeline)
- Kafka as central event broker

### 3. **Data Validation**
- Schema validation on ingestion
- Quality checks during processing
- Error tracking and reporting

### 4. **Connection Pooling**
- Efficient database connection management
- Prevents connection exhaustion

### 5. **Distributed Logging**
- Structured logging with context
- Log rotation and file management

### 6. **Error Handling & Retries**
- Exponential backoff for transient failures
- Graceful degradation

### 7. **Monitoring & Observability**
- Real-time dashboard
- Data quality metrics
- Performance tracking

## 🚢 Production Considerations

- **Data Retention**: Implement partitioning by date (done for Parquet)
- **Backups**: Regular database backups
- **Alerting**: Integrate with monitoring tools (Prometheus, DataDog, etc.)
- **Security**: Use secrets management for credentials
- **Scaling**: Use Kafka partitioning for parallel processing
- **Compression**: Use Snappy compression for Parquet files

## 📝 Sample Output

```
==================================
🏦 BANKING DATA PIPELINE - MONITORING DASHBOARD
==================================

📊 DATABASE STATUS
--
✅ Health: Healthy
📦 Size: 15 MB
   Customers: 2,543
   Accounts: 7,629
   Transactions: 156,872

📈 PIPELINE METRICS
--
Last Update: 2024-01-20T10:30:45.123Z

Data Volume:
  📱 Customers: 2,543 (+1.2/min)
  💳 Accounts: 7,629 (+3.8/min)
  💰 Transactions: 156,872 (+45.3/min)
  💵 Total Balance: $12,345,678.90
```

## 🤝 Contributing

This is a portfolio project. Suggestions and improvements welcome!

## 📜 License

MIT License - See LICENSE file for details

## 🎓 Learning Resources

- [Debezium Documentation](https://debezium.io/)
- [Apache Kafka Guide](https://kafka.apache.org/documentation/)
- [PostgreSQL WAL](https://www.postgresql.org/docs/current/wal.html)
- [Data Engineering Best Practices](https://github.com/datatalkclub/data-engineering-zoomcamp)

## ✅ Checklist for Production

- [ ] Change default PostgreSQL password
- [ ] Configure SSL/TLS for Kafka
- [ ] Set up automated backups
- [ ] Configure monitoring alerts
- [ ] Implement data retention policies
- [ ] Set up CI/CD pipeline
- [ ] Add API gateway for data access
- [ ] Implement data lineage tracking
- [ ] Add data cataloging (Apache Atlas, etc.)
- [ ] Set up disaster recovery

## 📞 Support

For issues, questions, or improvements:
1. Check troubleshooting section
2. Review logs in `logs/` directory
3. Run health checks: `python orchestrator.py --health`
4. Check Docker logs: `docker-compose logs`

---

**Built with ❤️ for data engineering portfolio** | Last Updated: 2024

