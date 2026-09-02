# Recovery Copilot --- Architectural Decision Record

> Accepted architecture decisions and their consequences.

**Repository:** `AribAsim/Recovery-Copilot`\
**Branch:** `main`\
**Document date:** 1 September 2026\
**Status:** Accepted decisions

## ADR Index

  -----------------------------------------------------------------------
  ADR                     Decision                Status
  ----------------------- ----------------------- -----------------------
  ADR-001                 LLM is Advisory, Never  Accepted
                          Authoritative           

  ADR-002                 Three-Provider AI       Accepted
                          Cascade with            
                          Deterministic Fallback  

  ADR-003                 Policy Engine as        Accepted
                          Deterministic Financial 
                          Safety Gate             

  ADR-004                 Stateful Recovery       Accepted
                          Context Propagation     

  ADR-005                 Expected-Value Ranking  Accepted
                          for Action Selection    

  ADR-006                 SQLite for Prototype,   Accepted
                          PostgreSQL Deferred     

  ADR-007                 ThreadPoolExecutor for  Accepted
                          Batch Work              

  ADR-008                 Single-Page             Accepted
                          Story-Driven Frontend   

  ADR-009                 Simulation over Real    Accepted
                          Gateway Side Effects    
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## ADR-001: LLM is Advisory, Never Authoritative

**Status:** Accepted

### Context

AI is useful for ambiguous diagnosis and message drafting, but
probabilistic output must not authorize financial action.

### Decision

Restrict LLM usage to diagnosis and messaging. `PolicyEngine` owns the
final action decision.

### Consequences

**Benefits**

-   Clear authority boundary.
-   Better auditability.
-   AI providers/models can change without changing financial rules.
-   Policy remains code-controlled and testable.

**Trade-off**

-   AI cannot directly optimize or execute the final financial action.

------------------------------------------------------------------------

## ADR-002: Three-Provider AI Cascade with Deterministic Fallback

**Status:** Accepted

### Context

External AI providers can fail, rate-limit or return malformed
responses.

### Decision

Use the following cascade:

``` text
OpenRouter
   ↓
NVIDIA NIM
   ↓
Groq
   ↓
Deterministic classifier
```

Provider responses are schema-validated and confidence values are
bounded.

Configured models in the analyzed implementation include:

-   OpenRouter: `meta-llama/llama-3.1-8b-instruct:free`
-   NVIDIA NIM: `meta/llama-3.1-8b-instruct`
-   Groq: `llama-3.3-70b-versatile`

### Consequences

**Benefits**

-   Reduced dependence on a single provider.
-   Bounded degradation.
-   Deterministic fallback keeps the workflow operational.

**Trade-off**

-   More provider-specific parsing and maintenance.

------------------------------------------------------------------------

## ADR-003: Deterministic Financial Safety Gate

**Status:** Accepted

### Context

An AI recommendation may be syntactically valid but violate business or
compliance constraints.

### Decision

Run deterministic policy checks before any execution.

Implemented rule sequence:

1.  AI output format validation.
2.  Transaction eligibility.
3.  Maximum attempts.
4.  Operating window.
5.  Promise-to-pay state.
6.  High-value limit for amounts ≥ ₹50,000.
7.  Repeated failed-action block.
8.  Confidence threshold, default `0.70`.
9.  Retry cooldown.

### Consequences

**Benefits**

-   Every block is explainable.
-   Rules are deterministic and testable.
-   Model behavior cannot bypass financial constraints.

**Trade-off**

-   Conservative controls can increase escalation.

------------------------------------------------------------------------

## ADR-004: Stateful Recovery Context

**Status:** Accepted

### Context

A retry strategy that ignores previous attempts can repeatedly select
the same failed tactic.

### Decision

Build `RecoveryContext` from attempt history and reduce the probability
of actions that previously failed on the same transaction.

### Consequences

**Benefits**

-   Reduces repetitive recovery behavior.
-   Makes each decision context-aware.

**Trade-off**

-   Requires reliable history hydration and state management.

------------------------------------------------------------------------

## ADR-005: Expected-Value Ranking for Action Selection

**Status:** Accepted

### Context

Recovery actions differ in both probability of success and economic
cost.

### Decision

Rank candidates using:

``` text
Expected Net Recovery =
(transaction amount × recovery probability) − action cost
```

### Consequences

**Benefits**

-   Makes economic value explicit.
-   Prevents recovery-rate-only optimization from favoring unnecessarily
    expensive actions.

**Trade-off**

-   Current probability inputs are synthetic/static and require
    calibration for production.

------------------------------------------------------------------------

## ADR-006: SQLite for Prototype, PostgreSQL Deferred

**Status:** Accepted

### Context

The project needs minimal setup for local development and
demonstrations, while production requires stronger concurrency and
operational capabilities.

### Decision

Use SQLite by default through SQLAlchemy. Preserve PostgreSQL
compatibility through the existing SQLAlchemy/`psycopg2-binary` path.

### Consequences

**Benefits**

-   Zero-configuration local setup.
-   Simple demonstrations.
-   Straightforward migration path.

**Trade-off**

-   SQLite is not appropriate for high-concurrency production workloads.

------------------------------------------------------------------------

## ADR-007: ThreadPoolExecutor for Batch Work

**Status:** Accepted

### Context

Batch operations benefit from parallelism, but distributed
infrastructure is unnecessary for the current prototype.

### Decision

Use `ThreadPoolExecutor` with configurable workers and independent
database sessions per worker.

### Consequences

**Benefits**

-   Simple deployment.
-   Easy to reason about.
-   No queue infrastructure required.

**Trade-off**

-   No durable distributed retries.
-   No queue durability or dead-letter semantics.

### Production evolution

Move to durable workers such as Celery/RQ or a Kafka-backed architecture
when scale requires it.

------------------------------------------------------------------------

## ADR-008: Single-Page Story-Driven Frontend

**Status:** Accepted

### Context

A narrative recovery flow is easier to understand during evaluation than
a generic metrics dashboard.

### Decision

Serve a single `index.html` from FastAPI and present the canonical
transaction through the recovery stages.

### Consequences

**Benefits**

-   Clear demonstration narrative.
-   Makes the AI → Policy → Executor boundary visible.
-   Low frontend complexity.

**Trade-off**

-   The current UI is optimized for demonstration and should evolve into
    an operations console for production.

------------------------------------------------------------------------

## ADR-009: Simulation over Real Gateway Side Effects

**Status:** Accepted

### Context

Real payment retries, messages and financial actions create financial
and legal side effects during development and benchmarking.

### Decision

Use seeded probabilistic simulation inside `ActionExecutor`, while
preserving the same policy-to-executor authority boundary.

### Consequences

**Benefits**

-   Safe demonstrations.
-   Reproducible benchmarks.
-   No accidental financial side effects.

**Trade-off**

-   Synthetic outcomes cannot be interpreted as live production
    performance.

------------------------------------------------------------------------

## Decision Summary

These decisions form a deliberate control architecture:

``` text
Probabilistic systems
        ↓
  Propose / explain
        ↓
Deterministic policy
        ↓
 Decide / constrain
        ↓
Authorized executor
        ↓
     Execute
        ↓
Outcome + audit
        ↓
Updated recovery context
```

The central design principle is:

> **Prediction ≠ Authorization ≠ Execution**

The major deferred changes are infrastructure scale, calibrated recovery
models and real-world side-effect adapters.
