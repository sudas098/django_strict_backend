# **Collaborative Document Backend API & Asynchronous AI Engine**

A strict, production-grade Django backend built with modern asynchronous concurrency (ASGI), LLM token streaming, Celery task distribution, vector similarity support (pgvector), in-memory Redis caching, tiered rate limiting, and static type safety as first-class architectural concerns.

## **System Architecture Highlights**

Plaintext  
                                  ┌───────────────────────────────────────────────┐  
                                  │           Reverse Proxy / Gateway             │  
                                  │             (e.g., Nginx / ALB)               │  
                                  └───────┬───────────────────────────────┬───────┘  
                                          │                               │  
                HTTP REST (Sync/Cached)   │                               │ Async Event-Stream / NDJSON  
                                          ▼                               ▼  
                 ┌─────────────────────────────────────────────────────────────────┐  
                 │                   Uvicorn (ASGI Application Server)             │  
                 │ ┌───────────────────────────┐     ┌───────────────────────────┐ │  
                 │ │     Django REST Layer     │     │  Async LLM Streaming View │ │  
                 │ │     (CRUD, Auth, RBAC)    │     │      (ai\_views.py)        │ │  
                 │ └─────────────┬─────────────┘     └─────────────┬─────────────┘ │  
                 └───────────────┼─────────────────────────────────┼───────────────┘  
                                 │                                 │ Non-blocking  
                                 ▼                                 ▼ (Event Loop)  
                 ┌─────────────────────────────┐     ┌───────────────────────────┐  
                 │       Redis (In-Memory)     │     │ External AI Model Gateway │  
                 │  \- Cache-Aside (TTL 300s)   │     │    (OpenAI / Anthropic)   │  
                 │  \- Sliding-Window Throttles │     └───────────────────────────┘  
                 │  \- Celery Message Broker    │  
                 └───────────────┬─────────────┘  
                                 │  
                 ┌───────────────┴─────────────┐  
                 │                             │  
                 ▼                             ▼  
  ┌─────────────────────────────┐ ┌───────────────────────────────────────────────┐  
  │   Celery Distributed Pool   │ │          PostgreSQL 16 \+ pgvector             │  
  │  (Heavy Exports / CPU Work) │ │   \- Relational Core & Foreign Key Cascades    │  
  │      (documents/tasks.py)   │ │   \- B-tree Indexes & Composite Constraints    │  
  └─────────────────────────────┘ │   \- High-Dimensional Vector Embeddings        │  
                                  └───────────────────────────────────────────────┘

* **Modern Asynchronous Concurrency (ASGI)**: Powered by Uvicorn, liberating the runtime from synchronous WSGI thread-starvation constraints during long-lived I/O operations.  
* **Non-Blocking LLM Token Streaming (ai\_views.py)**: Uses Python asyncio primitives and Django’s StreamingHttpResponse to deliver real-time token chunks via Newline Delimited JSON (NDJSON) with zero thread-blocking overhead.  
* **Distributed Asynchronous Worker Pipeline (Celery \+ Redis)**: Heavy CPU and slow I/O workloads (e.g., document exports) are offloaded to distributed background workers, returning an immediate 202 Accepted to callers.  
* **AI-Ready Relational Persistence (pgvector/pgvector:pg16)**: Production PostgreSQL database equipped with native vector similarity search extensions for future-proof RAG pipelines and semantic retrieval.  
* **Fully Containerized Infrastructure**: Deterministic multi-container topology orchestrating the ASGI backend, Redis broker/cache, and pgvector-enabled database via Docker Compose.  
* **Object-Level RBAC Enforcement**: Method-level capability checks via IsDocumentCollaborator guaranteeing owner-only deletion and editor-only mutation semantics.  
* **High-Throughput Redis Cache-Aside**: In-memory caching layer with automatic invalidation hooks on updates and deletes, maintaining constant $O(1)$ query complexity on warm reads.  
* **Tiered Rate Limiting & Abuse Defense**: Redis-backed sliding-window throttles protecting public auth routes against brute-force attacks and authenticated endpoints against resource exhaustion.  
* **Zero $N+1$ Query Architecture**: Enforced relational eager loading (select\_related, prefetch\_related) eliminating linear query escalation.  
* **Strict Static Typing**: Configured with strict mypy (integrating django-stubs and djangorestframework-stubs) to prevent runtime type exceptions.

