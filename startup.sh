#!/bin/bash
# Startup script for Banking Data Pipeline - Linux/macOS

set -e

echo "=================================="
echo "🏦 Banking Data Pipeline Startup"
echo "=================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

# Setup Python virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "🔧 Activating virtual environment..."
source venv/bin/activate

echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "🚀 Starting Docker containers..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

echo ""
echo "✅ Starting infrastructure setup..."
python3 orchestrator.py --startup

echo ""
echo "=================================="
echo "✅ Pipeline startup complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Run data generator (in another terminal):"
echo "   python3 data-generator/faker_generator.py"
echo ""
echo "2. Run Kafka consumer (in another terminal):"
echo "   python3 consumer/kafka_consumer.py"
echo ""
echo "3. Monitor pipeline (in another terminal):"
echo "   python3 monitoring.py"
echo ""
echo "=================================="
