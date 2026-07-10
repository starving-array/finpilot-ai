# System Architecture

**FinPilot AI — Team DistributedMind**
**IDBI Innovate 2026 - Track 03**

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview](#2-system-overview)
3. [Frontend Architecture](#3-frontend-architecture)
4. [Backend Gateway Architecture](#4-backend-gateway-architecture)
5. [ML Service Architecture](#5-ml-service-architecture)
6. [End-to-End Request Flow](#6-end-to-end-request-flow)
7. [Database Schema](#7-database-schema)
8. [API Contracts](#8-api-contracts)
9. [Exception Hierarchy](#9-exception-hierarchy)
10. [Circuit Breaker & Resilience](#10-circuit-breaker--resilience)
11. [Redis Caching Strategy](#11-redis-caching-strategy)
12. [Infrastructure & Docker](#12-infrastructure--docker)
13. [Security & Data Confidentiality](#13-security--data-confidentiality)
14. [CI/CD Pipeline](#14-cicd-pipeline)

---

## 1. Executive Summary

A 3-tier microservices system that scores Indian MSMEs for creditworthiness using alternative data (electricity, EPFO, water, fuel) when traditional data (GST, UPI) is sparse or absent.

### Key Capabilities

- Score a customer via `POST /api/v1/score/{customerId}` with circuit-breaker resilience
- View audit trail via `GET /api/v1/score/audit/{customerId}`
- Submit underwriter decisions via `POST /api/v1/decisions`
- View customer profile with data completeness score
- Health monitoring via `/api/v1/score/health`

### Output

- **GBM classification**: 4 buckets (disciplined / yes-to-go / non-disciplined / no-to-go)
- **Composite score**: Deterministic 0-1 weighted formula (model-independent)
- **SHAP explanations**: Per-feature attribution for every prediction (6 features)
- **Diagnostic flags**: EPFO plausibility, loan-to-capacity, seasonality

---

## 2. System Overview

### Architecture Diagram

```
                     +-------------------+
                     |   React SPA       |
                     |   :5173 / :3000   |
                     +--------+----------+
                              | HTTP JSON
                              v
               +------------------------------+
               |  Spring Boot Gateway :8080   |
               |                              |
               |  ScoreController             |
               |  DecisionService             |
               |  AuditController             |
               |                              |
               |  Resilience4j                |
               |  Circuit Breaker             |
               |  + Retry + Time Limiter      |
               +--------------+---------------+
                              |
            +-----------------+-----------------+
            |                 |                 |
            v                 v                 v
     +-----------+     +-----------+     +-----------+
     |  Redis 7  |     |PostgreSQL |     | FastAPI   |
     |  (cache)  |     | 16        |     | :8000     |
     |           |     | profiles  |     |(internal) |
     | score:{id}|     | audit_log |     +-----------+
     | TTL 30min |     | decisions |     | POST /predict
     +-----------+     +-----------+     | GET /health
                                         | GET /models/{v}/metadata
                                         +-----------+
                                                      |
                                                      v
                                         +-----------------------+
                                         | ModelManager singleton|
                                         | (loaded at startup)   |
                                         |                       |
                                         | GBM GradientBoosting  |
                                         | SHAP KernelExplainer  |
                                         | (20 background smpls) |
                                         +-----------------------+
```

### Layers

| Layer | Tech | Port | Role |
|-------|------|------|------|
| **Presentation** | React 18 + TypeScript + Vite 5 | 5173 (dev) / 3000 (prod) | Underwriter SPA with 6-state machine |
| **Gateway** | Spring Boot 3.3 (Java 21) | 8080 | REST API, orchestration, resilience, caching |
| **ML Service** | FastAPI (Python 3.11) | 8000 (internal) | Feature engineering, model inference, SHAP |
| **Cache** | Redis 7 | internal | Score response cache (30-min TTL) |
| **Database** | PostgreSQL 16 | internal | Customer profiles, audit log, decisions |

### Module Structure (Backend)

```
backend/
  common/        Shared DTOs, enums, JPA entities, Flyway migrations (V1-V10),
                 Redis config, security (JWT), observability (Micrometer)
  customer/      Customer profile lookup
  feature/       Feature module (passive - FE lives in ML service)
  scoring/       Core scoring service: ScoreController, ScoringClientService,
                 DecisionService, custom exceptions, DTOs
  audit/         Audit log queries
```

---

## 3. Frontend Architecture

### 3.1 Tech Stack

- **React 18** with functional components and hooks
- **TypeScript** - interfaces match backend DTOs exactly
- **Vite 5** - dev server + bundler
- **Tailwind CSS 3** - utility-first styling
- **TanStack React Query** - not actually used in current code (plain fetch)

### 3.2 State Machine (`App.tsx`)

A 6-state machine (not 7 - `idle`, `loading`, `success`, `stale`, `notFound`, `serviceDegraded`, `error`):

```
idle -> loading -> success (source=live|cache-hit)
                 -> stale   (source=cache-fallback)
                 -> notFound (404)
                 -> serviceDegraded (503)
                 -> error    (500/network)
All terminal states -> idle (user searches again)
```

### 3.3 Component Tree

```
App.tsx
  +-- Layout.tsx
       +-- SearchBar.tsx          (always, includes curated ID dropdown + business type filter)
       +-- ScoreOverview.tsx      (status=success|stale: bucket badge, confidence, flags)
       +-- ScoreDetail.tsx        (status=success|stale: SHAP reasons, feature values)
       +-- AuditTrail.tsx         (lazy-loaded on expand)
       +-- Stale banner           (inline in App.tsx when source=cache-fallback)
```

### 3.4 API Client (`api/client.ts`)

6 exported functions:

| Function | Method | Endpoint |
|----------|--------|----------|
| `fetchScore(customerId)` | POST | `/api/v1/score/{id}` |
| `fetchAudit(customerId)` | GET | `/api/v1/score/audit/{id}` |
| `fetchCustomerProfile(customerId)` | GET | `/api/v1/customers/{id}/profile` |
| `submitDecision(req)` | POST | `/api/v1/decisions` |
| `fetchDecisions(customerId)` | GET | `/api/v1/decisions/{id}` |
| `fetchPendingReviews()` | GET | `/api/v1/decisions/pending` |

Custom error classes: `NotFoundError` (404), `ServiceDegradedError` (503), `ApiError` (other)

### 3.5 TypeScript Types (`types/index.ts`)

Key interfaces matching backend DTOs exactly:

```typescript
ScoreResponse {
  customerId, bucket, probability, composite_score,
  features, flags, shap_explanation, model_version,
  source, stale_since, request_id, scored_at,
  business_name, owner_name, business_type, state,
  requested_loan_amount
}

Flags {
  is_blank_slate,
  epfo_plausibility: { flag, message, implied_wage, employee_count },
  capacity_flag: { flag, message, loan_to_revenue_ratio, source },
  seasonality_flags: { fuel: SeasonalityFlag, electricity: SeasonalityFlag }
}

ShapExplanation {
  shap_values, base_value, feature_ranking: FeatureRank[],
  human_readable_summary
}
```

Curated demo IDs: `CUST00042`, `CUST00011`, `CUST00087`, `CUST00134`

---

## 4. Backend Gateway Architecture

### 4.1 Controllers

#### ScoreController (`scoring/controller/ScoreController.java:70`)

| Method | Path | Service Call | Description |
|--------|------|--------------|-------------|
| POST | `/api/v1/score/{customerId}` | `ScoringClientService.score()` | Full scoring pipeline |
| GET | `/api/v1/score/audit/{customerId}` | `ScoringClientService.getAuditHistory()` | Historical scores |
| GET | `/api/v1/customers/{customerId}/profile` | `ScoringClientService.getCustomerProfile()` | Profile + data completeness |
| POST | `/api/v1/decisions` | `DecisionService.submitDecision()` | Underwriter decision |
| GET | `/api/v1/decisions/{customerId}` | `DecisionService.getDecisions()` | Decision history |
| GET | `/api/v1/decisions/pending` | `DecisionService.getPendingReviews()` | REVIEW decisions queue |
| GET | `/api/v1/score/health` | - | Health check |

### 4.2 ScoringClientService (`scoring/service/ScoringClientService.java:442`)

Annotated with Resilience4j:

```java
@Retry(name = "scoringService", fallbackMethod = "fallbackAfterRetry")
@CircuitBreaker(name = "scoringService", fallbackMethod = "fallbackAfterCircuitBreaker")
public ScoreResponse score(String customerId)
```

**Full score flow:**

1. `profileRepo.findByCustomerId(customerId)` -> JPA query
2. `buildPredictRequest(profile)` -> Map with 16 fields + business_type
3. HTTP POST to `{ml-service-url}/predict` (Java 11 HttpClient, HTTP 1.1)
4. `parseMlResponse(body)` -> Jackson reads JSON tree into internal `MlResult` record
5. Build `ScoreResponse` with `source="live"`
6. `persistAudit(result, mlResult)` -> INSERT into `audit_log_v2`
7. `cacheResult(result)` -> Redis SETEX with 30-min TTL (non-fatal on failure)
8. Return `ScoreResponse` to controller

**ML response parsing** (`parseMlResponse:280-311`):
- Extracts `customer_id`, `bucket`, `probability`, `composite_score`, `model_version`
- Parses `features` map
- Parses `flags` structure (is_blank_slate, epfo_plausibility, capacity_flag, seasonality_flags)
- Parses `shap_explanation` if present
- Returns `MlResult` record

**Customer profile** (`getCustomerProfile:132-164`):
- Counts non-null fields from 16 possible fields
- Returns `data_completeness` fraction (0.0-1.0)

### 4.3 DecisionService (`scoring/service/DecisionService.java:64`)

| Method | Description |
|--------|-------------|
| `submitDecision(request)` | Validates customer exists, creates `UnderwriterDecision` entity, saves |
| `getDecisions(customerId)` | Returns all decisions for a customer |
| `getPendingReviews()` | Returns all `REVIEW` decisions (manual underwriting queue) |

### 4.4 ScoreResponse DTO (`scoring/dto/ScoreResponse.java:78`)

Java record with `@JsonProperty` annotations for snake_case/camelCase mapping:

```java
public record ScoreResponse(
    String customerId,                    // camelCase for frontend
    @JsonProperty("composite_score") double compositeScore,
    @JsonProperty("model_version") String modelVersion,
    @JsonProperty("stale_since") Instant staleSince,
    @JsonProperty("scored_at") Instant scoredAt,
    @JsonProperty("business_name") String businessName,
    @JsonProperty("owner_name") String ownerName,
    @JsonProperty("business_type") String businessType,
    @JsonProperty("requested_loan_amount") Double requestedLoanAmount,
    ...
) {}
```

Inner records: `Flags`, `EpfoPlausibilityFlag`, `CapacityFlag`, `SeasonalityFlags`, `SeasonalityFlag`, `ShapExplanation`, `FeatureRank`

### 4.5 Configuration (`application.yml` in `common/`)

Key settings:
- Datasource: PostgreSQL via HikariCP (min 2, max 8)
- JPA: `ddl-auto: validate` (Flyway manages schema)
- Redis: Lettuce connection pool
- Resilience4j: circuit breaker, time limiter, retry
- CORS: `localhost:5173, localhost:3000`

---

## 5. ML Service Architecture

### 5.1 Entry Point (`main.py`)

```python
@asynccontextmanager
async def lifespan(app):
    load_model()   # ModelManager.load() - loads .joblib + creates SHAP explainer
    yield
```

- CORS middleware: `allow_origins=["*"]` (internal only)
- Timing middleware: `X-Process-Time` header
- Router includes: `/predict`, `/health`, `/models/{version}/metadata`

### 5.2 ModelManager (`model_loader.py`)

Singleton managing the model lifecycle:

```python
class ModelManager:
    def load(self, path=None):
        artifact = joblib.load(path or settings.model_path)
        if isinstance(artifact, dict):
            self._model = artifact["model"]
            self.model_version = artifact.get("version", "0.0.0")
            self._metadata = artifact.get("metadata", {})
        else:
            self._model = artifact  # Legacy flat .joblib
            self.model_version = "1.0.0"

        # Optional checksum verification
        if settings.model_checksum:
            verify_sha256(path, settings.model_checksum)

        self._load_explainer()

    def _load_explainer(self):
        background = np.random.default_rng(42).random((20, 6)) * 0.5 + 0.5
        self._explainer = shap.KernelExplainer(self._model.predict_proba, background)
```

### 5.3 Inference Flow (`router.py`)

```
POST /predict {customer_id, gst_registered, ..., business_type}
  |
  +-> Validate business_type (422 if invalid)
  +-> compute_all_features(16 fields) -> (features dict, flags dict)
  |     is_blank_slate() -> bool
  |     compute_payment_regularity()
  |     compute_financial_capacity_proxy()
  |     compute_business_longevity()
  |     compute_data_coverage()
  |     compute_evidence_confidence()
  |     check_epfo_plausibility() -> flag
  |     compute_capacity_flag() -> flag
  |     get_volatility_flag() -> fuel + electricity flags
  |
  +-> feature_vector = [[f1, f2, f3, f4, f5, f6]]  # (1, 6)
  +-> model.predict_proba(fv)  -> [p0, p1, p2, p3]
  +-> model.predict(fv)        -> pred_idx (0-3)
  +-> bucket = CATEGORY_ORDER[pred_idx]
  +-> probability = proba[pred_idx]
  +-> composite_score = weighted formula (5 features, not blank_slate_flag)
  +-> compute_shap(explainer, model, fv, blank_slate, business_type)
  |
  +-> Assemble ScoreResult -> PredictResponse
```

### 5.4 Feature Engineering Module Files

| File | Responsibility | Lines |
|------|---------------|-------|
| `feature_engineering.py` | 6 feature computations + `compute_all_features()` | 261 |
| `business_weights.py` | Sector weight lookup + `apply_signal_weights()` | 20 |
| `seasonality.py` | Volatility flag per sector/metric | 25 |
| `epfo_checks.py` | EPFO plausibility (implied wage) | 56 |
| `capacity_flag.py` | Loan-to-revenue capacity | 50 |
| `constants.py` | ALL domain constants (15 domain groups A-O) | 203 |
| `config.py` | Pydantic Settings (env-configurable) | 34 |

### 5.5 Constants Organization (`constants.py`)

All tunable parameters in one file, organized by domain:
- **A**: Financial capacity (elec percentiles, thresholds)
- **B**: Payment regularity (delay denominators, smoothing)
- **C**: Business longevity (scale years, floor params)
- **D**: Data coverage (group weights)
- **E**: Blank-slate thresholds (per business type)
- **F**: Composite score weights
- **G**: Signal weights (sector x signal matrix)
- **H**: Label buckets (training thresholds, risk map)
- **I**: Seasonality (volatility ranges)
- **J**: Loan capacity (ratio caps)
- **K**: EPFO (wage limits, rates)
- **L**: SHAP (feature sources)
- **M**: Model training (Optuna, split ratios)
- **N**: Validation gates (precision/recall targets)
- **O**: Risk signals (label validation penalties/bonuses)

### 5.6 Schemas (`schemas.py`)

Pydantic models for request/response:

```
PredictRequest:   customer_id, 16 fields, business_type
PredictResponse:  status, result (ScoreResult), request_id
ScoreResult:      customer_id, bucket, probability, composite_score,
                  features, flags, shap_explanation, model_version,
                  traditional_signal_contribution, alternative_signal_contribution
FeatureFlags:     is_blank_slate, epfo_plausibility, capacity_flag, seasonality_flags
ShapExplanation:  shap_values, base_value, feature_ranking[FeatureRank],
                  human_readable_summary, traditional/alternative_signal_contribution
FeatureRank:      feature_name, value, shap_value, rank, direction,
                  business_description, source
ErrorResponse:    status, error_code, message, details, request_id
ModelMetadata:    model_version, training_date, dataset_hash, metrics,
                  feature_schema, artifact_path, deployed_at/by, status
```

---

## 6. End-to-End Request Flow

### Scoring a Customer

```
Browser -> POST /api/v1/score/CUST00042
  -> [Spring Boot] ScoreController.score()
    -> [ScoringClientService] profileRepo.findByCustomerId("CUST00042")
    -> [PostgreSQL] SELECT * FROM customer_profile WHERE customer_id='CUST00042'
    -> Build predict request map (16 fields)
    -> [Resilience4j] @Retry @CircuitBreaker
      -> HTTP POST http://ml-service:8000/predict (Java 11 HttpClient)
        -> [FastAPI] validate business_type
        -> [FE] is_blank_slate(gst, upi, business_type) -> bool
        -> [FE] compute_payment_regularity(gst, epfo, elec, water, bt) -> float
        -> [FE] compute_financial_capacity_proxy(turnover, elec, bt) -> float
        -> [FE] compute_business_longevity(years, payment_reg, coverage) -> float
        -> [FE] compute_data_coverage(elec, epfo, water, fuel) -> float
        -> [FE] compute_evidence_confidence(gst, epfo, elec, water) -> float
        -> [FE] assemble flags: epfo_plausibility + capacity + seasonality
        -> [Model] feature_vector -> predict_proba -> predict
        -> [SHAP] KernelExplainer.shap_values -> rank 6 features
        -> return ScoreResult JSON
    <- Parse ML response (Jackson)
    -> [Redis] SETEX score:CUST00042 TTL=1800
    -> [PostgreSQL] INSERT INTO audit_log_v2 (...)
    <- return ScoreResponse HTTP 200 { source:"live", ... }
  -> [React] status="success", render ScoreOverview + ScoreDetail + AuditTrail
```

### Fallback Flow (Circuit Open)

```
Gateway detects circuit OPEN
  -> fallbackAfterCircuitBreaker(customerId, throwable)
    -> tryCacheFallback(customerId)
      -> Redis GET score:CUST00042
        -> HIT: return ScoreResponse(source="cache-hit")
        -> MISS: auditRepo.findByCustomerIdOrderByScoredAtDesc(customerId)
          -> FOUND: return ScoreResponse(source="cache-fallback", staleSince=scoredAt)
          -> NOT FOUND: throw ScoringServiceUnavailableException -> HTTP 503
```

### Audit Trail Flow

```
Browser -> GET /api/v1/score/audit/CUST00042
  -> auditRepo.findByCustomerIdOrderByScoredAtDesc(CUST00042)
  -> For each AuditLogV2 entity:
       deserialize JSONB fields (shap_reasons, capacity_flag, epfo_flag, seasonality_flags)
       map to ScoreResponse with source="cache-fallback"
  -> Return List<ScoreResponse> (empty array if no history)
```

---

## 7. Database Schema

### Active Tables (Generation 2: V8-V10)

#### V8: `customer_profile`
```sql
CREATE TABLE customer_profile (
    customer_id                          VARCHAR(20) PRIMARY KEY,
    business_name                        VARCHAR(200) NOT NULL,
    owner_name                           VARCHAR(200),
    business_type                        VARCHAR(50) NOT NULL,
    state                                VARCHAR(50),
    years_in_operation                   NUMERIC(4,1),
    gst_registered                       BOOLEAN NOT NULL DEFAULT FALSE,
    gst_monthly_turnover_avg             NUMERIC(14,2),
    gst_filing_regularity                NUMERIC(3,2),
    upi_monthly_txn_count                INTEGER,
    upi_monthly_txn_value                NUMERIC(14,2),
    electricity_monthly_units_avg        NUMERIC(10,2),
    electricity_payment_delay_days_avg   NUMERIC(6,2),
    epfo_contribution_regularity         NUMERIC(3,2),
    epfo_employee_count                  INTEGER,
    epfo_contribution_amount             NUMERIC(14,2),
    water_monthly_consumption_kl         NUMERIC(10,2),
    water_payment_delay_days_avg         NUMERIC(6,2),
    fuel_monthly_spend_avg               NUMERIC(14,2),
    fuel_spend_volatility                NUMERIC(5,2),
    requested_loan_amount                NUMERIC(14,2),
    is_blank_slate                       BOOLEAN NOT NULL DEFAULT FALSE,
    data_completeness_score              NUMERIC(3,2),
    created_at                           TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX idx_cp_business_type ON customer_profile (business_type);
CREATE INDEX idx_cp_blank_slate ON customer_profile (is_blank_slate);
```

#### V9: `audit_log_v2`
```sql
CREATE TABLE audit_log_v2 (
    id               BIGSERIAL PRIMARY KEY,
    customer_id      VARCHAR(20) NOT NULL REFERENCES customer_profile(customer_id),
    bucket           VARCHAR(20) NOT NULL,
    confidence       NUMERIC(5,4),
    blank_slate_flag BOOLEAN NOT NULL DEFAULT FALSE,
    model_version    VARCHAR(50) NOT NULL,
    shap_reasons     JSONB NOT NULL DEFAULT '{}',
    capacity_flag    JSONB DEFAULT '{}',
    epfo_flag        JSONB DEFAULT '{}',
    seasonality_flags JSONB DEFAULT '{}',
    source           VARCHAR(20) NOT NULL,
    scored_at        TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX idx_al_customer_id ON audit_log_v2 (customer_id);
CREATE INDEX idx_al_scored_at ON audit_log_v2 (scored_at DESC);
```

#### V10: `underwriter_decision`
```sql
CREATE TABLE underwriter_decision (
    id          BIGSERIAL PRIMARY KEY,
    customer_id VARCHAR(20) NOT NULL REFERENCES customer_profile(customer_id),
    decision    VARCHAR(20) NOT NULL CHECK (decision IN ('APPROVE', 'REVIEW', 'REJECT')),
    remarks     TEXT,
    reviewer    VARCHAR(100) NOT NULL DEFAULT 'underwriter',
    created_at  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX idx_ud_decision ON underwriter_decision (decision);
CREATE INDEX idx_ud_customer_id ON underwriter_decision (customer_id);
```

### Legacy Tables (Generation 1: V1-V7)

| Migration | Table | Purpose |
|-----------|-------|---------|
| V1 | `customer` | UUID PK, JSONB traditional/alternative data |
| V2 | `feature_snapshot` | Historical feature vectors |
| V3 | `prediction` | Immutable prediction records with hash chain |
| V4 | `audit_log` | Legacy audit trail with hash chain linking |
| V5 | `model_metadata` | Model version tracking |
| V6 | `business_rule` | JSON-based rule engine (5 seed rules) |
| V7 | `audit_chain_verification` | Audit integrity verification function |

---

## 8. API Contracts

### 8.1 FastAPI (Internal)

#### POST /predict

Request:
```json
{
  "customer_id": "CUST00042",
  "business_type": "manufacturing",
  "years_in_operation": 3.5,
  "gst_registered": false,
  "gst_monthly_turnover_avg": null,
  "gst_filing_regularity": null,
  "upi_monthly_txn_count": null,
  "upi_monthly_txn_value": null,
  "electricity_monthly_units_avg": 2150.0,
  "electricity_payment_delay_days_avg": 3.2,
  "epfo_contribution_regularity": 0.91,
  "epfo_employee_count": 8,
  "epfo_contribution_amount": 28800.0,
  "water_monthly_consumption_kl": 22.5,
  "water_payment_delay_days_avg": 1.0,
  "fuel_monthly_spend_avg": 12000.0,
  "fuel_spend_volatility": 0.18,
  "requested_loan_amount": 500000.0
}
```

Response 200:
```json
{
  "status": "success",
  "result": {
    "customer_id": "CUST00042",
    "bucket": "yes-to-go",
    "probability": 0.9982,
    "composite_score": 0.8234,
    "features": {
      "payment_regularity": 2.8,
      "financial_capacity_proxy": 0.61,
      "business_longevity": 0.50,
      "data_coverage": 1.0,
      "evidence_confidence": 0.83,
      "is_blank_slate_flag": 1.0
    },
    "flags": {
      "is_blank_slate": true,
      "epfo_plausibility": {
        "flag": "plausible",
        "message": "EPFO data is plausible (implied wage Rs 15,000)",
        "implied_wage": 15000.0,
        "employee_count": 8
      },
      "capacity_flag": {
        "flag": "normal",
        "message": "Loan amount is well within capacity (0.3x annual gst)",
        "loan_to_revenue_ratio": 0.3,
        "source": "gst"
      },
      "seasonality_flags": {
        "fuel": {"flag": "normal", "message": "fuel volatility within expected range"},
        "electricity": {"flag": "normal", "message": "electricity volatility within expected range"}
      }
    },
    "shap_explanation": {
      "shap_values": {"payment_regularity": 0.34, ...},
      "base_value": 1.2,
      "feature_ranking": [
        {"feature_name": "payment_regularity", "value": 2.8, "shap_value": 0.34,
         "rank": 1, "direction": "positive",
         "business_description": "Consistent manufacturing sector payment behavior...",
         "source": "alternative"}
      ],
      "human_readable_summary": "Assessment heavily relies on alternative data...",
      "traditional_signal_contribution": 0.12,
      "alternative_signal_contribution": 0.88
    },
    "model_version": "2.0.8",
    "traditional_signal_contribution": 0.12,
    "alternative_signal_contribution": 0.88
  },
  "request_id": "a1b2c3d4"
}
```

Error 422:
```json
{"status": "error", "error_code": "INVALID_PROFILE_DATA", "message": "Invalid business_type: invalid", "request_id": "..."}
```

Error 500:
```json
{"status": "error", "error_code": "PREDICTION_FAILED", "message": "Error details...", "request_id": "..."}
```

#### GET /health

```json
{"status": "UP", "model_version": "2.0.8", "model_loaded": true, "shap_loaded": true}
```

#### GET /models/{version}/metadata

```json
{"model_version": "2.0.8", "training_date": "...", "dataset_hash": "...",
 "metrics": {"train_macro_f1": 0.92, ...}, "feature_schema": [...],
 "artifact_path": "/app/models/model_2.0.8.joblib",
 "deployed_at": "...", "deployed_by": "system", "status": "active"}
```

### 8.2 Gateway (External)

#### POST /api/v1/score/{customerId}

Response 200 (live/cache-hit):
```json
{
  "customerId": "CUST00042",
  "bucket": "yes-to-go",
  "probability": 0.9982,
  "composite_score": 0.8234,
  "features": {"payment_regularity": 2.8, ...},
  "flags": {
    "is_blank_slate": true,
    "epfo_plausibility": {"flag": "plausible", "message": "...", "implied_wage": 15000.0, "employee_count": 8},
    "capacity_flag": {"flag": "normal", "loan_to_revenue_ratio": 0.3, "source": "gst", "message": "..."},
    "seasonality_flags": {"fuel": {...}, "electricity": {...}}
  },
  "shap_explanation": {...},
  "model_version": "2.0.8",
  "source": "live",
  "stale_since": null,
  "request_id": "a1b2c3d4",
  "scored_at": "2026-07-09T10:15:30Z",
  "business_name": "Shri Enterprises",
  "owner_name": "Amit Sharma",
  "business_type": "manufacturing",
  "state": "Maharashtra",
  "requested_loan_amount": 500000.0
}
```

Response 200 (cache-fallback):
```json
{
  "customerId": "CUST00042",
  "bucket": "yes-to-go",
  "probability": 0.9982,
  "composite_score": 0.0,
  "features": {},
  "flags": {"is_blank_slate": true, "epfo_plausibility": {...}, "capacity_flag": {...}, "seasonality_flags": {...}},
  "shap_explanation": null,
  "model_version": "2.0.8",
  "source": "cache-fallback",
  "stale_since": "2026-07-09T09:40:00Z",
  "request_id": "",
  "scored_at": "2026-07-09T09:40:00Z",
  "business_name": "",
  "owner_name": null,
  "business_type": null,
  "state": null,
  "requested_loan_amount": null
}
```

Error responses:
```json
{"error": "CUSTOMER_NOT_FOUND", "customerId": "CUST99999", "message": "Customer profile not found: CUST99999", "timestamp": "..."}
{"error": "SCORING_UNAVAILABLE", "message": "Scoring unavailable for CUST00042...", "retryAfterSeconds": 30, "timestamp": "..."}
{"error": "SCORING_TIMEOUT", "message": "ML service timed out for CUST00042", "timestamp": "..."}
{"error": "INVALID_PROFILE_DATA", "message": "Failed to parse ML response...", "timestamp": "..."}
{"error": "INTERNAL_ERROR", "message": "An unexpected error occurred", "timestamp": "..."}
```

#### GET /api/v1/score/audit/{customerId}

```json
[
  {
    "customerId": "CUST00042",
    "bucket": "yes-to-go",
    "probability": 0.9982,
    "composite_score": 0.0,
    "features": {},
    "flags": {...},
    "shap_explanation": null,
    "model_version": "2.0.8",
    "source": "cache-fallback",
    "stale_since": "2026-07-09T09:40:00Z",
    "request_id": "",
    "scored_at": "2026-07-09T09:40:00Z",
    "business_name": "",
    "owner_name": null,
    "business_type": null,
    "state": null,
    "requested_loan_amount": null
  }
]
```

Returns empty array `[]` if no history.

#### GET /api/v1/customers/{customerId}/profile

```json
{
  "customer_id": "CUST00042",
  "business_name": "Shri Enterprises",
  "owner_name": "Amit Sharma",
  "business_type": "manufacturing",
  "state": "Maharashtra",
  "years_in_operation": 3.5,
  "requested_loan_amount": 500000.0,
  "is_blank_slate": true,
  "data_completeness": 0.6875
}
```

---

## 9. Exception Hierarchy

```
FinancialHealthException (abstract, extends RuntimeException)
+-- CustomerNotFoundException            -> HTTP 404
+-- ScoringServiceUnavailableException   -> HTTP 503
+-- ScoringServiceTimeoutException       -> HTTP 504
+-- InvalidProfileDataException          -> HTTP 422
+-- AuditPersistenceException            -> HTTP 500 (logged only, score still returned)
```

**GlobalExceptionHandler** (`@ControllerAdvice`):
- Catches all exceptions
- Never leaks exception messages to client (`"An unexpected error occurred"`)
- Logs real error server-side with full stack trace

---

## 10. Circuit Breaker & Resilience

### 10.1 Resilience4j Stack

| Layer | Config | Behaviour |
|-------|--------|-----------|
| **Time Limiter** | 4s timeout | Cancels long-running requests |
| **Retry** | 2 attempts, 500ms wait | Retries transient failures (IOException, SocketTimeoutException) |
| **Circuit Breaker** | COUNT_BASED, 10-call sliding window, 50% failure rate threshold, 30s open wait | Prevents cascading failures |

### 10.2 Fallback Chain

```
1. Service call succeeds -> return "live", no fallback needed

2. Timeout (>4s, circuit still CLOSED) -> HTTP 504 SCORING_TIMEOUT
   No fallback on timeout -- surface performance issue visibly

3. Circuit OPEN or retries exhausted:
   a. Redis GET score:{customerId}
      -> HIT: return "cache-hit"
      -> MISS: continue
   b. PostgreSQL audit_log_v2 most recent entry
      -> FOUND: return "cache-fallback" with staleSince
      -> NOT FOUND: HTTP 503 SCORING_UNAVAILABLE
```

### 10.3 Resilience4j Config

```yaml
resilience4j:
  circuitbreaker:
    scoringService:
      sliding-window-type: COUNT_BASED
      sliding-window-size: 10
      failure-rate-threshold: 50
      wait-duration-in-open-state: 30s
      permitted-number-of-calls-in-half-open-state: 3
      automatic-transition-from-open-to-half-open-enabled: true
  timelimiter:
    scoringService:
      timeout-duration: 4s
      cancel-running-future: true
  retry:
    scoringService:
      max-attempts: 2
      wait-duration: 500ms
```

---

## 11. Redis Caching Strategy

### Cache-Aside Pattern

```
READ:  GET score:{customerId} -> if HIT return else call ML service
WRITE: SETEX score:{customerId} EX 1800 after successful ML response
```

| Key Pattern | TTL | Content | Failure Handling |
|-------------|-----|---------|------------------|
| `score:{customerId}` | 30 min | JSON serialized `ScoreResponse` | Logged as warning, non-fatal |

### Stale Fallback

Two-stage approach when circuit is OPEN:
1. `GET score:{customerId}` -- if key exists (within TTL), return as `cache-hit`
2. If expired, query `audit_log_v2` for most recent row -> return as `cache-fallback` with `staleSince`

Audit log doubles as persistence layer for stale reads -- no second Redis key needed.

---

## 12. Infrastructure & Docker

### 12.1 Docker Compose

5 services in `docker/docker-compose.yml`:

| Service | Image | Exposed Port | Depends On (healthy) |
|---------|-------|-------------|----------------------|
| `postgres` | postgres:16-alpine | - | - |
| `redis` | redis:7-alpine | - | - |
| `backend` | custom (eclipse-temurin:21-jre) | 8080 | postgres, redis |
| `ml-service` | custom (python:3.11-slim) | - (internal) | redis |
| `frontend` | custom (nginx:alpine) | 3000 | backend |

Named volumes: `postgres-data`, `redis-data`, `ml-models`

### 12.2 CLI Tool (`cli.py`)

| Command | Stages | Purpose |
|---------|--------|---------|
| `python cli.py dev` | 7 steps: env check -> infra -> backend -> seed -> train -> ML -> frontend | One-command startup |
| `python cli.py status` | - | Health report |
| `python cli.py commit` | - | Quality-gated commit |

### 12.3 Synthetic Data Pipeline

1. `generate_profiles.py` - 350 deterministic profiles (seed=42), 30% blank-slate, 5 business types, all 16 fields + is_blank_slate
2. `label_profiles.py` - Compute composite score -> assign bucket via thresholds -> validate distribution (target: 10-50% per bucket)
3. `seed.py` - Idempotent INSERT ON CONFLICT DO NOTHING into customer_profile

---

## 13. Security & Data Confidentiality

### 13.1 Rules

1. **No raw financial figures** in any log at INFO or above
2. **Exception catch-all** never passes `exception.getMessage()` to client
3. **Redis** stores ScoreResponse (bucket, confidence, reasons) - never full profile
4. **No bulk-export endpoints** (no `GET /customers`, no `GET /score/all`)
5. **FastAPI** has no external port mapping in docker-compose.yml
6. **audit_log** is append-only - no UPDATE or DELETE in application code
7. All credentials in `.env` only, gitignored
8. Treat synthetic data as if real from Day 1

### 13.2 Implementation

- Spring Security includes JWT filter and rate limiting (configured but not enforced in prototype)
- `AuditPersistenceException` logged as CRITICAL but does not block score response
- Audit log deserialization uses JSONB fields stored as structured data

---

## 14. CI/CD Pipeline

GitHub Actions (`.github/workflows/ci.yml`): 4 parallel jobs

| Job | Command | Artifact |
|-----|---------|----------|
| **backend** | `mvn clean verify` | Compile + test + checkstyle |
| **ml-service** | `ruff lint` + `pytest` | Python lint + tests |
| **frontend** | `npm ci` -> `npm run lint` -> `npm run build` | TypeScript + Vite |
| **docker** | `docker compose build` | Docker images |