## **Tech Stack**

| Domain | Technology | Operational Purpose |
| :---- | :---- | :---- |
| **Runtime & Framework** | Python 3.13, Django 5.2, DRF | High-productivity backend framework with strict relational ORM |
| **Application Server** | Uvicorn (ASGI) | Single-threaded non-blocking event-loop for concurrent I/O & streaming |
| **Database & Vector Engine** | PostgreSQL 16 \+ pgvector | Relational consistency (ACID) paired with high-dimensional vector search |
| **In-Memory Broker & Cache** | Redis 7 (Alpine) | Sub-millisecond cache-aside storage, Celery task queue, and sliding throttles |
| **Task Queue** | Celery | Distributed background job processing for non-blocking exports |
| **Containerization** | Docker, Docker Compose | Reproducible environments across development and production |
| **Testing Harness** | pytest, pytest-django, factory\_boy | Automated integration testing, mock factories, and query budget assertions |
| **Code Quality** | mypy (strict), ruff | Compile-time type verification and ultra-fast code styling |

## **Architecture & Relational Domain Model**

### **Entity-Relationship Diagram**

Plaintext  
\+------------------------------------+  
|             CustomUser             |  
\+------------------------------------+  
| id          : UUID (PK)            |  
| email       : EmailField (Unique)  |  
| is\_active   : BooleanField         |  
| date\_joined : DateTimeField        |  
\+------------------------------------+  
         │ 1                      │ 1  
         │ (owner)                │ (member)  
         │ N                      │ N  
         ▼                        ▼  
\+-----------------------+        \+-----------------------------------+  
|       Document        |        |          DocumentMember           |  
\+-----------------------+        \+-----------------------------------+  
| id         : UUID (PK)|        | id          : UUID (PK)           |  
| title      : CharField|◄───────┤ document\_id : FK \-\> Document      |  
| content    : TextField| 1      | user\_id     : FK \-\> CustomUser    |  
| owner\_id   : FK \-\> User        | role        : Enum(viewer, editor)|  
| created\_at : DateTime │        | created\_at  : DateTime            |  
| updated\_at : DateTime │        \+-----------------------------------+  
\+-----------------------+               Constraint: UNIQUE(doc, user)

### **Relational Design Decisions**

> 1. **Foreign Key Cascade Lifecycles (on\_delete=models.CASCADE)**:  
   * Deleting an **owner** cascades to purge all their authored Document records.  
   * Deleting a **collaborator user** cleans up their membership record (DocumentMember) without deleting or corrupting the shared Document.  
   * Deleting a **document** automatically cleans up all child DocumentMember entries, preventing orphaned ACL records.  
> 2. **Compound Unique Constraints**:  
   * Enforced at the database engine level via models.UniqueConstraint(fields=\["document", "user"\], name="unique\_document\_member") to prevent race conditions during permission assignment.  
> 3. **Indexing Strategy**:  
   * Dedicated B-tree indexes on owner\_id, created\_at, and title to accelerate WHERE filtering and ordered pagination scans (ORDER BY created\_at DESC).

## **Architectural Deep Dives**

### **1\. Asynchronous LLM Streaming Architecture (ai\_views.py)**

Traditional WSGI servers dedicate one operating system worker thread per HTTP request. When an endpoint interacts with a generative AI provider taking 3 to 10 seconds to generate completions, WSGI threads remain completely idle waiting for network packets—causing rapid thread starvation, latency spikes, and socket timeouts under minimal concurrent load.  
To resolve this, core/ai\_views.py establishes an asynchronous streaming pipeline:

Python  
class DocumentAiStreamView(APIView):  
    permission\_classes \= \[IsAuthenticated\]

    async def get(self, request: Request) \-\> StreamingHttpResponse:  
        prompt \= request.query\_params.get("q", "Summarize document")

        async def response\_stream() \-\> AsyncGenerator\[str, None\]:  
            async for token in MockAiStreamService.stream\_tokens(prompt):  
                yield token

        response \= StreamingHttpResponse(  
            response\_stream(),  
            content\_type="application/x-ndjson",  
        )  
        response\["Cache-Control"\] \= "no-cache"  
        response\["X-Accel-Buffering"\] \= "no"  
        return response

#### **Key Engineering Decisions**

* **Non-Blocking Cooperative Scheduling**: Downstream calls yield execution via await asyncio.sleep(). While waiting on upstream model tokens, the single worker process continues handling other concurrent requests on the event loop.  
* **Transfer Protocol**: Employs **HTTP Chunked Transfer Encoding** returning Newline Delimited JSON (application/x-ndjson). This allows clients to stream, parse, and render markdown tokens dynamically.  
* **Reverse-Proxy Buffer Bypass (X-Accel-Buffering: no)**: Nginx and edge CDNs buffer responses in 4KB/8KB chunks by default. Setting this header explicitly forces proxies to flush individual token packets to the client immediately, preserving the typewriter UI effect.

### **2\. Distributed Task Queue & Decoupled Workers (documents/tasks.py)**

Workloads involving disk writes, report compilation, or PDF generation must never run inside the web application's synchronous request-response loop.

Python  
@shared\_task(bind=True, max\_retries=3)  \# type: ignore\[misc\]  
def process\_document\_export(  
    self: Any,  
    document\_id: str,  
) \-\> dict\[str, str\]:  
    """Simulate heavy background export generation for a document."""  
    try:  
        doc \= Document.objects.get(id\=document\_id)  
        logger.info(  
            "document\_export\_started",  
            extra={"document": str(doc.id), "document\_title": doc.title},  
        )  
        time.sleep(3)  \# Heavy file compilation workload  
        return {  
            "status": "completed",  
            "document\_id": str(doc.id),  
            "export\_url": f"https\://storage.cdn.company.internal/exports/{doc.id}.pdf",  
        }  
    except Document.DoesNotExist as exc:  
        logger.error("document\_not\_found", extra={"document\_id": document\_id})  
        raise exc

* **Asynchronous Offloading**: The API endpoint enqueues the task onto Redis and immediately dispatches an HTTP 202 Accepted response with a task reference, keeping API p99 latency minimal.  
* **Separation of Concerns**: CPU-bound tasks use standard worker threads (time.sleep) in an isolated Celery pool, completely segregated from the event loop of the Uvicorn ASGI server.

### **3\. Containerized Topology (Docker & Compose)**

The backend runs as an orchestrated set of containers configured to mirror production network topologies:

Plaintext  
\[ Docker Network: django\_backend\_default \]  
 ├── web      (python:3.13-slim \+ Uvicorn ASGI, ports: 8000:8000)  
 ├── redis    (redis:7-alpine, ports: 6379:6379)  
 └── db       (pgvector/pgvector:pg16, ports: 5432:5432)

* **Database Engine**: Uses the official pgvector/pgvector:pg16 image, enabling Postgres extension provisioning (CREATE EXTENSION IF NOT EXISTS vector;) for semantic embedding search.  
* **Deterministic Startup Orchestration**: Uses Compose health checks (pg\_isready \-U postgres) and service dependency conditions (condition: service\_healthy) to ensure the Django backend never attempts migrations or server starts until PostgreSQL and Redis have passed readiness probes.  
* **Production Build Hygiene**: Multi-stage layer caching ensures that system dependencies (libpq-dev, build-essential) and Python requirements are compiled before source code ingestion, minimizing container build duration.

### **4\. High-Performance Caching & Cache-Aside Architecture**

High-throughput read endpoints that mutate rarely (GET /api/documents/{id}/) are decoupled from direct PostgreSQL execution using an **in-memory Cache-Aside (Lazy Loading)** design pattern.

Plaintext  
GET /api/documents/{id}/  
     │  
     ▼  
