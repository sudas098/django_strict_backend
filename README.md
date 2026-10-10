# Collaborative Document Backend API

A strict, production-grade Django REST Framework backend built with security, relational data integrity, $O(1)$ query optimization, in-memory Redis caching, and static type safety as first-class architectural concerns.

## Architecture Highlights

* **Custom Identity Architecture**: Custom User model using UUIDv4 primary keys (neutralizing sequential ID enumeration and IDOR attack surfaces), RFC-compliant email authentication, and transactional user provisioning.
* **Stateless JWT Security**: Dual-token flow via `djangorestframework-simplejwt` with short-lived access tokens (15 minutes) and rolling refresh tokens (1 day) using standard HMAC/RSA signing.
* **Collaborative Multi-Tenant Domain**: Relational access model supporting document ownership and granular role-based memberships (`viewer`, `editor`).
* **Database-Level Integrity Guarantees**: Compound unique constraints preventing duplicate role allocations, explicit foreign key cascade lifecycles, and composite B-tree indexes for fast filtering and sorted lookups.
* **Multi-Tenant Scope Isolation**: Queryset filtering (`get_queryset`) strictly enforces that callers can only discover documents they own or actively collaborate on. Requests targeting unauthorized UUIDs return `404 Not Found` rather than `403`, eliminating resource enumeration leaks.
* **Object-Level RBAC Enforcement**: Custom permission class (`IsDocumentCollaborator`) checks method-level capabilities per object, guaranteeing that deletions are owner-only and mutations require editor privileges.
* **Zero $N+1$ Query Architecture**: Relational fetching optimized down to constant $O(1)$ database hits via `select_related` and `prefetch_related`.
* **High-Throughput Redis Cache-Aside Layer**: In-memory caching layer backed by Redis (`django-redis`) with strict Time-To-Live (TTL: 300s) and proactive cache eviction on update (`PATCH`/`PUT`) and deletion (`DELETE`).
* **Automated CI Quality Gates & Testing**: Complete integration test harness using `pytest`, `pytest-django`, and `factory_boy` dynamic model fixtures to validate RBAC rules, verify zero-query cache hits, and assert query budgets with zero mocking.
* **Resilient Infrastructure Design**: Cloud database provisioning via Neon (PostgreSQL) with connection pooling (`conn_max_age=600`) paired with fail-open Redis connection options (`IGNORE_EXCEPTIONS = True`).
* **Strict Quality Tooling**: Static typing enforced across all modules via `mypy` (`django-stubs`, `djangorestframework-stubs`), fast code style and import hygiene via `ruff`, and strict environment validation via Pydantic Settings.

## Tech Stack

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Framework** | Django 5.2 + DRF | Mature ORM, battle-tested security defaults, and flexible viewset architecture |
| **Database** | PostgreSQL (Neon Serverless) | ACID transactions, native UUIDv4, robust connection pooling |
| **Cache Engine** | Redis + `django-redis` | Sub-millisecond read latency, high-throughput memory storage, atomic evictions |
| **Authentication** | `djangorestframework-simplejwt` | Stateless horizontally scalable token authentication |
| **Testing Suite** | `pytest`, `pytest-django`, `factory_boy`, `Faker` | Fast test execution, isolated database states, schema-resilient fixtures |
| **Static Analysis** | `mypy` (strict mode with `django-stubs`) | Compile-time type verification, catching `None` dereferences before runtime |
| **Linter & Formatter** | `ruff` | Ultra-fast PEP 8 and import order compliance |
| **Configuration** | Pydantic Settings | Fail-fast runtime environment variable validation |

---

## Architecture & Relational Domain Model

### Entity-Relationship Diagram

