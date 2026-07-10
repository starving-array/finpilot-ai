#!/bin/bash
set -euo pipefail

echo "=== FHSS Development Setup ==="

# Backend
echo "Building backend..."
cd backend
./mvnw clean install -DskipTests -B
cd ..

# ML Service
echo "Setting up ML service..."
cd ml-service
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd ..

# Frontend
echo "Setting up frontend..."
cd frontend
npm install
cd ..

# Synthetic Data
echo "Setting up synthetic data generator..."
cd synthetic-data
python -m venv .venv
source .venv/bin/activate
pip install faker pandas psycopg2-binary
cd ..

echo "=== Setup complete ==="
echo "Run 'docker compose -f docker/docker-compose.yml up' to start all services"
