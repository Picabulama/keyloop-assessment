# Intelligent Inventory Dashboard — Backend API

FastAPI + SQLAlchemy backend for a dealership vehicle inventory dashboard: filterable
inventory listing, automatic aging-stock (>90 days) identification, and per-vehicle
action logging.

Full architecture and design rationale: [`docs/SYSTEM_DESIGN.md`](docs/SYSTEM_DESIGN.md).

## Stack

Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2, PostgreSQL, Prometheus metrics,
JSON structured logging.

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# make sure Postgres is running first — see "Local PostgreSQL setup" below
docker compose up -d db

# create tables (schema creation is explicit, not an app-startup side effect)
python -m scripts.init_db

# optional: seed sample dealership data, including aging vehicles
python -m scripts.seed_data

uvicorn app.main:app --reload
```

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Raw OpenAPI spec: http://127.0.0.1:8000/openapi.json (also checked into [`openapi.json`](openapi.json))
- Health check: http://127.0.0.1:8000/health
- Prometheus metrics: http://127.0.0.1:8000/metrics

## Local PostgreSQL setup (Docker)

The app requires a running PostgreSQL instance — there is no SQLite fallback. The
easiest way to get one locally is via the `db` service already defined in
`docker-compose.yml`.

**Option A — run just the database in Docker, app on your host (fastest inner loop):**

```bash
# start a disposable Postgres 16 container, exposed on localhost:5432
docker compose up -d db

# wait for it to report healthy
docker compose ps

# (optional) connect and poke around
docker compose exec db psql -U inventory -d inventory
```

This creates a `inventory` database/user (`inventory` / `inventory`) matching the
default `DATABASE_URL` in `app/config.py`:

```
postgresql+psycopg2://inventory:inventory@localhost:5432/inventory
```

Then run the app on your host as normal (see Quickstart above). Data persists in the
named Docker volume `pg_data` across restarts; `docker compose down -v` wipes it.

**Option B — run everything in Docker (app + db):**

```bash
docker compose up --build
```

The `api` service waits for `db`'s healthcheck before starting, and connects to it via
the Docker network hostname `db` (`DATABASE_URL=postgresql+psycopg2://inventory:inventory@db:5432/inventory`).

**Option C — no Docker at all:** install Postgres natively (e.g. `brew install
postgresql@16`), then create a matching role/database:

```bash
createuser -s inventory -P   # set password "inventory" when prompted
createdb -O inventory inventory
```

and point `DATABASE_URL` (env var or `.env` file) at it, e.g.
`postgresql+psycopg2://inventory:inventory@localhost:5432/inventory`.

## Tests

```bash
pytest -v
```

14 tests cover CRUD, filter combinations, the aging-stock boundary (exactly 90 days is
**not** aging; 91+ days **is**), aging summary math, and action logging/ordering.

The test suite runs against an in-memory SQLite database (see `tests/conftest.py`)
rather than the Postgres instance used for local/production runs. This is a
deliberate, common testing tradeoff — fast, hermetic, zero external dependency for
CI — not a statement about the app's runtime database, which is PostgreSQL-only. The
app itself contains no SQLite-specific code path.

## API walkthrough (cURL)

Create a vehicle:

```bash
curl -s -X POST http://127.0.0.1:8000/vehicles \
  -H "Content-Type: application/json" \
  -d '{
        "vin": "1HGCM82633A004352",
        "make": "Honda",
        "model": "Accord",
        "trim": "EX-L",
        "year": 2022,
        "color": "Silver",
        "price": 24900,
        "mileage": 18000,
        "date_received": "2026-02-01"
      }'
```

List inventory, filtered by make/model, with pagination:

```bash
curl -s "http://127.0.0.1:8000/vehicles?make=Honda&model=Accord&limit=20&offset=0"
```

Only aging stock (>90 days in inventory):

```bash
curl -s "http://127.0.0.1:8000/vehicles?aging_only=true"
```