```text
+------------------------------------+
|             CustomUser             |
+------------------------------------+
| id          : UUID (PK)            |
| email       : EmailField (Unique)  |
| is_active   : BooleanField         |
| date_joined : DateTimeField        |
+------------------------------------+
         | 1                      | 1
         | (owner)                | (member)
         | N                      | N
         v                        v
+-----------------------+        +-----------------------------------+
|       Document        |        |          DocumentMember           |
+-----------------------+        +-----------------------------------+
| id         : UUID (PK)|        | id          : UUID (PK)           |
| title      : CharField|<-------| document_id : FK -> Document      |
| content    : TextField| 1      | user_id     : FK -> CustomUser    |
| owner_id   : FK -> User        | role        : Enum(viewer, editor)|
| created_at : DateTime |        | created_at  : DateTime            |
| updated_at : DateTime |        +-----------------------------------+
+-----------------------+               Constraint: UNIQUE(doc, user)
```

### Relational Design Decisions

1. **Foreign Key Cascade Lifecycles (`on_delete=models.CASCADE`)**:
   * Deleting an **owner** cascades to purge all their authored `Document` records.
   * Deleting a **collaborator user** cleans up their membership record (`DocumentMember`) without deleting or corrupting the shared `Document`.
   * Deleting a **document** automatically cleans up all child `DocumentMember` entries, preventing orphaned ACL records.
2. **Compound Unique Constraints**:
   * Enforced at the database engine level via `models.UniqueConstraint(fields=["document", "user"], name="unique_document_member")` to prevent race conditions during permission assignment.
3. **Indexing Strategy**:
   * Dedicated B-tree indexes on `owner_id`, `created_at`, and `title` to accelerate `WHERE` filtering and ordered pagination scans (`ORDER BY created_at DESC`).

---

## Role-Based Access Control (RBAC) Matrix

Object-level access rules enforced via `IsDocumentCollaborator`:

| Operation | HTTP Method | Document Owner | Collaborator (`editor`) | Collaborator (`viewer`) | Non-Member / Anonymous |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **View Document** | `GET`, `HEAD`, `OPTIONS` | Allowed | Allowed | Allowed | `404 Not Found` / `401` |
| **Update Document** | `PUT`, `PATCH` | Allowed | Allowed | `403 Forbidden` | `404 Not Found` / `401` |
| **Delete Document** | `DELETE` | Allowed | `403 Forbidden` | `403 Forbidden` | `404 Not Found` / `401` |
| **Manage Members** | `POST /members/` | Allowed | `403 Forbidden` | `403 Forbidden` | `404 Not Found` / `401` |

---

## High-Performance Caching & Cache-Aside Architecture

High-throughput read endpoints that mutate rarely (`GET /api/documents/{id}/`) are decoupled from direct PostgreSQL execution using an **in-memory Cache-Aside (Lazy Loading)** design pattern.

