# Recovery Copilot --- Design Document

> **AI-powered payment recovery with deterministic financial controls**\
> **Core principle: AI recommends. Policy authorizes. Executor acts.**

**Repository:** `AribAsim/Recovery-Copilot`\
**Branch:** `main`\
**Document date:** 1 September 2026

## 1. Executive Summary

Recovery Copilot is a bounded revenue-recovery system for failed
payments and overdue invoices. It treats recovery as a sequence of
stateful decisions rather than a blind retry loop.

The system separates probabilistic AI assistance from deterministic
financial control:

-   AI diagnoses failure categories and can generate customer-facing
    recovery messaging.
-   A stateful predictor proposes candidate recovery actions.
-   Expected Net Recovery ranks candidates economically.
-   A deterministic Policy Engine authorizes or blocks the proposed
    action.
-   An allowlisted executor performs only policy-approved actions.
-   The outcome is persisted and becomes context for the next decision.
-   Every attempt produces an auditable decision and outcome record.

The current implementation intentionally uses simulated execution so
demonstrations and benchmarks cannot create real financial side effects.

## 2. Goals and Non-Goals

### Goals

1.  Context-aware recovery instead of blind retries.
2.  Deterministic policy enforcement around financial actions.
3.  Resilience to AI-provider failures through a provider cascade and
    deterministic fallback.
4.  Stateful learning from previous recovery attempts.
5.  Transparent auditability and reproducible benchmarking.
6.  Lightweight local deployment suitable for development and
    demonstrations.

### Non-Goals

-   Real payment charging or production gateway side effects.
-   Production-scale distributed job orchestration.
-   A production-grade customer communications platform.
-   Continuously trained or fully calibrated recovery-probability
    models.

## 3. Architecture Overview

The core lifecycle is:

``` text
Failure
   ↓
Diagnose
   ↓
Generate Recovery Candidates
   ↓
Expected Net Recovery Ranking
   ↓
Deterministic Policy Gate
   ↓
Execute Approved Action
   ↓
Observe Outcome
   ↓
Update Recovery Context
   ↓
Next Decision / Terminal State
   ↓
Audit
```

### Architectural boundary

``` text
LLM / Predictor → Recommendation
Policy Engine    → Authorization
Executor        → Action
Outcome         → New Context
```

The LLM is never the authority for financial execution.

## 4. Component Design

  --------------------------------------------------------------------------
  Layer                   Primary components         Responsibility
  ----------------------- -------------------------- -----------------------
  API / Bootstrap         `app/main.py`,             FastAPI application,
                          `app/routers/*`            routes, startup and SPA
                                                     serving

  Orchestration           `app/services/engine.py`   Coordinates individual
                                                     attempts, batches and
                                                     until-resolved flows

  Diagnosis               `llm_classifier.py`,       AI diagnosis,
                          `classifier.py`            validation and
                                                     deterministic fallback

  Prediction / Value      `stateful_predictor.py`,   Candidate actions,
                          `recovery_value.py`        history-aware
                                                     probabilities and value
                                                     ranking

  Decision / Policy       `decision_router.py`,      Maps diagnoses to
                          `policy_engine.py`         actions and enforces
                                                     hard rules

  Execution               `action_executor.py`       Allowlisted execution
                                                     boundary and
                                                     deterministic
                                                     simulation

  Messaging               `llm_client.py`            AI-assisted customer
                                                     recovery messaging

  Persistence             `database.py`, `models.py` SQLAlchemy persistence
                                                     for transactions,
                                                     invoices and attempts

  Observability           `outcome_recorder.py`,     Outcome records and
                          dashboard services         recovery/economic
                                                     summaries
  --------------------------------------------------------------------------

## 5. Detailed Data Flow

### 5.1 B2C payment recovery

1.  `POST /recovery/run/{id}` receives a transaction ID.
2.  The recovery engine builds policy and historical recovery context.
3.  Diagnosis runs in LLM or deterministic mode.
4.  LLM output is schema-validated and confidence is bounded.
5.  The stateful predictor creates candidate actions and penalizes
    actions that previously failed for the same transaction.
6.  Expected Net Recovery is calculated:

``` text
Expected Net Recovery =
(transaction amount × recovery probability) − action cost
```

7.  Candidates are ranked.
8.  `PolicyEngine` evaluates deterministic financial rules.
9.  The executor receives only the approved action.
10. Execution returns outcome, cost, recovery amount and escalation
    state.
11. A `RecoveryAttempt` is persisted.
12. Transaction state and recovery context are updated for the next
    attempt.

### 5.2 B2B invoice recovery

Invoice recovery uses days-overdue buckets and hard stopping limits. The
system maps invoice state to escalation actions, avoids blindly
repeating failed actions, simulates the outcome and records the attempt
before updating invoice status.

## 6. Data Model and Auditability

### Transaction

Represents a B2C failed-payment record.

Key fields include:

-   payment reference
-   amount
-   failure code
-   status
-   timestamps

### Invoice

Represents a B2B overdue receivable.

Key fields include:

-   invoice state
-   amount
-   days overdue
-   recovery status

### RecoveryAttempt

Represents the auditable decision and outcome record.

It captures:

-   diagnosis
-   diagnosis confidence and source
-   recommendation
-   recovery probability
-   reasoning
-   policy decision
-   policy block/override reason
-   evaluated rules
-   approved action
-   execution result
-   action cost
-   recovered amount
-   net recovery
-   outcome
-   escalation state
-   timestamp

The outcome-dataset endpoint exposes recovery attempts for offline
analysis and evaluation.

