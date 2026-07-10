Write-Host "=== FHSS Development Setup ==="

# Backend
Write-Host "Building backend..."
Set-Location backend
.\mvnw.cmd clean install -DskipTests -B
Set-Location ..

# ML Service
Write-Host "Setting up ML service..."
Set-Location ml-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Set-Location ..

# Frontend
Write-Host "Setting up frontend..."
Set-Location frontend
npm install
Set-Location ..

# Synthetic Data
Write-Host "Setting up synthetic data generator..."
Set-Location synthetic-data
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install faker pandas psycopg2-binary
Set-Location ..

Write-Host "=== Setup complete ==="
Write-Host "Run 'docker compose -f docker/docker-compose.yml up' to start all services"