### Cache-Aside Sequence Flow

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
1. Mutate / Delete record in PostgreSQL
2. Evict / Invalidate cache key: cache.delete(f"doc:{id}")
```

### Invalidation Policy & Fault Tolerance
* **Deterministic Cache Keys**: Formatted as `doc:{id}` to establish discrete namespace boundaries.
* **Proactive Invalidation**: Handled in view lifecycle hooks (`perform_update` and `perform_destroy`), guaranteeing that stale representations never outlive a write transaction.
* **Fail-Open Resilience**: Configured with `IGNORE_EXCEPTIONS = True` and strict connection timeouts (5s). If the Redis cluster encounters downtime, the backend automatically falls back to direct database execution rather than dropping user requests.
* **Isolated Testing Environment**: During `pytest` sessions, cache backend cleanly routes to Django's in-memory `LocMemCache`, eliminating network dependencies while validating eviction behavior.

---

## Performance & Query Optimization ($O(1)$ Constant Queries)

When serializing relational models with nested representations, naïve ORM queries trigger the **$N+1$ query problem**, firing 1 initial query for the list and $N$ individual queries for each related foreign key:

```sql
-- Naïve execution without eager loading (fetching 10 documents with 2 members each):
SELECT * FROM documents;                     -- 1 query
SELECT * FROM users WHERE id = ...;          -- 10 queries (one per owner)
SELECT * FROM document_members WHERE ...;    -- 10 queries (one per document)
SELECT * FROM users WHERE id IN (...);       -- 10 queries (nested member users)
-- Total: 31+ queries (scales linearly with result size)
```

### Eager Loading Strategy

To eliminate linear query amplification and preserve low latency under concurrent traffic, `DocumentViewSet.get_queryset()` enforces explicit eager loading:

```python
Document.objects.filter(
    Q(owner=user) | Q(memberships__user=user)
).distinct().select_related(
    "owner"
).prefetch_related(
    "memberships__user"
)
```

* **`select_related("owner")`**: Performs an SQL `INNER JOIN` in the primary query to retrieve author data in a single roundtrip.
* **`prefetch_related("memberships__user")`**: Uses batched SQL `WHERE id IN (...)` queries to load all memberships and nested user representations in 1 additional query.

**Result:** Total database queries remain strictly **constant ($O(1)$)** regardless of whether the endpoint returns 10 or 1,000 documents.

---

## Security Architecture: Ownership Injection & Scope Isolation

1. **Scope Isolation (`get_queryset`)**:
   Clients cannot access documents outside their authorization boundary. Queries are filtered using an `OR` condition (`Q(owner=request.user) | Q(memberships__user=request.user)`) combined with `.distinct()`, preventing cross-tenant leakage. Requests targeting unauthorized UUIDs return `404 Not Found` to prevent object existence enumeration.
2. **Server-Side Ownership Injection (`perform_create`)**:
   Clients are **never** trusted to provide the `owner` field in the request payload. The input serializer (`DocumentCreateUpdateSerializer`) strictly limits input fields to `["title", "content"]`, while `perform_create` automatically binds the verified JWT principal (`request.user`) server-side:
   ```python
   def perform_create(self, serializer: Any) -> None:
       serializer.save(owner=self.request.user)
   ```
3. **Decoupled Read/Write DTOs (`get_serializer_class`)**:
   * `DocumentCreateUpdateSerializer`: Sanitized write-only boundary that ignores read-only metadata.
   * `DocumentSerializer`: Detailed read-only DTO exposing full nested user profiles and membership ACL details.
   * `DocumentMemberAddSerializer`: Validates target collaborator email and role constraints before updating membership tables.

---

## Automated Testing & CI Quality Gates

Enterprise systems enforce regression protection via automated integration tests rather than manual verification. The test suite leverages `pytest-django` and `factory_boy` dynamic model factories to construct isolated test fixtures in milliseconds.

### Model Factories (`factory_boy`)

Dynamic model generation abstracts fixture boilerplate and shields tests from schema changes:
* **`UserFactory`**: Creates valid `CustomUser` instances with sequence-generated emails (`user{n}@example.com`) and hashed passwords.
* **`DocumentFactory`**: Creates `Document` instances with randomized sentences and paragraphs using `factory.Faker`.
* **`DocumentMemberFactory`**: Generates membership ACL relations linked via `factory.SubFactory`.

### Verified Test Suites

#### 1. RBAC & $N+1$ Performance Tests (`documents/tests/test_rbac.py`)
* `test_owner_can_delete_document`: Asserts that an authenticated document owner can issue a `DELETE` request (`204 No Content`).
* `test_viewer_cannot_update_document`: Asserts that an authenticated collaborator with role `viewer` attempting a `PATCH` request is blocked with `403 Forbidden`.
* `test_viewer_cannot_delete_document`: Asserts that an authenticated collaborator with role `viewer` attempting a `DELETE` request is blocked with `403 Forbidden`.
* `test_editor_can_update_document`: Asserts that an authenticated collaborator with role `editor` successfully updates the document title (`200 OK`).
* `test_list_documents_avoids_n_plus_one`: Asserts via `django_assert_num_queries` that listing 10 documents with 20 nested members executes in a fixed query budget, guaranteeing $O(1)$ query scalability.

#### 2. Caching & Invalidation Tests (`documents/tests/test_cache.py`)
* `test_retrieve_uses_cache_on_subsequent_reads`: Asserts that an initial `GET` hits the database, while the immediate subsequent `GET` triggers a cache hit executing **exactly 0 database queries**.
* `test_update_invalidates_cache`: Asserts that mutating a document via `PATCH` evicts the associated `doc:{id}` key from the cache, preventing stale reads.

---

## Setup & Local Development

### 1. Environment & Dependencies

```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate   # Windows PowerShell
# source .venv/bin/activate # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-super-secret-key-change-me
DEBUG=True
DATABASE_URL=postgresql://<user>:<password>@<neon-endpoint>.neon.tech/<dbname>?sslmode=require
REDIS_URL=redis://127.0.0.1:6379/1
```

### 3. Migrations & Server

```powershell
# Run migrations against Neon PostgreSQL
python manage.py makemigrations
python manage.py migrate