## 7. Policy and Safety Controls

The Policy Engine is deterministic and independent of model behavior.

The implemented rule sequence includes:

1.  AI output format validation.
2.  Transaction eligibility.
3.  Maximum attempt limit.
4.  Operating-window validation.
5.  Promise-to-pay state.
6.  High-value transaction control for amounts ≥ ₹50,000.
7.  Repeated failed-action blocking.
8.  Confidence threshold, default `0.70`.
9.  Retry cooldown.

The architecture follows a fail-closed principle: invalid, unsafe or
unauthorized recommendations cannot reach execution.

## 8. Stateful Recovery

Recovery context is constructed from the transaction and previous
attempts.

A failed action is not discarded. Instead, its outcome influences
subsequent candidate probabilities.

Conceptually:

``` text
Attempt 1
   ↓
Action fails
   ↓
Context updated
   ↓
Previous action penalized
   ↓
Attempt 2 selects a different candidate
```

This converts recovery from:

``` text
failure → retry → retry → retry
```

into:

``` text
failure → observe → update state → choose next safe action
```

## 9. Concurrency and Scaling

Batch recovery currently uses Python `ThreadPoolExecutor` with a
configurable worker count, defaulting to 4. Each worker uses an
independent SQLAlchemy session.

  ------------------------------------------------------------------------
  Current design          Reason                  Production evolution
  ----------------------- ----------------------- ------------------------
  `ThreadPoolExecutor`    Simple parallelism      Durable worker queue
                                                  such as
                                                  Celery/RQ/Kafka-backed
                                                  workers

  SQLite                  Zero-configuration      PostgreSQL with
                          local setup             migrations and pooling

  Synchronous provider    Simple prototype        Async I/O, retries and
  calls                   behavior                circuit breakers
  ------------------------------------------------------------------------

## 10. Frontend Design

`index.html` implements a story-driven single-page interface.

The canonical demo flow exposes:

1.  Failed Payment
2.  AI Diagnosis
3.  Policy Gate
4.  Execution
5.  Next Best Action
6.  Attempt Timeline
7.  Technical Audit
8.  Benchmark

The UI intentionally makes the authorization boundary visible: an AI
recommendation can be blocked by deterministic policy before execution.

## 11. Testing Strategy

The repository includes tests covering:

-   policy limits and cooldown behavior
-   repeated-action blocking
-   confidence gating
-   high-value controls
-   malformed AI output
-   terminal states
-   promise-to-pay and operating-window rules
-   provider fallback
-   concurrency and exception tolerance
-   stateful probability degradation

The benchmark/replay utilities provide controlled scenario evaluation.

## 12. Deployment and Configuration

The application uses Python 3.11+ and can run locally or in a container.

``` bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python scripts/seed_demo.py
uvicorn app.main:app --reload
```

Default configuration:

  ----------------------------------------------------------------------------------------
  Setting                                                    Default Purpose
  ------------------------ ----------------------------------------- ---------------------
  `DATABASE_URL`                           `sqlite:///./recovery.db` Persistence

  `MAX_RETRY_ATTEMPTS`                                           `3` Attempt ceiling

  `CONFIDENCE_THRESHOLD`                                      `0.70` Minimum confidence

  `DIAGNOSIS_MODE`                                             `llm` LLM or deterministic
                                                                     diagnosis

  `RECOVERY_MAX_WORKERS`                                         `4` Batch concurrency

  `OPENROUTER_MODEL`         `meta-llama/llama-3.1-8b-instruct:free` Primary model
  ----------------------------------------------------------------------------------------

API credentials must remain outside source control.

## 13. Security and Operational Controls

The design provides several important boundaries:

-   LLM output cannot directly execute financial actions.
-   Execution is allowlisted.
-   High-value transactions receive additional controls.
-   Low-confidence diagnoses are prevented from automatic execution.
-   Every attempt records both recommendation and authoritative policy
    outcome.
-   Demonstration execution is simulated.
-   Provider integrations are isolated behind service boundaries.

## 14. Production Evolution

The prototype can evolve without changing the central authority
boundary.

Planned evolution includes:

1.  Replace simulation with real payment/message adapters.
2.  Preserve the same policy → executor boundary.
3.  Migrate persistence to PostgreSQL.
4.  Add schema migrations and connection pooling.
5.  Introduce durable asynchronous jobs with idempotency and dead-letter
    handling.
6.  Calibrate recovery probabilities from observed outcomes.
7.  Add authentication, authorization and secret management.
8.  Add structured logging and distributed tracing.
9.  Separate the demonstration UI from a production operations console.

## 15. Repository Structure

``` text
Recovery-Copilot/
├── app/
│   ├── core/
│   ├── models/
│   ├── routers/
│   ├── services/
│   └── main.py
├── scripts/
├── tests/
├── docs/
├── index.html
├── requirements.txt
├── Dockerfile
└── .env.example
```

### Key service files

``` text
llm_classifier.py       Diagnosis
classifier.py           Deterministic fallback
recovery_context.py     Historical transaction state
stateful_predictor.py   History-aware candidate prediction
recovery_value.py       Expected Net Recovery
policy_engine.py        Deterministic authorization
action_executor.py      Execution boundary
outcome_recorder.py     Outcome intelligence
engine.py               Recovery orchestration
```

## 16. Design Summary

Recovery Copilot deliberately separates **prediction, authorization and
execution**.

> **AI recommends. Policy authorizes. Executor acts. Context informs the
> next decision.**

This separation provides a foundation for explainable, auditable and
controlled AI-assisted financial recovery.
