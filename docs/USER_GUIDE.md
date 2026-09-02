# Recovery Copilot --- User Guide

> Installation, configuration, API usage, UI walkthrough, benchmarking
> and troubleshooting.

**Repository:** `AribAsim/Recovery-Copilot`\
**Branch:** `main`\
**Document date:** 1 September 2026

## 1. What Recovery Copilot Does

Recovery Copilot demonstrates a controlled recovery workflow for failed
payments and overdue invoices.

The system:

1.  Diagnoses the failure.
2.  Predicts candidate recovery actions.
3.  Ranks actions using Expected Net Recovery.
4.  Applies deterministic policy controls.
5.  Executes only an approved action.
6.  Records the outcome.
7.  Uses the outcome as context for the next attempt.

The current executor is simulation-based.

## 2. Prerequisites

-   Python 3.11 or newer
-   Git and a terminal
-   Repository checked out locally
-   Docker is optional
-   An AI provider key is optional when using deterministic diagnosis

## 3. Installation

``` bash
cd Recovery-Copilot

python -m venv venv
```

### macOS / Linux

``` bash
source venv/bin/activate
```

### Windows PowerShell

``` powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

``` bash
pip install -r requirements.txt
```

Create configuration:

``` bash
cp .env.example .env
```

On Windows, copy `.env.example` to `.env` using the equivalent shell
command if `cp` is unavailable.

Keep API keys local and never commit them.

## 4. Configuration

  ------------------------------------------------------------------------------------------------------
  Variable                 Default                                   Required          Meaning
  ------------------------ ----------------------------------------- ----------------- -----------------
  `OPENROUTER_API_KEY`     ---                                       AI mode           Primary provider
                                                                                       credential

  `OPENROUTER_MODEL`       `meta-llama/llama-3.1-8b-instruct:free`   No                Primary model

  `GROQ_API_KEY`           ---                                       No                Fallback provider
                                                                                       credential

  `NVIDIA_API_KEY`         ---                                       No                Fallback provider
                                                                                       credential

  `DATABASE_URL`           `sqlite:///./recovery.db`                 No                Database

  `MAX_RETRY_ATTEMPTS`     `3`                                       No                Hard retry
                                                                                       ceiling

  `CONFIDENCE_THRESHOLD`   `0.70`                                    No                Minimum
                                                                                       confidence for
                                                                                       automatic action

  `DIAGNOSIS_MODE`         `llm`                                     No                `llm` or
                                                                                       `deterministic`

  `RECOVERY_MAX_WORKERS`   `4`                                       No                Batch workers
  ------------------------------------------------------------------------------------------------------

For a provider-independent demo:

``` text
DIAGNOSIS_MODE=deterministic
```

## 5. Starting the Application

Seed the canonical demonstration transaction:

``` bash
python scripts/seed_demo.py
```

Start FastAPI:

``` bash
uvicorn app.main:app --reload
```

Open:

``` text
http://127.0.0.1:8000/
```

The application also initializes tables and demo data during startup
when the database is empty.

## 6. UI Walkthrough

### Failed Payment

Shows the canonical transaction and its current state.

**Action:** Click **RUN NEXT RECOVERY**.

### AI Diagnosis

Shows:

-   failure category
-   confidence
-   diagnosis source

The source can be an AI provider or deterministic fallback.

### Policy Gate

Shows whether the recommended action is:

-   approved
-   blocked
-   overridden

The section exposes the rules that influenced the decision.

### Execution

Shows:

-   approved action
-   simulated outcome
-   cost
-   recovery amount
-   customer message where applicable

### Next Best Action

Shows the state-aware candidate for the next recovery attempt.

Previous failed actions influence subsequent selection.

### Attempt Timeline

Shows the chronological recovery history and state transitions.

### Technical Audit

Provides detailed decision fields useful for debugging and compliance
review.

### Benchmark

Shows scenario-level recovery comparisons.

The Operations dropdown can hide batch controls during presentations.
**Reset Demo** recreates the canonical transaction and clears its
previous attempt history.

## 7. API Reference

### Generate synthetic transactions

``` http
POST /transactions/generate
```

Example body:

``` json
{
  "n": 60,
  "scenario": "baseline",
  "seed": 42
}
```

Supported scenarios:

``` text
baseline
card_heavy
infra_heavy
ambiguous_heavy
```

### Run one recovery attempt

``` http
POST /recovery/run/{id}
```

### Run a batch

``` http
POST /recovery/run-batch
```

### Run until resolved

``` http
POST /recovery/run-until-resolved
```

### Retrieve audit history

``` http
GET /recovery/audit/{id}
```

### Export outcome intelligence

``` http
GET /recovery/outcome-dataset
```

### Read dashboard summary

