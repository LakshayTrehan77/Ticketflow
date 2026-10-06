# TicketFlow

A support ticket backend. Users create tickets, a small ML model reads the text and sets the category and priority, and support agents manage the tickets through a REST API.

I built this to practice the full path of a backend service: API design, auth, database, a bit of machine learning, containers, Kubernetes and CI. It is small on purpose, so the whole thing can be read in an evening.

## What it does

- Register and login with JWT tokens (passwords hashed with bcrypt)
- Two roles: `user` and `agent`. Users see only their own tickets, agents see everything
- When a ticket is created, a scikit-learn model predicts the **category** (billing, technical, account, feature_request, general) and a **priority** (low, medium, high)
- Filtering and pagination on the ticket list
- Agents can change status, assign tickets to other agents and see a stats summary
- Stats are cached in Redis (falls back to a plain in-memory cache if Redis is not there)
- `/health`, `/ready` and `/metrics` (Prometheus) endpoints for running it in Kubernetes
- Automatic API docs at `/docs`

## Tech stack

| Area | What I used |
|------|-------------|
| Language | Python 3.12 |
| API | FastAPI, Pydantic, Uvicorn |
| Database | PostgreSQL (SQLite for local dev and tests), SQLAlchemy 2 |
| Cache | Redis |
| Auth | JWT (PyJWT), bcrypt, role based access |
| ML | scikit-learn (TF-IDF + Logistic Regression), joblib |
| Containers | Docker (multi-stage build), Docker Compose |
| Orchestration | Kubernetes (Deployment, StatefulSet, Service, Ingress, HPA, Kustomize) |
| CI/CD | GitHub Actions, GitHub Container Registry |
| Monitoring | Prometheus metrics |
| Testing | pytest, ruff |

## Architecture

```
            client
              |
          [ Ingress ]
              |
   +----------------------+
   |   FastAPI (2+ pods)  |---- loads model at startup (joblib)
   +----------------------+
        |            |
   [ PostgreSQL ]  [ Redis ]
```

Code is split in layers so each file has one job:

- `routers/` takes the request and returns the response
- `services/` has the actual logic (ticket queries, classifier, cache)
- `models.py` is the database tables, `schemas.py` is the request/response shapes

## Project structure

```
ticketflow/
├── app/
│   ├── main.py              # app setup, middleware, startup
│   ├── config.py            # settings from environment variables
│   ├── database.py          # engine and session
│   ├── models.py            # SQLAlchemy tables
│   ├── schemas.py           # Pydantic schemas
│   ├── security.py          # password hashing and JWT
│   ├── deps.py              # current user / agent dependencies
│   ├── metrics.py           # Prometheus counters
│   ├── routers/             # auth, tickets, health
│   └── services/            # ticket_service, classifier, cache
├── ml/
│   ├── data/tickets.csv     # labelled training tickets
│   └── train.py             # training script
├── tests/                   # pytest tests
├── k8s/                     # Kubernetes manifests
├── .github/workflows/ci.yml # lint, test, build image
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── requirements.txt
```

## Run it locally

You need Python 3.12 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
make install
cp .env.example .env
make run
```

`make run` trains the model first and then starts the server on http://localhost:8000. Open http://localhost:8000/docs to try the endpoints.

By default it uses a local SQLite file. Any email listed in `AGENT_EMAILS` gets the agent role when it registers.

## Run with Docker Compose

This starts the API, PostgreSQL and Redis together.

```bash
docker compose up --build
```

The model is trained while the image is built, so the container is ready to serve right away.

## Deploy to Kubernetes

The manifests are meant for a local cluster (minikube or kind) but should work on any cluster.

```bash
# 1. build and push your image, then change the image name in k8s/deployment.yaml
# 2. create the secret from the example file
cp k8s/secret.example.yaml k8s/secret.yaml     # edit the values
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secret.yaml

# 3. everything else
kubectl apply -k k8s/
kubectl -n ticketflow get pods
```

What is in there:

- API **Deployment** with 2 replicas, rolling updates, liveness and readiness probes, resource limits and a non-root user
- **HorizontalPodAutoscaler** that scales between 2 and 6 pods on CPU
- **StatefulSet** with a persistent volume for PostgreSQL
- Redis, a ClusterIP Service and an nginx **Ingress**
- Config in a ConfigMap, passwords in a Secret (the real secret file is not committed)

Redis is shared between the pods on purpose. With only an in-memory cache each pod would have its own copy and the stats could be out of sync.

## API examples

```bash
# register and login
curl -X POST localhost:8000/auth/register -H "Content-Type: application/json" \
  -d '{"email": "me@example.com", "password": "password123"}'

curl -X POST localhost:8000/auth/login -d "username=me@example.com&password=password123"

# create a ticket (use the access_token from the login response)
curl -X POST localhost:8000/tickets \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"title": "Refund please", "description": "I was charged twice this month and need a refund"}'
```

Response (shortened):

```json
{
  "id": 1,
  "category": "billing",
  "priority": "high",
  "status": "open",
  "confidence": 0.92
}
```

| Method | Path | Who | Description |
|--------|------|-----|-------------|
| POST | `/auth/register` | anyone | create an account |
| POST | `/auth/login` | anyone | get a token |
| GET | `/auth/me` | logged in | current user |
| POST | `/tickets` | logged in | create a ticket (auto classified) |
| GET | `/tickets` | logged in | list tickets, filters: `status`, `category`, `priority`, `page`, `size` |
| GET | `/tickets/{id}` | owner or agent | one ticket |
| PATCH | `/tickets/{id}` | agent | change status, assignee, category, priority |
| GET | `/tickets/stats` | agent | counts by status, category and priority |
| GET | `/health`, `/ready`, `/metrics` | anyone | ops endpoints |

## The ML part

The classifier lives in `ml/train.py`. Two models are trained, one for category and one for priority. Both are a TF-IDF (word and character n-grams) feature step followed by Logistic Regression.

The dataset is 200 short tickets that I wrote by hand (`ml/data/tickets.csv`). I evaluated on a stratified 80/20 split and then retrained on all of the data for the model that gets shipped.

| Target | Accuracy on held out 20% |
|--------|--------------------------|
| Category (5 classes) | 0.85 |
| Priority (3 classes) | 0.55 |

Being honest about the numbers: the category model works well enough for this kind of text, but priority is hard to guess from the wording alone and the dataset is small. To help with that, tickets that contain words like "urgent" or "asap" are always set to high. A real system would need real labelled tickets and better evaluation.

If the model file is missing the API still starts and gives every ticket the default labels (`general` / `medium`), and `/ready` reports not ready.

Retrain any time with:

```bash
make train
```

## Tests

```bash
make test
make lint
```

26 tests cover registration and login, permissions (user vs agent), ticket creation and filtering, pagination, the cache being cleared on new tickets, the classifier and the health/metrics endpoints. Tests run against in-memory SQLite, so they need no database or Redis.

## CI/CD

The GitHub Actions workflow runs on every push and pull request: install, lint with ruff, run pytest. On `main` it also builds the Docker image and pushes it to GitHub Container Registry.

## Things I would add next

- Alembic migrations (right now tables are created on startup)
- Comments on tickets and email notifications
- Rate limiting on the login route
- A bigger dataset, and swapping the model for a small transformer to compare
- Terraform for a managed cluster (EKS or GKE) and a managed Postgres

