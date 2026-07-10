# FinPilot AI

**Team DistributedMind — IDBI Innovate 2026**

AI-powered financial intelligence for emerging businesses.

---

## Elevator Pitch

FinPilot AI is an explainable AI platform that helps banks assess the financial health of new-to-credit MSMEs using alternative business signals — electricity consumption, water usage, EPFO contributions, and fuel expenses — alongside traditional financial indicators.

The platform is designed to support underwriters rather than replace them, providing transparent recommendations, confidence scores, and explainable reasoning for every assessment.

---

## Problem Statement & Vision

Traditional credit underwriting heavily depends on financial history such as GST filings, bank statements, UPI activity, and credit bureau reports. Many MSMEs and emerging businesses lack sufficient traditional financial footprints despite operating healthy businesses. As a result, they are often rejected by conventional credit scoring systems.

FinPilot AI addresses this challenge by combining traditional financial indicators with alternative operational signals:

- Electricity consumption
- Water consumption
- EPFO contributions
- Fuel expenses
- Business activity trends

The platform generates an explainable **Financial Health Score** that assists underwriters in making fairer and more informed lending decisions.

### Core Principles

- Human-in-the-loop decision making
- Explainability-first AI
- Support for new-to-credit businesses
- Transparent confidence scoring
- Auditability and traceability
- Modular and extensible architecture

### Mission

Enable financial inclusion by helping lenders recognize healthy businesses that would otherwise be invisible to traditional credit systems.

---

## Architecture

```
React SPA -> Spring Boot Gateway (Resilience4j) -> FastAPI ML Service
              |-> Redis cache (30-min TTL)
              |-> PostgreSQL (profiles + audit log + decisions)
```

### Layers

| Layer | Technology | Port | Role |
|-------|-----------|------|------|
| **Frontend** | React 18 + TypeScript + Vite | 5173 (dev) / 3000 (prod) | Underwriter SPA with 7-state machine |
| **Gateway** | Spring Boot 3.3 (Java 21) | 8080 | REST API, orchestration, resilience, caching |
| **ML Service** | FastAPI (Python 3.11) | 8000 | Feature engineering, model inference, SHAP |
| **Cache** | Redis 7 | internal | Score response cache (30-min TTL) |
| **Database** | PostgreSQL 16 | internal | Customer profiles, audit log, decisions |

### Core Workflow

```
Customer Profile
↓
Data Validation
↓
Data Completeness Check
↓
Traditional Data Available?
├── Yes → Feature Engineering
└── No  → Blank-Slate Decision Engine
         ↓
Feature Engineering (6 features)
↓
Feature Validation
↓
ML Prediction (GBM)
↓
SHAP Explainability
↓
Business Rule Validation
↓
Confidence Calculation
↓
Financial Health Score
↓
Audit Logging
↓
Underwriter Dashboard
```

---

## Quick Start

```bash
cp .env.example .env
docker compose -f docker/docker-compose.yml up -d
# Wait ~60s for health checks
curl -s -X POST http://localhost:8080/api/v1/score/CUST00042 | jq .
```

Frontend at http://localhost:3000 — enter a Customer ID or pick a demo profile.

One-command CLI alternative: `python cli.py dev`

---

## CLI Commands

```bash
python cli.py dev        # Full project startup (7 stages)
python cli.py status     # Repository health report
python cli.py test       # Run all test suites
python cli.py commit     # Quality-gated commit
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/score/{customerId}` | Score a customer (live or cached) |
| GET | `/api/v1/score/audit/{customerId}` | Audit history |
| GET | `/api/v1/customers/{customerId}/profile` | Profile + data completeness |
| POST | `/api/v1/decisions` | Submit underwriter decision |
| GET | `/api/v1/decisions/{customerId}` | Decision history |
| GET | `/api/v1/decisions/pending` | Pending reviews |
| GET | `/api/v1/score/health` | Health check |

---

## Scoring Logic

6 features computed from raw profile data:

| Feature | Weight | What it measures |
|---------|--------|-----------------|
| `payment_regularity` | 40% | Consistency across GST, EPFO, electricity, water |
| `financial_capacity_proxy` | 25% | GST turnover or electricity proxy |
| `business_longevity` | 20% | Years in operation (capped 15) with young-business floor |
| `data_coverage` | 10% | How many alt-data sources present |
| `evidence_confidence` | 5% | Consistency across payment signals |

**Bucket thresholds**: disciplined ≥ 0.70, yes-to-go ≥ 0.50, non-disciplined ≥ 0.30, no-to-go < 0.30

Business-type-aware signal weights and seasonality handling adjust per sector (manufacturing, logistics, retail, services, trading).

---

## Demo Profiles

| ID | Business | Type | Bucket | Notes |
|----|----------|------|--------|-------|
| CUST00042 | Ramesh Traders | Manufacturing | yes-to-go | Blank-slate, approved via alt-data |
| CUST00011 | Shakti Manufacturing | Manufacturing | disciplined | Full data, high performer |
| CUST00087 | Kaveri Logistics | Logistics | non-disciplined | Fuel volatility risk |
| CUST00134 | Anand Cold Chain | Trading | no-to-go | High risk, rejected |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| ML model | scikit-learn GradientBoostingClassifier |
| Model serving | FastAPI (Python 3.11) |
| API gateway | Spring Boot 3.3 (Java 21) |
| Resilience | Resilience4j (circuit breaker + retry + time limiter) |
| Database | PostgreSQL 16 + Flyway |
| Cache | Redis 7 |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Explainability | SHAP (KernelExplainer) |
| Containerisation | Docker Compose |
| CI/CD | GitHub Actions |

---

## Repository Structure

```
backend/
  common/       Shared DTOs, JPA entities, Flyway migrations, Redis config
  customer/     Customer profile lookup
  feature/      Feature module (passive — FE lives in ML service)
  scoring/      Core scoring service + controllers
  audit/        Audit log queries

ml-service/
  app/          FastAPI entrypoint, router, feature engineering, model loader
  tests/        Pytest suite (92 tests)

frontend/
  src/          React SPA — App, Layout, SearchBar, ScoreOverview, AuditTrail

synthetic-data/
  generate_profiles.py   350-customer profile generator
  label_profiles.py      Composite score → bucket assigner
  seed.py                Idempotent DB seeding

docs/
  architecture.md        Full system architecture
  developer-guide.md     Setup, CLI usage, troubleshooting
  scoring-logic.md       Complete scoring formulas
  stack-decisions.md     Technology rationale and design decisions
```

---

## Documentation

Detailed documentation in the `docs/` directory:

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | Full system architecture, components, data flow, API contracts, database schema |
| [Developer Guide](docs/developer-guide.md) | Setup instructions, CLI usage, configuration, troubleshooting |
| [Scoring Logic](docs/scoring-logic.md) | Complete scoring formulas, feature engineering, SHAP, edge cases |
| [Stack & Decisions](docs/stack-decisions.md) | Technology rationale, design decisions, trade-offs, roadmap |

---

## License

All Rights Reserved. © 2026 DistributedMind.

This project is submitted as part of IDBI Innovate 2026. No license is granted for commercial use, reproduction, or distribution without explicit permission.