# Start the dev server
python manage.py runserver
```

### 4. Running Quality Gates

```powershell
# Run full automated test suite (RBAC + Caching)
pytest

# Static typing verification
mypy core config documents

# Fast linting and format inspection
ruff check .
```

---

## API Endpoints Reference

### Authentication & Identity

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Register new user account | No |
| `POST` | `/api/auth/token` | Obtain JWT pair (access + refresh) | No |
| `POST` | `/api/auth/token/refresh` | Refresh access token | No |
| `GET` | `/api/users/me` | Fetch authenticated user profile | Bearer JWT |

### Collaborative Documents

All document endpoints require `Authorization: Bearer <access_token>`.

| Method | Endpoint | Description | Permitted Roles |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/documents/` | List accessible documents ($O(1)$ query optimized) | Owner, Editor, Viewer |
| `POST` | `/api/documents/` | Create new document (injects `request.user`) | Authenticated |
| `GET` | `/api/documents/<uuid:id>/` | Retrieve document detail (Redis Cache-Aside enabled) | Owner, Editor, Viewer |
| `PUT`/`PATCH` | `/api/documents/<uuid:id>/` | Update document title or content (evicts cache) | Owner, Editor |
| `DELETE` | `/api/documents/<uuid:id>/` | Delete document (evicts cache) | Owner strictly |
| `POST` | `/api/documents/<uuid:id>/members/` | Add or update collaborator membership | Owner strictly |

---

## Engineering Sprint Changelog

* **`AUTH-201`**: Custom User Model with UUID Primary Key, PostgreSQL Integration, and Zero Schema Drift.
* **`AUTH-202`**: User Registration Endpoint with Serializer Validation & Transaction Boundaries.
* **`AUTH-203`**: Stateless JWT Authentication & Protected Profile Endpoint.
* **`DOC-301`**: Domain Modeling, Relational Integrity & Query Performance (Document entity, role-based `DocumentMember`, compound unique constraints, and B-tree indexing).
* **`DOC-302`**: Documents CRUD API, Atomic Ownership Ingestion, Multi-Tenant Scope Isolation & $N+1$ Query Elimination (`select_related`, `prefetch_related`).
* **`DOC-303`**: Granular Object-Level Permissions (`IsDocumentCollaborator`), Member Delegation Endpoint (`/members/`), and Owner-Only Destruction Protections.
* **`TEST-401`**: Enterprise Automated Testing Harness & CI Quality Gates (`pytest-django`, `factory_boy` dynamic model factories, RBAC matrix regression testing, and query-count assertions).
* **`CACHE-501`**: High-Throughput In-Memory Caching Layer (`django-redis`, Cache-Aside pattern, zero-query subsequent reads, and proactive cache invalidation policies).