\[ Check Cache (Key: "doc:{id}") \]  
     │  
     ├── HIT  ──► Return cached JSON directly (0 SQL queries executed)  
     │  
     └── MISS ──► 1\. Query PostgreSQL via ORM (enforcing RBAC permission checks)  
                  2\. Serialize payload  
                  3\. Store in Redis (TTL: 300s)  
                  4\. Return JSON response

PATCH / PUT / DELETE /api/documents/{id}/  
     │  
     ▼  
1\. Mutate / Delete record in PostgreSQL  
2\. Evict / Invalidate cache key: cache.delete(f"doc:{id}")

#### **Invalidation Policy & Fault Tolerance**

* **Deterministic Cache Keys**: Formatted as doc:{id} to establish discrete namespace boundaries.  
* **Proactive Invalidation**: Handled in view lifecycle hooks (perform\_update and perform\_destroy), guaranteeing that stale representations never outlive a write transaction.  
* **Fail-Open Resilience**: Configured with IGNORE\_EXCEPTIONS \= True and strict connection timeouts (5s). If the Redis cluster encounters downtime, the backend automatically falls back to direct database execution rather than dropping user requests.  
* **Isolated Testing Environment**: During pytest sessions, cache backend cleanly routes to Django's in-memory LocMemCache, eliminating network dependencies while validating eviction behavior.

### **5\. Performance & Query Optimization ($O(1)$ Constant Queries)**

When serializing relational models with nested representations, naïve ORM queries trigger the $N+1$ **query problem**, firing 1 initial query for the list and $N$ individual queries for each related foreign key:

SQL  
\-- Naïve execution without eager loading (fetching 10 documents with 2 members each):  
SELECT \* FROM documents;                     \-- 1 query  
SELECT \* FROM users WHERE id \= ...;          \-- 10 queries (one per owner)  
SELECT \* FROM document\_members WHERE ...;    \-- 10 queries (one per document)  
SELECT \* FROM users WHERE id IN (...);       \-- 10 queries (nested member users)  
\-- Total: 31+ queries (scales linearly with result size)

#### **Eager Loading Strategy**

To eliminate linear query amplification and preserve low latency under concurrent traffic, DocumentViewSet.get\_queryset() enforces explicit eager loading:

Python  
Document.objects.filter(  
    Q(owner=user) | Q(memberships\_\_user=user)  
).distinct().select\_related(  
    "owner"  
).prefetch\_related(  
    "memberships\_\_user"  
)

* **select\_related("owner")**: Performs an SQL INNER JOIN in the primary query to retrieve author data in a single roundtrip.  
* **prefetch\_related("memberships\_\_user")**: Uses batched SQL WHERE id IN (...) queries to load all memberships and nested user representations in 1 additional query.

**Result**: Total database queries remain strictly **constant ($O(1)$)** regardless of whether the endpoint returns 10 or 1,000 documents.

## **Tiered Rate Limiting & Abuse Prevention (RATE-502)**

Public APIs face asymmetric threats: expensive compute operations (like cryptographic password hashing) can be abused to cause Denial-of-Service (DoS) and credential stuffing. The system implements a **tiered throttling topology** backed by atomic Redis operations:

Plaintext  
Incoming HTTP Request  
         │  
         ▼  
\[ Throttling Gateway \]  
         │  
         ├── Unauthenticated (/api/auth/\*) ──► ScopedRateThrottle ("auth\_anon")  
         │                                      Key: throttle\_anon\_\<client\_ip\>  
         │                                      Limit: 5 requests / minute  
         │  
         └── Authenticated (/api/documents/\*) ─► UserRateThrottle  
                                                 Key: throttle\_user\_\<user\_id\>  
                                                 Limit: 60 requests / minute

### **Throttling Policy Matrix**

| Scope / Class | Target Endpoints | Tracking Key | Rate Limit | Threat Mitigated |
| :---- | :---- | :---- | :---- | :---- |
| **ScopedRateThrottle** (auth\_anon) | /api/auth/register/, /api/auth/token/  | Client IP Address (throttle\_anon\_\<ip\>) | **5 req / minute**  | Credential stuffing, brute-force password guessing, PBKDF2 CPU starvation |
| **UserRateThrottle** | /api/documents/\*  | Authenticated user.pk (throttle\_user\_\<id\>) | **60 req / minute**  | Resource starvation, scraper bots; prevents NAT gateway IP collisions across shared subnets |
| **AnonRateThrottle** | Global unauthenticated endpoints | Client IP Address (throttle\_anon\_\<ip\>) | **30 req / minute**  | Broad automated scraping and endpoint scanning |

