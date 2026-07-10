# Developer Guide

**FinPilot AI — Team DistributedMind**

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Quick Start with CLI](#2-quick-start-with-cli)
3. [Manual Setup - Common Steps](#3-manual-setup---common-steps)
4. [Path A: Full Docker (16GB+ RAM)](#4-path-a-full-docker-16gb-ram)
5. [Path B: Partial Docker (8GB RAM)](#5-path-b-partial-docker-8gb-ram)
6. [End-to-End Verification](#6-end-to-end-verification)
7. [Configuration Reference](#7-configuration-reference)
8. [Demo Profiles](#8-demo-profiles)
9. [Troubleshooting](#9-troubleshooting)
10. [Project Map](#10-project-map)

---

## 1. Prerequisites

| Tool | Version | Required For |
|------|---------|-------------|
| Python | 3.11+ | ML service, data generation |
| Node.js | 18+ | Frontend |
| Docker Desktop | latest | PostgreSQL, Redis, optional containers |
| Java | 21 (JDK) | Backend (only if running outside Docker) |
| Git | any | Version control |

---

## 2. Quick Start with CLI

The fastest way to get the full system running:

```bash
# 1. Clone and configure
git clone <repo-url> DistributedMind-IDBI
cd DistributedMind-IDBI
cp .env.example .env

# 2. One-command startup
python cli.py dev
```

The CLI handles the full 7-step startup:
1. Environment check (Python, Docker, Node)
2. Start infrastructure (PostgreSQL + Redis via Docker)
3. Start backend (Spring Boot with Flyway migrations)
4. Seed database (350 customer profiles)
5. Train ML model
6. Start ML service (FastAPI)
7. Start frontend (Vite dev server)

To skip slow steps when iterating:
```bash
python cli.py dev --skip-seed --skip-train
```

Other CLI commands:
```bash
python cli.py status    # Health report (git, Docker, APIs)
python cli.py commit    # Quality-gated commit with conventional commit prompt
```

---

### Live Logs After `python cli.py dev`

The CLI writes its own log to `logs/cli.log`.

For Docker containers started by the CLI, follow logs in real time:

```bash
docker compose -f docker/docker-compose.yml logs -f          # all containers
docker compose -f docker/docker-compose.yml logs -f backend  # single service
```

The ML service and frontend are launched as background processes with their output suppressed. To see their live output, run them manually in separate terminals instead:

```bash
# Terminal 2 — ML Service
cd ml-service
set MODEL_PATH=models\model_latest.joblib
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 3 — Frontend
cd frontend
npx vite --port 5173
```

---

## 3. Manual Setup - Common Steps

### A. Start Infrastructure

```bash
docker compose -f docker/docker-compose.yml up -d postgres redis
```

Wait 10 seconds, then verify:
```bash
docker compose -f docker/docker-compose.yml ps
```

Both `fhss-postgres` and `fhss-redis` should show `Up (healthy)`.

### B. Create Database Schema (Flyway Migrations)

The backend runs Flyway migrations automatically on startup:
```bash
docker compose -f docker/docker-compose.yml up -d backend
```

Wait ~60 seconds for Spring Boot to start, then verify:
```bash
curl http://localhost:8080/api/v1/score/health
```

Expected: `{"status":"UP","service":"fhss-gateway","timestamp":"..."}`

### C. Seed the Database

```bash
cd synthetic-data
pip install psycopg2-binary
python seed.py
cd ..
```

Expected: `Loaded 350 labeled profiles ... Inserted: 350, Skipped: 0`

### D. Train the ML Model

```bash
cd ml-service
pip install -r requirements.txt
python -m app.training.train_model ..\synthetic-data\output\profiles_labeled.csv
```

Expected: Classification report output, model saved to `models/model_latest.joblib`.

---

## 4. Path A: Full Docker (16GB+ RAM)

Everything runs in Docker containers:

```bash
# Start remaining services
docker compose -f docker/docker-compose.yml up -d ml-service frontend
```

Wait ~20 seconds for ML service to load the model, then verify:
```bash
curl http://localhost:8000/health
```

Expected: `{"status":"UP","model_version":"2.0.x","model_loaded":true,...}`

Access: `http://localhost:3000`

---

## 5. Path B: Partial Docker (8GB RAM)

Run ML service and frontend locally for faster iteration.

### E2. Start ML Service Locally

Open a **new terminal**:
```bash
cd ml-service
set MODEL_PATH=models\model_latest.joblib
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Wait for `Application startup complete`, then verify:
```bash
curl http://localhost:8000/health
```

### F2. Start Frontend Locally

Open a **new terminal**:
```bash
cd frontend
npm install
npm run dev
```

Access: `http://localhost:5173` (Vite proxy forwards `/api` to backend on `:8080`)

---

## 6. End-to-End Verification

Run these from any terminal:

```bash
# Health check
curl http://localhost:8080/api/v1/score/health

# Score a customer
curl -s -X POST http://localhost:8080/api/v1/score/CUST00001 | jq .

# Get customer profile
curl -s http://localhost:8080/api/v1/customers/CUST00001/profile | jq .

# Submit a decision
curl -s -X POST http://localhost:8080/api/v1/decisions ^
  -H "Content-Type: application/json" ^
  -d "{\"customer_id\":\"CUST00001\",\"decision\":\"APPROVE\",\"remarks\":\"Good profile\"}"

# Get pending reviews
curl -s http://localhost:8080/api/v1/decisions/pending | jq .
```

---

## 7. Configuration Reference

All configuration is driven by environment variables in `.env`.

### Backend

| Variable | Default | Notes |
|----------|---------|-------|
| `ML_SERVICE_URL` | `http://ml-service:8000` | Change to `http://host.docker.internal:8000` for Path B |
| `SPRING_DATASOURCE_URL` | `jdbc:postgresql://postgres:5432/fhss` | |
| `SPRING_DATASOURCE_USERNAME` | `fhss` | |
| `SPRING_DATASOURCE_PASSWORD` | `change_me_in_production` | |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:3000` | |

### ML Service

| Variable | Default | Notes |
|----------|---------|-------|
| `MODEL_PATH` | `/app/models/model_latest.joblib` | Use `models\model_latest.joblib` on Windows |
| `UVICORN_WORKERS` | `2` | |
| `ML_SERVICE_PORT` | `8000` | |

### Docker Compose

| Variable | Default | Notes |
|----------|---------|-------|
| `POSTGRES_DB` | `fhss` | |
| `POSTGRES_USER` | `fhss` | |
| `POSTGRES_PASSWORD` | `change_me_in_production` | |

Override any variable by setting it in `.env` (gitignored). See `.env.example` for the full list.

---

## 8. Demo Profiles

The system comes pre-seeded with 350 synthetic profiles (CUST00001-CUST00350). Four curated demo profiles are hardcoded in the SearchBar dropdown:

| ID | Business Name | Type | Bucket | Notes |
|----|---------------|------|--------|-------|
| CUST00042 | Ramesh Traders | Manufacturing | yes-to-go | Blank-slate - approved via alt-data |
| CUST00011 | Shakti Manufacturing | Manufacturing | disciplined | Full data - high performer |
| CUST00087 | Kaveri Logistics | Logistics | non-disciplined | Fuel volatility risk |
| CUST00134 | Anand Cold Chain | Trading | no-to-go | High risk - rejected |

---

## 9. Troubleshooting

### Scoring returns SCORING_UNAVAILABLE

**Cause**: Backend cannot reach ML service, or model not loaded.

**Check**:
```bash
# Is ML running?
curl http://localhost:8000/health

# Is backend healthy?
curl http://localhost:8080/api/v1/score/health
```

If ML returns `DEGRADED`, retrain the model (Step D).

### Backend returns 404 / CUSTOMER_NOT_FOUND

**Cause**: Database not seeded.

**Fix**: Run `python seed.py` from `synthetic-data/` directory.

### Frontend shows stale data banner

**Cause**: ML service was down during scoring; response from Redis/audit cache.

**Fix**: Start ML service and re-score.

### Port already in use

```bash
netstat -ano | findstr :8080
taskkill /PID <PID> /F
```

### Docker container keeps restarting

```bash
docker logs fhss-backend --tail 50
```

### "password authentication failed" on PostgreSQL

Old data exists - clear and restart:
```bash
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d postgres redis
```

### Windows-specific: ML service fails to start

Ensure Python scripts use the correct path separator:
```bash
set MODEL_PATH=models\model_latest.joblib
```

And pip install with quotes for paths with spaces:
```bash
python -m pip install -r requirements.txt
```

---

## 10. Project Map

```
DistributedMind-IDBI/
  cli.py                          Unified CLI tool (dev, status, commit)

  synthetic-data/
    generate_profiles.py          350-customer profile generator
    label_profiles.py             Composite score -> bucket assigner
    seed.py                       Idempotent DB seeding via psycopg2
    output/profiles_labeled.csv   Seeded labeled profiles

  ml-service/
    app/
      main.py                     FastAPI entry point with lifespan
      router.py                   POST /predict, GET /health
      feature_engineering.py      6-feature computation (THE CORE)
      model_loader.py             Model loading at startup
      explain.py                  SHAP explanation computation
      business_weights.py         Sector-specific signal weights
      epfo_checks.py              EPFO plausibility flag
      capacity_flag.py            Loan-to-capacity assessment
      seasonality.py              Fuel/electricity volatility flags
      training/
        train_model.py            GBM training script
    models/                       .joblib model artifacts

  backend/
    scoring/
      controller/ScoreController.java       REST endpoints
      service/ScoringClientService.java     Core orchestration + resilience
      service/DecisionService.java          Underwriter workflow
    common/
      resources/db/migration/               Flyway SQL migrations (V1-V10)

  frontend/
    src/
      App.tsx                   7-state orchestrator
      components/               Layout, SearchBar, ScoreOverview,
                                ScoreDetail, AuditTrail

  docs/
    architecture.md             Full system architecture
    developer-guide.md          This document
    scoring-logic.md            Complete scoring logic with formulas
    stack-decisions.md          Technology stack and design decisions
```

For detailed architecture, scoring logic, and tech decisions, refer to the other documents in `docs/`.
