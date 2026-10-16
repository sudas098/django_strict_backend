<div align="center">

# Collaborative Document Backend API & Asynchronous AI Engine

**A production-grade Django backend built for async concurrency, LLM token streaming, distributed tasks, and type safety.**

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-REST-A30000)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-4169E1?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-Workers-37814A?logo=celery&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![mypy](https://img.shields.io/badge/mypy-strict-2A6DB2)
![ruff](https://img.shields.io/badge/lint-ruff-D7FF64)

</div>

---

Built with ASGI concurrency, LLM token streaming, Celery task distribution, vector similarity support (pgvector), in-memory Redis caching, tiered rate limiting, and static type safety as first-class architectural concerns.

## Table of Contents

- [System Architecture Highlights](#system-architecture-highlights)
- [Tech Stack](#tech-stack)
- [Relational Domain Model](#relational-domain-model)
- [Architectural Deep Dives](#architectural-deep-dives)
  - [1. Async LLM Streaming](#1-asynchronous-llm-streaming-architecture-ai_viewspy)
  - [2. Distributed Task Queue](#2-distributed-task-queue--decoupled-workers-documentstaskspy)
  - [3. Containerized Topology](#3-containerized-topology-docker--compose)
  - [4. Caching (Cache-Aside)](#4-high-performance-caching--cache-aside-architecture)
  - [5. Query Optimization](#5-performance--query-optimization-o1-constant-queries)
- [Tiered Rate Limiting](#tiered-rate-limiting--abuse-prevention-rate-502)
- [RBAC Matrix](#role-based-access-control-rbac-matrix)
- [API Endpoints Reference](#api-endpoints-reference)
- [Getting Started](#getting-started)
- [Quality Gates](#quality-gates--verification)
- [Engineering Sprint Changelog](#engineering-sprint-changelog)

---

## System Architecture Highlights

```text
                        ┌───────────────────────────────────────────────┐
                        │            Reverse Proxy / Gateway            │
                        │              (e.g., Nginx / ALB)              │
                        └───────┬───────────────────────────────┬───────┘
                                │                               │
      HTTP REST (Sync/Cached)   │                               │   Async Event-Stream / NDJSON
                                ▼                               ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │                Uvicorn (ASGI Application Server)                │
        │ ┌───────────────────────────┐   ┌───────────────────────────┐   │
        │ │     Django REST Layer     │   │ Async LLM Streaming View  │   │
        │ │    (CRUD, Auth, RBAC)     │   │      (ai_views.py)        │   │
        │ └─────────────┬─────────────┘   └─────────────┬─────────────┘   │
        └───────────────┼───────────────────────────────┼─────────────────┘
                        │                               │ Non-blocking
                        ▼                               ▼ (Event Loop)
        ┌─────────────────────────────┐   ┌───────────────────────────┐
        │      Redis (In-Memory)      │   │ External AI Model Gateway │
        │  - Cache-Aside (TTL 300s)   │   │   (OpenAI / Anthropic)    │
        │  - Sliding-Window Throttles │   └───────────────────────────┘
        │  - Celery Message Broker    │
        └───────────────┬─────────────┘
                        │
          ┌─────────────┴─────────────┐
          │                           │
          ▼                           ▼
┌─────────────────────────────┐ ┌───────────────────────────────────────────┐
│   Celery Distributed Pool   │ │          PostgreSQL 16 + pgvector         │
│  (Heavy Exports / CPU Work) │ │  - Relational Core & FK Cascades          │
│     (documents/tasks.py)    │ │  - B-tree Indexes & Composite Constraints │
└─────────────────────────────┘ │  - High-Dimensional Vector Embeddings     │
                                └───────────────────────────────────────────┘
```

| Feature | Description |
| :-- | :-- |
| ⚡ **Modern Async Concurrency (ASGI)** | Powered by Uvicorn, freeing the runtime from synchronous WSGI thread-starvation during long-lived I/O. |
| 🌊 **Non-Blocking LLM Token Streaming** | `ai_views.py` uses Python `asyncio` and Django's `StreamingHttpResponse` to deliver real-time token chunks via Newline Delimited JSON (NDJSON) with zero thread-blocking overhead. |
| 🧵 **Distributed Worker Pipeline** | Heavy CPU and slow I/O workloads (e.g., document exports) are offloaded to Celery + Redis workers, returning an immediate `202 Accepted`. |
| 🧠 **AI-Ready Persistence** | PostgreSQL (`pgvector/pgvector:pg16`) with native vector similarity search for future-proof RAG pipelines and semantic retrieval. |
| 🐳 **Fully Containerized** | Deterministic multi-container topology orchestrating the ASGI backend, Redis broker/cache, and pgvector database via Docker Compose. |
| 🔐 **Object-Level RBAC** | `IsDocumentCollaborator` guarantees owner-only deletion and editor-only mutation semantics. |
| 🚀 **Redis Cache-Aside** | Automatic invalidation hooks on updates and deletes, keeping warm reads at constant `O(1)` query complexity. |
| 🛡️ **Tiered Rate Limiting** | Redis-backed sliding-window throttles protect public auth routes from brute force and authenticated endpoints from resource exhaustion. |
| 🎯 **Zero N+1 Queries** | Enforced eager loading (`select_related`, `prefetch_related`) eliminates linear query escalation. |
| ✅ **Strict Static Typing** | Strict `mypy` (with `django-stubs` and `djangorestframework-stubs`) prevents runtime type exceptions. |

---

## Tech Stack

| Domain | Technology | Operational Purpose |
| :-- | :-- | :-- |
| **Runtime & Framework** | Python 3.13, Django 5.2, DRF | High-productivity backend framework with a strict relational ORM |
| **Application Server** | Uvicorn (ASGI) | Non-blocking event loop for concurrent I/O and streaming |
| **Database & Vector Engine** | PostgreSQL 16 + pgvector | ACID relational consistency paired with high-dimensional vector search |
| **In-Memory Broker & Cache** | Redis 7 (Alpine) | Sub-millisecond cache-aside storage, Celery queue, and sliding throttles |
| **Task Queue** | Celery | Distributed background job processing for non-blocking exports |
| **Containerization** | Docker, Docker Compose | Reproducible environments across development and production |
| **Testing Harness** | pytest, pytest-django, factory_boy | Integration testing, mock factories, and query budget assertions |
| **Code Quality** | mypy (strict), ruff | Compile-time type verification and fast linting/formatting |

---

## Relational Domain Model

### Entity-Relationship Diagram

```mermaid
erDiagram
    CUSTOMUSER ||--o{ DOCUMENT : "owns"
    CUSTOMUSER ||--o{ DOCUMENTMEMBER : "is member"
    DOCUMENT   ||--o{ DOCUMENTMEMBER : "has"

    CUSTOMUSER {
        UUID id PK
        string email UK
        boolean is_active
        datetime date_joined
    }
    DOCUMENT {
        UUID id PK
        string title
        text content
        UUID owner_id FK
        datetime created_at
        datetime updated_at
    }
    DOCUMENTMEMBER {
        UUID id PK
        UUID document_id FK
        UUID user_id FK
        enum role "viewer | editor"
        datetime created_at
    }
```

> **Constraint:** `UNIQUE(document, user)` on `DocumentMember`.

### Relational Design Decisions

**1. Foreign Key cascade lifecycles** (`on_delete=models.CASCADE`)

- Deleting an **owner** cascades to purge all their authored `Document` records.
- Deleting a **collaborator user** removes their `DocumentMember` record without touching the shared `Document`.
- Deleting a **document** cleans up all child `DocumentMember` entries, preventing orphaned ACL records.

**2. Compound unique constraints**

- Enforced at the database level via `models.UniqueConstraint(fields=["document", "user"], name="unique_document_member")` to prevent race conditions during permission assignment.

**3. Indexing strategy**

- Dedicated B-tree indexes on `owner_id`, `created_at`, and `title` to accelerate `WHERE` filtering and ordered pagination scans (`ORDER BY created_at DESC`).

---

## Architectural Deep Dives

### 1. Asynchronous LLM Streaming Architecture (`ai_views.py`)

Traditional WSGI servers dedicate one OS worker thread per HTTP request. When an endpoint calls a generative AI provider that takes 3 to 10 seconds to respond, those threads sit idle waiting for network packets, causing thread starvation, latency spikes, and socket timeouts under minimal concurrent load.

`core/ai_views.py` solves this with an asynchronous streaming pipeline:

```python
class DocumentAiStreamView(APIView):
    permission_classes = [IsAuthenticated]

    async def get(self, request: Request) -> StreamingHttpResponse:
        prompt = request.query_params.get("q", "Summarize document")

        async def response_stream() -> AsyncGenerator[str, None]:
            async for token in MockAiStreamService.stream_tokens(prompt):
                yield token

        response = StreamingHttpResponse(
            response_stream(),
            content_type="application/x-ndjson",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
```

**Key engineering decisions**

- **Non-blocking cooperative scheduling:** Downstream calls yield execution via `await asyncio.sleep()`. While waiting on upstream model tokens, the single worker process keeps serving other requests on the event loop.
- **Transfer protocol:** HTTP Chunked Transfer Encoding returning Newline Delimited JSON (`application/x-ndjson`), so clients can stream, parse, and render markdown tokens dynamically.
- **Reverse-proxy buffer bypass (`X-Accel-Buffering: no`):** Nginx and edge CDNs buffer responses in 4KB/8KB chunks by default. This header forces proxies to flush each token packet immediately, preserving the typewriter UI effect.

### 2. Distributed Task Queue & Decoupled Workers (`documents/tasks.py`)

Workloads involving disk writes, report compilation, or PDF generation must never run inside the synchronous request-response loop.

```python
@shared_task(bind=True, max_retries=3)  # type: ignore[misc]
def process_document_export(
    self: Any,
    document_id: str,
) -> dict[str, str]:
    """Simulate heavy background export generation for a document."""
    try:
        doc = Document.objects.get(id=document_id)
        logger.info(
            "document_export_started",
            extra={"document": str(doc.id), "document_title": doc.title},
        )
        time.sleep(3)  # Heavy file compilation workload
        return {
            "status": "completed",
            "document_id": str(doc.id),
            "export_url": f"https://storage.cdn.company.internal/exports/{doc.id}.pdf",
        }
    except Document.DoesNotExist as exc:
        logger.error("document_not_found", extra={"document_id": document_id})
        raise exc
```

- **Asynchronous offloading:** The API enqueues the task onto Redis and immediately returns `202 Accepted` with a task reference, keeping p99 latency minimal.
- **Separation of concerns:** CPU-bound tasks run on standard worker threads in an isolated Celery pool, fully segregated from the Uvicorn event loop.

### 3. Containerized Topology (Docker & Compose)

The backend runs as an orchestrated set of containers that mirror production network topology:

```text
[ Docker Network: django_backend_default ]
 ├── web      (python:3.13-slim + Uvicorn ASGI, ports: 8000:8000)
 ├── redis    (redis:7-alpine,                  ports: 6379:6379)
 └── db       (pgvector/pgvector:pg16,          ports: 5432:5432)
```

- **Database engine:** The official `pgvector/pgvector:pg16` image enables extension provisioning (`CREATE EXTENSION IF NOT EXISTS vector;`) for semantic embedding search.
- **Deterministic startup:** Compose health checks (`pg_isready -U postgres`) and `condition: service_healthy` ensure Django never runs migrations or starts serving until PostgreSQL and Redis pass readiness probes.
- **Production build hygiene:** Multi-stage layer caching compiles system dependencies (`libpq-dev`, `build-essential`) and Python requirements before source ingestion, minimizing build time.

### 4. High-Performance Caching & Cache-Aside Architecture

Read-heavy endpoints that rarely mutate (`GET /api/documents/{id}/`) are decoupled from direct PostgreSQL execution using an in-memory **Cache-Aside (Lazy Loading)** pattern.

```text
GET /api/documents/{id}/
     │
     ▼
[ Check Cache (Key: "doc:{id}") ]
     │
     ├── HIT  ──► Return cached JSON directly (0 SQL queries executed)
     │
     └── MISS ──► 1. Query PostgreSQL via ORM (enforcing RBAC permission checks)
                  2. Serialize payload
                  3. Store in Redis (TTL: 300s)
                  4. Return JSON response

PATCH / PUT / DELETE /api/documents/{id}/
     │
     ▼
1. Mutate / delete record in PostgreSQL
2. Evict cache key: cache.delete(f"doc:{id}")
```

**Invalidation policy & fault tolerance**

- **Deterministic cache keys:** Formatted as `doc:{id}` to establish discrete namespace boundaries.
- **Proactive invalidation:** Handled in view lifecycle hooks (`perform_update`, `perform_destroy`), so stale representations never outlive a write transaction.
- **Fail-open resilience:** Configured with `IGNORE_EXCEPTIONS = True` and strict connection timeouts (5s). If Redis goes down, the backend falls back to direct database execution instead of dropping requests.
- **Isolated testing:** During pytest sessions, the cache backend routes to Django's in-memory `LocMemCache`, removing network dependencies while still validating eviction behavior.

### 5. Performance & Query Optimization (`O(1)` Constant Queries)

When serializing relational models with nested representations, naïve ORM access triggers the **N+1 query problem**: 1 initial query for the list plus N queries for each related foreign key.

```sql
-- Naïve execution without eager loading (10 documents, 2 members each):
SELECT * FROM documents;                     -- 1 query
SELECT * FROM users WHERE id = ...;          -- 10 queries (one per owner)
SELECT * FROM document_members WHERE ...;    -- 10 queries (one per document)
SELECT * FROM users WHERE id IN (...);       -- 10 queries (nested member users)
-- Total: 31+ queries (scales linearly with result size)
```

**Eager loading strategy**

`DocumentViewSet.get_queryset()` enforces explicit eager loading:

```python
Document.objects.filter(
    Q(owner=user) | Q(memberships__user=user)
).distinct().select_related(
    "owner"
).prefetch_related(
    "memberships__user"
)
```

- **`select_related("owner")`:** Performs a SQL join in the primary query to fetch author data in a single round trip.
- **`prefetch_related("memberships__user")`:** Uses batched `WHERE id IN (...)` queries to load all memberships and nested users in one additional query.

> **Result:** Total database queries stay strictly constant (`O(1)`) whether the endpoint returns 10 or 1,000 documents.

---

## Tiered Rate Limiting & Abuse Prevention (RATE-502)

Public APIs face asymmetric threats: expensive compute operations (like cryptographic password hashing) can be abused for Denial-of-Service (DoS) and credential stuffing. The system implements a **tiered throttling topology** backed by atomic Redis operations:

```text
Incoming HTTP Request
         │
         ▼
[ Throttling Gateway ]
         │
         ├── Unauthenticated (/api/auth/*) ──► ScopedRateThrottle ("auth_anon")
         │                                     Key:   throttle_anon_<client_ip>
         │                                     Limit: 5 requests / minute
         │
         └── Authenticated (/api/documents/*) ─► UserRateThrottle
                                                 Key:   throttle_user_<user_id>
                                                 Limit: 60 requests / minute
```

### Throttling Policy Matrix

| Scope / Class | Target Endpoints | Tracking Key | Rate Limit | Threat Mitigated |
| :-- | :-- | :-- | :-- | :-- |
| **ScopedRateThrottle** (`auth_anon`) | `/api/auth/register/`, `/api/auth/token/` | Client IP (`throttle_anon_<ip>`) | **5 req / min** | Credential stuffing, brute-force guessing, PBKDF2 CPU starvation |
| **UserRateThrottle** | `/api/documents/*` | User PK (`throttle_user_<id>`) | **60 req / min** | Resource starvation, scraper bots; prevents NAT gateway IP collisions on shared subnets |
| **AnonRateThrottle** | Global unauthenticated endpoints | Client IP (`throttle_anon_<ip>`) | **30 req / min** | Broad automated scraping and endpoint scanning |

> **Zero-compute interception:** When a client exceeds quota, DRF intercepts the request before view logic or database execution and returns **`429 Too Many Requests`** with a standard error envelope and a `Retry-After` header. Abusive traffic costs **0 SQL queries**.

---

## Role-Based Access Control (RBAC) Matrix

Object-level access validation is handled by `IsDocumentCollaborator`:

| Operation | Method | Route | Owner | Editor | Viewer | Unauthorized / Anon |
| :-- | :-- | :-- | :-: | :-: | :-: | :-: |
| **List Documents** | `GET` | `/api/documents/` | ✅ | ✅ | ✅ | `401` |
| **Create Document** | `POST` | `/api/documents/` | ✅ | ✅ | ✅ | `401` |
| **Retrieve Document** | `GET` | `/api/documents/<id>/` | ✅ | ✅ | ✅ | `404` |
| **Update Document** | `PUT`, `PATCH` | `/api/documents/<id>/` | ✅ | ✅ | `403` | `404` |
| **Delete Document** | `DELETE` | `/api/documents/<id>/` | ✅ | `403` | `403` | `404` |
| **Manage Members** | `POST` | `/api/documents/<id>/members/` | ✅ | `403` | `403` | `404` |
| **Enqueue Export** | `POST` | `/api/documents/<id>/export/` | ✅ | ✅ | `403` | `404` |

> 🔒 **Security note:** Unauthorized queries on existing documents return `404 Not Found` rather than `403 Forbidden` through strict `get_queryset` filtering, mitigating IDOR identification and object-enumeration attacks.

---

## API Endpoints Reference

All routes require a trailing slash (`/`). Unless noted, endpoints expect `Authorization: Bearer <access_token>`.

### Authentication & Account Identity

| Method | Endpoint | Description | Rate Limit |
| :-- | :-- | :-- | :-- |
| `POST` | `/api/auth/register/` | Register user account | 5 req / min (IP-scoped) |
| `POST` | `/api/auth/token/` | Issue access and refresh JWT pair | 5 req / min (IP-scoped) |
| `POST` | `/api/auth/token/refresh/` | Refresh expired access token | 30 req / min |
| `GET` | `/api/users/me/` | Fetch authenticated profile details | 60 req / min |

### Collaborative Documents

| Method | Endpoint | Description | Status |
| :-- | :-- | :-- | :-- |
| `GET` | `/api/documents/` | Paginated document listing (`O(1)` eager-loaded) | `200 OK` |
| `POST` | `/api/documents/` | Create document (binds `request.user` server-side) | `201 Created` |
| `GET` | `/api/documents/<uuid:id>/` | Retrieve document (Cache-Aside enabled) | `200 OK` |
| `PATCH` | `/api/documents/<uuid:id>/` | Partially update title/content (evicts cache) | `200 OK` |
| `DELETE` | `/api/documents/<uuid:id>/` | Delete document (evicts cache, cascade clean) | `204 No Content` |
| `POST` | `/api/documents/<uuid:id>/members/` | Assign/update member role (viewer/editor) | `200 OK` |
| `POST` | `/api/documents/<uuid:id>/export/` | Enqueue background document export | `202 Accepted` |

### Asynchronous AI Streaming

| Method | Endpoint | Description | Protocol / Format |
| :-- | :-- | :-- | :-- |
| `GET` | `/api/ai/stream/?q=<prompt>` | Non-blocking token generation stream | `application/x-ndjson` (chunked) |

---

## Getting Started

### Prerequisites

- Docker Desktop (with WSL2 integration enabled on Windows)
- Python 3.13 (for local toolchains)
- Git

### Local Containerized Setup (Recommended)

**1. Clone and configure the environment**

```bash
git clone <repository_url> django_backend
cd django_backend
cp .env.example .env
```

**2. Launch the container ecosystem**

```bash
docker compose up --build -d
```

**3. Verify service health**

```bash
docker compose ps
```

**4. Run database migrations inside the container**

```bash
docker compose exec web python manage.py migrate
```

**5. Execute automated quality gates inside the container**

```bash
docker compose exec web pytest
```

The application is now accessible at <http://localhost:8000>.

### Native Local Development (Without Docker)

**1. Environment setup**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

**2. Environment variables**

Create a `.env` file in the project root:

```dotenv
SECRET_KEY=local-dev-insecure-secret-key-32-chars-min
DEBUG=True
DATABASE_URL=postgres://postgres:postgres@localhost:5432/django_db
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

**3. Start the ASGI server**

```bash
uvicorn config.asgi:application --host 127.0.0.1 --port 8000 --reload
```

**4. Launch the Celery worker** (in a separate terminal)

```bash
celery -A config worker --loglevel=info
```

---

## Quality Gates & Verification

Every pull request must pass the static type, linting, and automated testing suites:

```bash
# 1. Static type checking (strict mypy)
mypy core config documents

# 2. Fast lint & import verification
ruff check .

# 3. Test suite (RBAC, cache eviction, Celery tasks, query limits)
pytest
```

---

## Engineering Sprint Changelog

| Ticket | Summary |
| :-- | :-- |
| **AUTH-201** | Custom User Model with UUID primary key, PostgreSQL integration, and zero schema drift. |
| **AUTH-202** | User registration endpoint with serializer validation and transaction boundaries. |
| **AUTH-203** | Stateless JWT authentication and protected profile endpoint. |
| **DOC-301** | Domain modeling, relational integrity, and query performance (`Document` entity, role-based `DocumentMember`, compound unique constraints, B-tree indexing). |
| **DOC-302** | Documents CRUD API, atomic ownership ingestion, multi-tenant scope isolation, and N+1 query elimination (`select_related`, `prefetch_related`). |
| **DOC-303** | Granular object-level permissions (`IsDocumentCollaborator`), member delegation endpoint (`/members/`), and owner-only destruction protections. |
| **TEST-401** | Automated testing harness and CI quality gates (pytest-django, factory_boy factories, RBAC matrix regression tests, query-count assertions). |
| **CACHE-501** | In-memory caching layer (django-redis, Cache-Aside, zero-query subsequent reads, proactive invalidation). |
| **RATE-502** | Tiered rate limiting and abuse prevention (Redis sliding-window throttling, scoped IP protection against brute-force hashing, user quotas, zero-SQL 429 interception). |
| **ASYNC-601** | ASGI engine migration and async non-blocking LLM streaming via `DocumentAiStreamView` using chunked `application/x-ndjson`. |
| **TASK-602** | Celery + Redis async task infrastructure with retries, structured telemetry, and non-blocking export jobs. |
| **DEVOPS-603** | Multi-container Docker infrastructure with Python 3.13-slim, Redis 7, and `pgvector/pgvector:pg16` database nodes. |