* **Zero-Compute Interception**: When a client exceeds their quota, DRF intercepts the request before view logic or database execution, instantly returning **429 Too Many Requests** along with a standard error envelope and a Retry-After header. Abusive traffic costs **0 SQL queries**.

## **Role-Based Access Control (RBAC) Matrix**

Object-level access validation handled by IsDocumentCollaborator:

| Operation | HTTP Method | Route | Owner | Editor | Viewer | Unauthorized / Anon |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **List Documents** | GET | /api/documents/ | Allowed | Allowed | Allowed | 401 Unauthorized |
| **Create Document** | POST | /api/documents/ | Allowed | Allowed | Allowed | 401 Unauthorized |
| **Retrieve Document** | GET | /api/documents/\<id\>/ | Allowed | Allowed | Allowed | 404 Not Found  |
| **Update Document** | PUT, PATCH  | /api/documents/\<id\>/ | Allowed | Allowed | 403 Forbidden  | 404 Not Found  |
| **Delete Document** | DELETE  | /api/documents/\<id\>/ | Allowed | 403 Forbidden  | 403 Forbidden  | 404 Not Found  |
| **Manage Members** | POST  | /api/documents/\<id\>/members/ | Allowed | 403 Forbidden  | 403 Forbidden  | 404 Not Found  |
| **Enqueue Export** | POST | /api/documents/\<id\>/export/ | Allowed | Allowed | 403 Forbidden | 404 Not Found |

*Security Note: Unauthorized queries on existing documents return 404 Not Found rather than 403 Forbidden through strict get\_queryset filtering, mitigating IDOR identification and object-enumeration attacks.*

## **API Endpoints Reference**

All routes require a trailing slash (/). Unless noted, all endpoints expect Authorization: Bearer \<access\_token\>.

### **Authentication & Account Identity**

| Method | Endpoint | Description | Rate Limit |
| :---- | :---- | :---- | :---- |
| POST | /api/auth/register/  | Register user account | 5 req / min (IP-scoped) |
| POST | /api/auth/token/  | Issue access and refresh JWT pair | 5 req / min (IP-scoped) |
| POST | /api/auth/token/refresh/  | Refresh expired access token | 30 req / min |
| GET | /api/users/me/  | Fetch authenticated profile details | 60 req / min |

### **Collaborative Documents**

| Method | Endpoint | Description | Response Status |
| :---- | :---- | :---- | :---- |
| GET | /api/documents/  | Paginated document listing ($O(1)$ eager-loaded) | 200 OK |
| POST | /api/documents/  | Create document (binds request.user server-side) | 201 Created |
| GET | /api/documents/\<uuid:id\>/  | Retrieve document (Cache-Aside enabled) | 200 OK |
| PATCH | /api/documents/\<uuid:id\>/  | Partially update title/content (evicts cache) | 200 OK |
| DELETE | /api/documents/\<uuid:id\>/  | Delete document (evicts cache, cascade clean) | 204 No Content |
| POST | /api/documents/\<uuid:id\>/members/  | Assign/update member role (viewer/editor) | 200 OK |
| POST | /api/documents/\<uuid:id\>/export/ | Enqueue background document export | 202 Accepted |

### **Asynchronous AI Streaming**

| Method | Endpoint | Description | Protocol / Format |
| :---- | :---- | :---- | :---- |
| GET | /api/ai/stream/?q=\<prompt\> | Non-blocking token generation stream | application/x-ndjson (Chunked) |

## **Getting Started**

### **Prerequisites**

* Docker Desktop (with WSL2 integration enabled on Windows)  
* Python 3.13 (for local toolchains)  
* Git

### **Local Containerized Setup (Recommended)**