``` http
GET /dashboard/summary
```

### Change runtime settings

``` http
POST /recovery/settings
```

Example:

``` json
{
  "DIAGNOSIS_MODE": "deterministic"
}
```

or:

``` json
{
  "CONFIDENCE_THRESHOLD": 0.85
}
```

## 8. B2B Invoice Recovery

Generate invoices:

``` http
POST /invoices/generate
```

Example:

``` json
{
  "n": 20
}
```

Run invoice recovery:

``` http
POST /invoices/run-batch
```

Retrieve invoice audit:

``` http
GET /invoices/audit/{id}
```

Invoice recovery demonstrates escalation/dunning logic based on invoice
state and days overdue. It does not perform real collection.

## 9. Benchmark Workflow

### Presentation demo

``` bash
python scripts/seed_demo.py
uvicorn app.main:app --reload
```

Then:

1.  Open the application.
2.  Show the failed payment.
3.  Run the first recovery.
4.  Inspect the attempt timeline.
5.  Run the next recovery.
6.  Show how prior state influences the decision.
7.  Show the Policy Gate.
8.  Show the Executor.
9.  Show the final outcome.
10. Show the benchmark.

### Multi-scenario evaluation

Generate and run the same workflow for:

``` text
baseline
card_heavy
infra_heavy
ambiguous_heavy
```

The purpose is to reduce cherry-picking and evaluate behavior across
different synthetic populations.

## 10. Useful Scripts

  -----------------------------------------------------------------------
  Script                              Purpose
  ----------------------------------- -----------------------------------
  `scripts/seed_demo.py`              Seeds the canonical demonstration
                                      transaction

  `scripts/replay_harness.py`         Multi-scenario replay/stress
                                      evaluation

  `scripts/run_diagnosis.py`          Diagnosis-only benchmark

  `scripts/run_integrity.py`          Audit/data-integrity checks

  `scripts/run_perf_comparison.py`    Performance comparison workflow

  `scripts/final_sanity_check.py`     Pre-demo sanity validation
  -----------------------------------------------------------------------

## 11. Troubleshooting

  -----------------------------------------------------------------------
  Symptom                 Likely cause            Action
  ----------------------- ----------------------- -----------------------
  Unexpected UI data      Old records remain      Run `seed_demo.py` and
                                                  hard-refresh

  Provider/API-key        Missing credential      Configure `.env` or use
  warning                                         deterministic mode

  High escalation rate    High threshold or       Inspect audit data and
                          ambiguous input         adjust deliberately

  Recovery does not       Attempt/terminal logic  Check
  terminate               issue                   `MAX_RETRY_ATTEMPTS`
                                                  and logs

  Docker exits            Port/persistence        Set `PORT` and persist
                          configuration           the SQLite database
  -----------------------------------------------------------------------

## 12. Benchmark Interpretation

The benchmark is a controlled synthetic evaluation, not a production
guarantee.

A representative benchmark configuration reported:

  Strategy                         Recovery   Simulated Net Recovery
  ------------------------------ ---------- ------------------------
  Always Retry                          88%                 ₹482,224
  Rule-Based Recovery                   86%                 ₹470,568
  AI-Assisted Recovery Copilot          95%                 ₹516,545

The correct interpretation is:

> On the controlled synthetic benchmark, the AI-assisted strategy
> recovered 95% of transactions versus 88% for Always Retry, with higher
> simulated net recovery.

Do **not** interpret this as "95% AI accuracy" or as a production
recovery rate.

## 13. Operational Notes

-   The executor is simulation-based.
-   Benchmark results are synthetic.
-   API keys must remain outside source control.
-   Each attempt should be treated as an auditable decision record.
-   Production persistence should use PostgreSQL.
-   Production batch processing should use durable asynchronous jobs.
-   Real gateway actions require idempotency, authentication,
    authorization, rate limits, retries/circuit breakers and explicit
    side-effect adapters.

## 14. Example Command Set

### Install

``` bash
pip install -r requirements.txt
```

### Demo

``` bash
python scripts/seed_demo.py
uvicorn app.main:app --reload
```

### Generate data

``` bash
curl -X POST http://localhost:8000/transactions/generate \
  -H "Content-Type: application/json" \
  -d '{"n":60,"scenario":"baseline","seed":42}'
```

### Single attempt

``` bash
curl -X POST http://localhost:8000/recovery/run/1
```

### Batch

``` bash
curl -X POST http://localhost:8000/recovery/run-batch
```

### Until resolved

``` bash
curl -X POST http://localhost:8000/recovery/run-until-resolved
```

### Audit

``` bash
curl http://localhost:8000/recovery/audit/1
```

### Dashboard

``` bash
curl http://localhost:8000/dashboard/summary
```