Custom age window (between 30 and 120 days):

```bash
curl -s "http://127.0.0.1:8000/vehicles?min_age_days=30&max_age_days=120"
```

Aging summary for a dashboard KPI tile:

```bash
curl -s "http://127.0.0.1:8000/vehicles/aging-summary"
# {"aging_threshold_days":90,"total_vehicles":8,"aging_vehicle_count":4,"aging_percentage":50.0,"oldest_days_in_inventory":180}
```

Log a manager action/status on an aging vehicle:

```bash
curl -s -X POST http://127.0.0.1:8000/vehicles/{vehicle_id}/actions \
  -H "Content-Type: application/json" \
  -d '{
        "status": "price_reduction_planned",
        "note": "Reduce list price by $1,500 next Monday.",
        "created_by": "jane.manager"
      }'
```

View the action history for a vehicle (most recent first):

```bash
curl -s "http://127.0.0.1:8000/vehicles/{vehicle_id}/actions"
```

Update or remove a vehicle:

```bash
curl -s -X PATCH http://127.0.0.1:8000/vehicles/{vehicle_id} -d '{"price": 22900}' -H "Content-Type: application/json"
curl -s -X DELETE http://127.0.0.1:8000/vehicles/{vehicle_id}
```

## Project layout

```
app/
  main.py          FastAPI app, middleware, metrics, health check
  models.py        SQLAlchemy ORM models (Vehicle, InventoryAction)
  schemas.py       Pydantic request/response contracts
  crud.py          Query/filter logic, aging calculation
  config.py        Environment-driven settings
  logging_conf.py  JSON structured logging + request-id context
  routers/
    vehicles.py    Inventory CRUD + filters + aging summary
    actions.py     Per-vehicle action log endpoints
scripts/
  seed_data.py     Sample dealership inventory (includes aging vehicles)
tests/             pytest suite (isolated in-memory SQLite per test; app itself is Postgres-only)
docs/
  SYSTEM_DESIGN.md Architecture, data flow, tech choices, observability, future work
```

## Notes / assumptions

- **Client layer**: mocked via this README's cURL examples, the auto-generated
  Swagger UI, and the checked-in `openapi.json` contract — no frontend is included per
  the backend-focused track of this challenge.
- **Aging threshold**: fixed at >90 days via `AGING_THRESHOLD_DAYS` (env-configurable),
  matching the scenario's stated definition. "Age" is computed from `date_received`
  vs. current date, not stored redundantly, so it's always accurate.
- **Persistence**: PostgreSQL is the only supported runtime database (via
  `psycopg2`). A `docker-compose.yml` `db` service gives a one-command local instance
  — see "Local PostgreSQL setup" above. All access goes through SQLAlchemy Core/ORM
  with no Postgres-specific SQL, so a managed Postgres (RDS, Cloud SQL, etc.) is a
  drop-in swap via `DATABASE_URL` for production.
- **Multi-dealership**: a `dealership_id` field exists on `Vehicle` for future
  multi-tenancy but isn't enforced/authenticated yet — see System Design Document's
  "Future Work" section.

## AI Collaboration Narrative

I built this project together with Claude, using it as a coding partner rather than just a place to ask questions.

**Design phase.** I picked the tech stack myself — Python and FastAPI for the backend, PostgreSQL in Docker for the database, plus logging and a health check so the service is easy to monitor and run anywhere.

**Implementation.** I explained the business logic to Claude — tracking dealership inventory, flagging vehicles that had been sitting too long, and logging follow-up actions on them — and had it generate the database structure and API endpoints from that description. I also asked it to generate the mock data used for seeding.

**Verification.** I spun up the database in Docker, seeded it with the sample data scripts, started the server, and went through the endpoints with curl and the Swagger UI to make sure everything worked. Along the way I caught a couple of bugs — one in how "aging" vehicles were being identified, and one in how actions were ordered — and got them fixed before wrapping up.
