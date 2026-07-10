# Technology Stack & Design Decisions

**FinPilot AI — Team DistributedMind**

---

## Table of Contents

1. [Technology Stack](#1-technology-stack)
2. [Why Each Technology](#2-why-each-technology)
3. [Design Decisions](#3-design-decisions)
4. [Trade-offs & Alternatives Considered](#4-trade-offs--alternatives-considered)
5. [Future Roadmap](#5-future-roadmap)
6. [Known Limitations](#6-known-limitations)

---

## 1. Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **ML Model** | scikit-learn GradientBoostingClassifier | 1.5+ | Classification into 4 credit buckets |
| **ML Serving** | FastAPI | 0.115+ | Model inference REST API |
| **API Gateway** | Spring Boot | 3.3.4 (Java 21) | REST API, orchestration, resilience |
| **Frontend** | React + TypeScript + Vite | React 18, Vite 5 | Underwriter SPA |
| **Database** | PostgreSQL | 16 | Customer profiles, audit log, decisions |
| **Cache** | Redis | 7 Alpine | Score response caching |
| **Resilience** | Resilience4j | Spring Cloud 2023.0.3 | Circuit breaker, retry, time limiter |
| **Containerization** | Docker Compose | latest | 5-service orchestration |
| **CI/CD** | GitHub Actions | - | Lint, test, build on push |
| **Explainability** | SHAP | 0.46+ | Per-prediction feature attribution |
| **Data Generation** | Python (custom) | 3.11+ | 350 synthetic MSME profiles |
| **Build (Backend)** | Maven | 3.9+ | Multi-module Spring Boot project |

### Dependencies

**ML Service** (`ml-service/pyproject.toml`):
```
fastapi, uvicorn, pydantic, pydantic-settings
lightgbm, shap, scikit-learn, pandas, numpy
redis, joblib, prometheus-client
```

**Frontend** (`frontend/package.json`):
```
react, react-dom, @tanstack/react-query
vite, typescript, tailwindcss, postcss, autoprefixer
```

**Backend** (`backend/pom.xml`):
```
Spring Boot 3.3.4, Spring Cloud 2023.0.3
Spring Data JPA, Spring Data Redis, Spring Security
Resilience4j, Flyway, Testcontainers
Jackson, Springdoc (OpenAPI), Micrometer + Prometheus
```

---

## 2. Why Each Technology

### ML Model: scikit-learn GBM (not XGBoost/LightGBM, not Neural Network)

**Why GBM**: Gradient Boosting Machines are the proven workhorse for tabular/structured data with feature interactions. Outperform random forests on this data type.

**Why not XGBoost/LightGBM**: scikit-learn's GBM has native SHAP TreeExplainer support, unlike LightGBM's internal SHAP implementation which has compatibility issues with multi-class. The hackathon timeline favors a working, well-understood implementation over marginal performance gains.

**Why not Neural Network**: Neural networks require significantly more data (350 profiles is insufficient), are harder to explain (SHAP works but with less reliability), and introduce unnecessary complexity for a 6-feature tabular problem.

### Model Serving: FastAPI (not Flask, not Django)

**Why FastAPI**: Async-first, Pydantic validation on request/response (reduces boilerplate), auto-generates OpenAPI docs, under 100ms inference latency for single row. Loads model once at startup (not per request).

**Why not Flask**: Synchronous by default, no built-in request validation, more boilerplate for the same result.

**Why not Django**: Heavy framework for a single-endpoint microservice. Overkill for 3 routes.

### API Gateway: Spring Boot (not Node.js Express, not Python)

**Why Spring Boot**: Handles Redis cache, PostgreSQL JPA, Resilience4j circuit breaker, and Flyway migrations in a single runtime. Battle-tested for exactly this pattern - an orchestration gateway with multiple downstream dependencies.

**Why not Node.js/Express**: Would require separate libraries for JPA-like ORM, circuit breaker, Redis client. Spring ecosystem provides all of these as first-class integrations.

**Why not Python (FastAPI as gateway)**: ML service IS FastAPI. A second Python service would share the same runtime weaknesses (GIL, memory). Java/Spring Boot is the candidate's primary language - no context-switch penalty.

### Resilience: Resilience4j (not Hystrix, not manual try-catch)

**Why Resilience4j**: Native Spring Boot integration via annotations. No extra service to deploy. Wraps only the gateway -> FastAPI call - the one unpredictable network hop.

**Why not Hystrix**: Netflix Hystrix is in maintenance mode. Resilience4j is the modern replacement with active development.

**Why not manual try-catch**: Would need to implement sliding window counters, state transitions, thread pool isolation manually. Resilience4j provides all of this with 10 lines of config.

### Cache: Redis (not Memcached, not in-memory)

**Why Redis**: Sub-millisecond lookups, built-in TTL/expiry, persisted to disk. Cache-aside pattern is simple to implement with Lettuce client.

**Why not Memcached**: No persistence, no TTL (must manage expiry manually), fewer Spring integrations.

**Why not in-memory (Caffeine/Guava)**: In-memory cache would not survive gateway restart. Redis is a separate service that persists across restarts and can serve stale fallback.

### Database: PostgreSQL (not MySQL, not MongoDB)

**Why PostgreSQL**: JSONB for storing SHAP reasons (queryable without schema changes). Flyway migrations for versioned schema evolution. Relational integrity for audit log.

**Why not MySQL**: PostgreSQL's JSONB is superior for semi-structured data. The audit log's SHAP reasons array is a natural fit for JSONB.

**Why not MongoDB**: The data model is fundamentally relational (customer profile -> audit log -> decisions). A document DB would require embedding or application-level joins.

### Frontend: React (not vanilla JS, not Vue/Angular)

**Why React**: Component structure maps directly to the 5 UI states (SearchBar, ScoreBadge, ReasonsList, CapacityFlag, AuditTrail). No routing needed (single page). TypeScript adds safety for complex response types.

**Why not vanilla JS**: A multi-component layout with state management and API integration would be significantly harder to maintain in vanilla JS.

**Why not Vue/Angular**: React is more widely used in hackathon contexts and the developer's experience is with React.

### Data Generation: Python Custom (not Faker, not external datasets)

**Why custom**: Offline/no-network safe. Faker is a convenience, not a requirement - removing the dependency means the generator runs anywhere without pip network access. All logic is deterministic (`random.seed(42)`) for reproducibility.

---

## 3. Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Frontend type** | Minimal React, no router | Single page, no routing needed; component structure maps to UI states |
| **File upload** | None - lookup only | Production data comes from API integrations, not manual entry; out of scope |
| **Blank-slate trigger** | Both GST AND UPI thin | Either-or would flag businesses with strong GST but no UPI - genuinely creditworthy |
| **Alt-data weighting** | Business-type-aware multipliers | Fuel spend is core for logistics, irrelevant for services - same weight is unfair |
| **Seasonal volatility** | CV relative to sector norm | High fuel CV for logistics is expected, not risky; absolute threshold would penalize |
| **Young business penalty** | Longevity floor at 0.50 when all 3 conditions met | Young business with complete, consistent data is less risky than old business with sparse data |
| **Data completeness** | Separated into coverage + confidence | Prevents perverse incentive of withholding weak signals |
| **EPFO plausibility** | Flag only, not model feature | Not in training data; adds underwriter transparency without distorting score |
| **Capacity flag** | Separate field, not part of score | Loan amount appropriateness is a different risk dimension from creditworthiness |
| **Circuit breaker scope** | Gateway -> FastAPI only | Postgres and Redis are local infra with connection pooling; CB adds complexity without benefit |
| **Circuit open fallback** | Stale cache -> audit_log -> 503 | Stale-but-real data is more useful than nothing; honest via staleSince |
| **Model versioning** | Filename + sidecar JSON | Zero infrastructure, audit-log compatible, survives retraining without code changes |
| **Docker health checks** | `depends_on: service_healthy` | Guarantees clean boot order; eliminates fresh-clone demo failures |
| **TLS** | Production note in README only | Internal Docker bridge network is not a realistic attack surface for prototype |
| **SHAP reasons count** | Top 7 (not 5) | With 6 features, top 5 could hide the 6th; 7 ensures all features are visible |
| **Audit log** | Append-only | Compliance requirement; compromised instance cannot rewrite history |
| **React state** | Plain useState | Five states, one fetch - no state library justified |
| **Gateway HTTP client** | Java 11 HttpClient | Avoids Apache/OkHttp dependency; sufficient for single internal call |
| **PostgreSQL port** | Exposed only for development | Removed from docker-compose for demo; internal Docker network only |
| **Label thresholds** | Stricter for training (0.84/0.78/0.70) vs production (0.70/0.50/0.30) | Model should learn to discriminate more finely than the production thresholds |

---

## 4. Trade-offs & Alternatives Considered

### Feature Engineering Location

**Chosen**: Feature engineering in the ML service (Python/FastAPI), not in the gateway.

**Trade-off**: Gateway sends raw profile data to ML service; the ML service computes features.

**Alternative considered**: Computing features in the gateway (Java) and sending pre-computed features to ML.

**Why chosen**: Single implementation of feature engineering for both training and inference (no drift). Python + Pandas is far more productive for data transformation than Java. The 16-field JSON payload is small (< 1KB).

### SHAP Explainer Type

**Chosen**: `KernelExplainer` (model-agnostic)

**Trade-off**: ~30s per prediction vs TreeExplainer's ~300ms. But KernelExplainer works with any sklearn model.

**Alternative considered**: `TreeExplainer` (model-specific, O(TLD) complexity)

**Why chosen**: KernelExplainer is the only SHAP variant that works reliably with scikit-learn's multi-class GBM across SHAP versions. TreeExplainer has version-specific compatibility issues. With 350 profiles and demo-only usage, 30s per prediction is acceptable.

### Monorepo vs Microservices

**Chosen**: Monorepo with 3 microservices

**Trade-off**: Single repository, but separate Docker images and deployable units.

**Alternative considered**: Single monolithic service (FastAPI handles everything)

**Why chosen**: Separation of concerns - the ML service is a pure inference engine that could be swapped out. The gateway handles all orchestration, caching, and resilience. A monolith would couple these concerns.

### No Authentication

**Chosen**: No auth for prototype

**Trade-off**: Anyone who can reach the gateway can score customers. Acceptable for internal demo.

**Alternative considered**: JWT-based auth with Spring Security

**Why chosen**: JWT configuration is a day of work that adds zero judged value. The prototype runs on an internal Docker network. Production note documents the requirement.

### SQL-Based Audit Trail

**Chosen**: PostgreSQL for audit log (not a separate audit service)

**Trade-off**: Audit log shares the same database as customer profiles. A compromised DB could affect both.

**Alternative considered**: Separate audit database or append-only event store

**Why chosen**: For a prototype, a separate audit database adds infrastructure complexity without proportional benefit. The append-only constraint is enforced at the application layer, not by a separate database.

---

## 5. Future Roadmap

### Phase 2 - Post-Shortlist (Real IDBI Sandbox Data)

| Work Item | Description | Priority |
|-----------|-------------|----------|
| **Retrain on real data** | The synthetic-trained model demonstrates the pipeline; retrain on IDBI sandbox profiles | Critical |
| **Calibrate sector weights** | Validate `SIGNAL_WEIGHTS` against real MSME payment outcomes from sandbox | High |
| **Confidence-driven guidance** | Use SHAP to tell underwriters which additional data would improve confidence most | Medium |
| **Model drift monitoring** | Compare prediction distributions across model versions; surface in admin view | Medium |
| **Optuna hyperparameter tuning** | Replace fixed hyperparams with automated search for production optimization | Medium |
| **Business-critical metrics** | Gate model releases on precision@low-risk, recall@high-risk, ECE calibration | High |

### Phase 3 - Production Hardening

| Work Item | Description |
|-----------|-------------|
| **TLS everywhere** | Cert-manager or Let's Encrypt for all external endpoints |
| **Authentication** | JWT/OAuth2 before the gateway |
| **Real data integration** | GSTN API, account aggregator (UPI), DISCOM APIs, EPFO API |
| **Model retraining cadence** | Monthly retraining with automated validation gates |
| **Audit log retention** | Regulatory-compliant retention policy with archival |
| **Rate limiting** | Token bucket per IP/user for gateway endpoints |
| **Read replica** | PostgreSQL read replica for audit queries (primary handles writes) |

### Phase 4 - Feature Expansion

| Work Item | Description |
|-----------|-------------|
| **Shadow model pipeline** | Offline comparison of experimental model vs champion model |
| **Feature store** | Centralized feature computation and serving layer |
| **Location-based risk** | Commercial real estate, footfall, geographic demand data |
| **Ownership scoring** | MCA/ROC filings as additional signal |
| **Co-applicant scoring** | Personal guarantor creditworthiness assessment |

---

## 6. Known Limitations

### Functional Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| **Synthetic data** (350 profiles) | Model may not generalize to real MSME data | Pipeline is designed to accept real data without code changes; retrain on IDBI sandbox post-shortlist |
| **SHAP KernelExplainer** | ~30s per prediction (vs TreeExplainer's ~300ms) | Acceptable for demo; migrate to TreeExplainer if compatible with model version |
| **No authentication** | Anyone who can reach the gateway can score customers | Prototype runs on internal Docker network; documented for production |
| **Single-region** | All services on one host | Acceptable for prototype; production would require multi-region deployment |
| **No bulk operations** | Cannot score multiple customers at once | Deliberate - no bulk-export endpoints per data confidentiality rules |

### Technical Limitations

| Limitation | Location | Details |
|------------|----------|---------|
| **Hardcoded thresholds** | `feature_engineering.py` | Should import from `config.py` (config values exist but are decorative) |
| **Dockerfiles run as root** | Multiple Dockerfiles | Acceptable for prototype; should add `USER` directive for production |
| **CORS allow_origins=["*"]** | ML service `main.py` | Should restrict to backend URL (internal network, acceptable for prototype) |
| **Error leakage** | ML service `router.py` | Uses `str(e)` in error responses; should log and return generic message |
| **Dead code** | `predictor.py`, `training/feature_engineering.py` | Legacy 17-feature pipeline; should be removed |
| **Classification report** | `train_model.py` | Uses wrong `CATEGORY_ORDER` for display labels (doesn't affect predictions) |

### Data Limitations

| Limitation | Details |
|------------|---------|
| **No historical outcome data** | Labels are heuristic (not real repayment data) |
| **No temporal dimension** | All profiles generated at a single point in time |
| **No geographic diversity** | Profiles use generic Indian state distribution |
| **No fraud or outlier cases** | Synthetic data is clean and well-behaved |
