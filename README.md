# Financial Health Score - Underwriter Console

**IDBI Innovate 2026 - Track 03 - Team: DistributedMinds (solo)**

AI-assisted financial health scoring for MSMEs with thin or alternative-only credit histories. Scores into four buckets (disciplined / yes-to-go / non-disciplined / no-to-go) using hand-crafted features from electricity, EPFO, water, and fuel data - not just GST and UPI.

---

## Quick Start

```bash
cp .env.example .env
docker compose -f docker/docker-compose.yml up -d
# Wait ~60s for health checks
curl -s -X POST http://localhost:8080/api/v1/score/CUST00042 | jq .
```

Frontend at http://localhost:3000 - enter a Customer ID or pick a demo profile.

One-command CLI alternative: `python cli.py dev`

---

## What Makes This Different

| Approach | Most Submissions | This System |
|----------|-----------------|-------------|
| **Blank-slate scoring** | Impute zeros for missing traditional data | Alt-data drives the score; blank-slate flag changes the narrative for underwriter |
| **Feature weights** | Generic weights for all business types | Business-type-aware multipliers (fuel = 1.6x for logistics, 0.4x for services) |
| **Data fairness** | Mix coverage and quality (penalizes submitting weak data) | Separated into coverage + confidence; never penalizes providing more data |
| **Explainability** | Feature importance bar chart (global) | SHAP per-prediction explanations with source tagging (standard / alternative / mixed) |
| **Resilience** | Single-point-of-failure | Circuit breaker + Redis cache + audit log fallback chain |
| **Diagnostic flags** | Score only | EPFO plausibility, loan-to-capacity, seasonality flags |

---

## Architecture Overview

```
React SPA -> Spring Boot Gateway (Resilience4j) -> FastAPI ML Service
              |-> Redis cache (30-min TTL)
              |-> PostgreSQL (profiles + audit log)
```

- **Frontend**: React 18 + TypeScript + Vite (7-state state machine)
- **Gateway**: Spring Boot 3.3 (Java 21) with Resilience4j circuit breaker
- **ML Service**: FastAPI (Python) with scikit-learn GBM + SHAP explanations
- **Cache**: Redis 7 (cache-aside pattern with stale fallback)
- **Database**: PostgreSQL 16 with Flyway migrations (V8-V10)
- **Infrastructure**: Docker Compose (5 services with health checks)

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

## Scoring Logic Summary

6 features computed from raw profile data:

| Feature | Weight | What it measures |
|---------|--------|-----------------|
| `payment_regularity` | 40% | Consistency across GST, EPFO, electricity, water |
| `financial_capacity_proxy` | 25% | GST turnover or electricity proxy |
| `business_longevity` | 20% | Years in operation (capped 15) with young-business floor |
| `data_coverage` | 10% | How many alt-data sources present |
| `evidence_confidence` | 5% | Consistency across payment signals |

**Bucket thresholds**: disciplined >= 0.70, yes-to-go >= 0.50, non-disciplined >= 0.30, no-to-go < 0.30

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

## Documentation

Detailed documentation is available in the `docs/` directory:

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | Full system architecture, components, data flow, API contracts, database schema |
| [Developer Guide](docs/developer-guide.md) | Setup instructions, CLI usage, configuration, troubleshooting |
| [Scoring Logic](docs/scoring-logic.md) | Complete scoring formulas, feature engineering, SHAP, edge cases |
| [Stack & Decisions](docs/stack-decisions.md) | Technology rationale, design decisions, trade-offs, roadmap |

---

## Known Limitations

- **Synthetic data**: 350 generated profiles - not real customer data. Retrain on IDBI sandbox data post-shortlist
- **SHAP KernelExplainer**: ~30s per prediction (TreeExplainer not fully compatible with multi-class GBM in current SHAP version)
- **No authentication**: Prototype assumes pre-authenticated corporate network
- **Single-region**: All services on one host
- **Dockerfiles run as root**: Acceptable for prototype, add USER directive for production
