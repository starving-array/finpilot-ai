# FinPilot AI

**Team DistributedMind — IDBI Innovate 2026**

AI-powered financial intelligence for emerging businesses.

---

## Elevator Pitch

FinPilot AI is an explainable AI platform that helps banks assess the financial health of new-to-credit MSMEs using alternative business signals — electricity consumption, water usage, EPFO contributions, and fuel expenses — alongside traditional financial indicators.

The platform is designed to support underwriters rather than replace them, providing transparent recommendations, confidence scores, and explainable reasoning for every assessment.

---

## Quick Start

### Prerequisites

- Docker Desktop (16GB+ RAM recommended)
- Git

### Run

```bash
git clone <repo-url> finpilot-ai
cd finpilot-ai
cp .env.example .env
docker compose -f docker/docker-compose.yml up -d
# Wait ~60s for health checks
curl -s -X POST http://localhost:8080/api/v1/score/CUST00042 | jq .
```

Frontend at [http://localhost:3000](http://localhost:3000) — enter a Customer ID or pick a demo profile.

### Production Deploy

```bash
export GHCR_NAMESPACE=your-org
docker compose -f docker/docker-compose.prod.yml up -d
```

---

## Architecture

```
React SPA (nginx:3000)
    │ POST /api/v1/score/{customerId}
    ▼
Spring Boot Gateway (8080)  ← Resilience4j (retry → circuit-breaker → cache → audit)
    │
    ├── Redis 7 (score cache, 30-min TTL)
    ├── PostgreSQL 16 (profiles + audit log + decisions)
    └── FastAPI ML Service (8000, internal)
         ├── Feature engineering (6 features)
         ├── Composite score (deterministic weighted formula)
         ├── GBM classifier → bucket + confidence
         ├── TreeExplainer SHAP (exact, deterministic)
         └── Diagnostic flags (EPFO, capacity, seasonality)
```

### Scoring Formula

| Feature | Weight | What it measures |
|---------|--------|-----------------|
| `payment_regularity` | 40% | Consistency across GST, EPFO, electricity, water |
| `financial_capacity_proxy` | 25% | GST turnover or electricity proxy |
| `business_longevity` | 20% | Years in operation (capped 15) with young-business floor |
| `data_coverage` | 10% | How many alt-data sources present |
| `evidence_confidence` | 5% | Consistency across payment signals |

**Buckets**: disciplined ≥ 0.80, yes-to-go ≥ 0.65, non-disciplined ≥ 0.45, no-to-go < 0.45

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/score/{customerId}` | Score a customer |
| GET | `/api/v1/score/audit/{customerId}` | Audit history |
| GET | `/api/v1/customers/{customerId}/profile` | Profile + data completeness |
| POST | `/api/v1/decisions` | Submit underwriter decision |
| GET | `/api/v1/decisions/{customerId}` | Decision history |
| GET | `/api/v1/decisions/pending` | Pending reviews |
| GET | `/api/v1/score/health` | Health check |

---

## Demo Profiles

| ID | Business | Type | Bucket |
|----|----------|------|--------|
| CUST00042 | Ramesh Traders | Manufacturing | yes-to-go (blank-slate) |
| CUST00011 | Shakti Manufacturing | Manufacturing | disciplined |
| CUST00087 | Kaveri Logistics | Logistics | non-disciplined |
| CUST00134 | Anand Cold Chain | Trading | no-to-go |

---

## Repository Structure

```
backend/
  common/       Shared DTOs, JPA entities, Flyway migrations, Redis, security
  customer/     Customer profile lookup
  feature/      Feature module (passive — FE lives in ML service)
  scoring/      Core scoring service + controllers
  audit/        Audit log queries
ml-service/
  app/          FastAPI entrypoint, router, feature engineering, model loader, checks
  tests/        Pytest suite
frontend/
  src/          React SPA — App, Layout, SearchBar, ScoreOverview, AuditTrail, ScoreDetail
docker/
  docker-compose.yml       Development compose (builds from source)
  docker-compose.prod.yml  Production compose (pulls pre-built images)
synthetic-data/
  generate_profiles.py     350-customer profile generator
  label_profiles.py        Composite score → bucket assigner
  seed.py                  Idempotent DB seeding
docs/
  architecture.md          Full system architecture
  developer-guide.md       Setup, CLI usage, troubleshooting
  scoring-logic.md         Complete scoring formulas
  stack-decisions.md       Technology rationale and design decisions
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| ML model | scikit-learn GradientBoostingClassifier + GradientBoostingRegressor |
| Model serving | FastAPI (Python 3.11) |
| API gateway | Spring Boot 3.3 (Java 21) |
| Resilience | Resilience4j (circuit breaker + retry + time limiter) |
| Database | PostgreSQL 16 + Flyway |
| Cache | Redis 7 |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Explainability | SHAP (TreeExplainer — exact, deterministic) |
| Containerisation | Docker Compose + GitHub Container Registry |
| CI/CD | GitHub Actions |

---

## CLI

```bash
python cli.py dev        # Full project startup (7 stages)
python cli.py status     # Repository health report
python cli.py test       # Run all test suites
python cli.py commit     # Quality-gated commit
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | Full system architecture, components, data flow, API contracts, DB schema |
| [Developer Guide](docs/developer-guide.md) | Setup instructions, CLI usage, configuration, troubleshooting |
| [Scoring Logic](docs/scoring-logic.md) | Complete scoring formulas, feature engineering, SHAP, edge cases |
| [Stack & Decisions](docs/stack-decisions.md) | Technology rationale, design decisions, trade-offs, roadmap |

---

## License

All Rights Reserved. © 2026 DistributedMind.

This project is submitted as part of IDBI Innovate 2026. No license is granted for commercial use, reproduction, or distribution without explicit permission.