> 1. **Clone and Configure Environment**:  
>    Bash  
>    git clone \<repository\_url\> django\_backend  
>    cd django\_backend  
>    cp .env.example .env

> 2. **Launch Container Ecosystem**:  
>    Bash  
>    docker compose up \--build \-d

> 3. **Verify Service Health**:  
>    Bash  
>    docker compose ps

> 4. **Run Database Migrations Inside Container**:  
>    Bash  
>    docker compose exec web python manage.py migrate

> 5. **Execute Automated Quality Gates Inside Container**:  
>    Bash  
>    docker compose exec web pytest

The application is now accessible at http\://localhost:8000.

### **Native Local Development (Without Docker)**

> 1. **Environment Setup**:  
>    Bash  
>    python \-m venv .venv  
>    source .venv/bin/activate  \# On Windows: .venv\\Scripts\\activate  
>    pip install \--upgrade pip  
>    pip install \-r requirements.txt

> 2. **Environment Variables**:  
>    Create a .env file in the root directory:  
>    Code snippet  
>    SECRET\_KEY=local-dev-insecure-secret-key-32-chars-min  
>    DEBUG=True  
>    DATABASE\_URL=postgres://postgres:postgres@localhost:5432/django\_db  
>    REDIS\_URL=redis://localhost:6379/0  
>    CELERY\_BROKER\_URL=redis://localhost:6379/0  
>    CELERY\_RESULT\_BACKEND=redis://localhost:6379/0

> 3. **Start the ASGI Server**:  
>    Bash  
>    uvicorn config.asgi:application \--host 127.0.0.1 \--port 8000 \--reload

> 4. **Launch Background Celery Worker** (in a separate terminal):  
>    Bash  
>    celery \-A config worker \--loglevel=info

## **Quality Gates & Verification**

Every pull request must pass the static type safety, linting, and automated testing suites:

Bash  
\# 1\. Static Type Checking (Strict Mypy)  
mypy core config documents

\# 2\. Fast Lint & Import Verification  
ruff check .

\# 3\. Test Suite (RBAC, Cache Eviction, Celery Tasks, Query Limits)  
pytest

## **Engineering Sprint Changelog**

* **AUTH-201**: Custom User Model with UUID Primary Key, PostgreSQL Integration, and Zero Schema Drift.  
* **AUTH-202**: User Registration Endpoint with Serializer Validation & Transaction Boundaries.  
* **AUTH-203**: Stateless JWT Authentication & Protected Profile Endpoint.  
* **DOC-301**: Domain Modeling, Relational Integrity & Query Performance (Document entity, role-based DocumentMember, compound unique constraints, and B-tree indexing).  
* **DOC-302**: Documents CRUD API, Atomic Ownership Ingestion, Multi-Tenant Scope Isolation & $N+1$ Query Elimination (select\_related, prefetch\_related).  
* **DOC-303**: Granular Object-Level Permissions (IsDocumentCollaborator), Member Delegation Endpoint (/members/), and Owner-Only Destruction Protections.  
* **TEST-401**: Enterprise Automated Testing Harness & CI Quality Gates (pytest-django, factory\_boy dynamic model factories, RBAC matrix regression testing, and query-count assertions).  
* **CACHE-501**: High-Throughput In-Memory Caching Layer (django-redis, Cache-Aside pattern, zero-query subsequent reads, and proactive cache invalidation policies).  
* **RATE-502**: Tiered Rate Limiting & Abuse Prevention (Redis atomic sliding-window throttling, scoped public IP protection against brute-force hashing, user quotas, and zero-SQL 429 interception).  
* **ASYNC-601**: ASGI Engine Migration & Asynchronous Non-Blocking LLM Streaming Pipeline via DocumentAiStreamView using Chunked application/x-ndjson.  
* **TASK-602**: Celery \+ Redis Asynchronous Task Infrastructure with Task Retries, Structured Telemetry, and Non-blocking Export Jobs.  
* **DEVOPS-603**: Multi-Container Docker Infrastructure Provisioning with Python 3.13-slim, Redis 7, and pgvector/pgvector:pg16 Database Nodes.