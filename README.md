# AI Growth Journey Orchestration Platform

Event-driven Python system that turns customer behavior into auditable next actions while consent, support, freshness, cooldown and approval rules remain deterministic.

## What works

Events are validated, UTC-normalized, persisted and deduplicated. The API builds Customer 360 state, ordered funnels, stable experiment assignments, explainable journey decisions, policy verdicts, a role-gated approval/outbox flow, deterministic outreach fallback, simulated execution and idempotent feedback callbacks. No real message is sent.

## Windows / PowerShell setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m app.scripts.init_db
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`. In another terminal run `python -m pytest -v` or `python -m app.scripts.demo`.

## Architecture

`sources → /events → SQLite → customer state → deterministic eligibility → action candidate → policy + approval → transactional outbox → fake adapter → feedback`

The default `EXECUTION_MODE=simulation`. `LLM_PROVIDER=fake` means drafts use a deterministic fallback and are not AI output. Real provider credentials, recipients, campaigns and paid LLM calls are deliberately absent.

## Local agent layer with Ollama

The Journey Planner can select only from deterministic `allowed_actions`; the Outreach Agent can use only supplied facts and the approved CTA. Both validate Ollama output against Pydantic schemas and fall back deterministically on timeout, invalid JSON, an ungrounded fact, or a forbidden action.

```powershell
docker compose up -d ollama
docker compose exec ollama ollama pull qwen2.5:3b
docker compose up -d api
```

Check `GET /agents/health`, call `POST /agents/plan/{user_id}`, or generate a draft with `POST /actions/{action_id}/draft`. Ollama stays local at port 11434; no paid API is used.

## Safety and trade-offs

SQLite and synchronous jobs suit a local portfolio demo, not concurrent production traffic. Header roles illustrate authorization boundaries but require a real identity provider before deployment. `create_all` initializes development databases; schema changes need Alembic migrations. Provider-specific signatures, reconciliation and actual sequence semantics require a selected vendor and sandbox account.

Tests are isolated in `tests/.test-growth.db` and never reset `growth.db`. Install `requirements-dev.txt` to use Alembic.

See `docs/requirements-traceability.md`, `docs/demo-scenario.md`, `docs/runbook.md`, and local-only `learning_lab/START_HERE.md`.
