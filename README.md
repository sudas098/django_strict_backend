# Collaborative Document Backend API

A strict, production-grade Django REST Framework backend built with security, relational data integrity, query optimization, and static type safety as first-class architectural concerns.

---

## Features

- **Custom Identity & Security**: Custom User model using UUIDv4 primary keys (neutralizing ID enumeration attacks), email-based authentication, and atomic transaction boundaries during user provisioning.
- **Stateless JWT Flow**: Short-lived access tokens (15 minutes) with rolling refresh tokens (1 day) using standard HMAC/RSA signing.
- **Collaborative Domain Modeling**: Relational multi-tenant document architecture supporting document ownership and granular role-based memberships (`viewer`, `editor`).
- **Database-Level Integrity Guarantees**: Compound unique constraints preventing duplicate role allocations, explicit foreign key cascade lifecycles, and composite B-tree indexes for fast filtering and sorted lookups.
- **Multi-Tenant Scope Isolation**: Queryset filtering (`get_queryset`) strictly enforces that users can only access documents they own or are actively granted membership to. Requests attempting to access unauthorized UUIDs return `404 Not Found` rather than revealing resource existence.
- **Object-Level RBAC Enforcement**: Custom permission class (`IsDocumentCollaborator`) checks method-level capabilities per object, guaranteeing that deletions are owner-only and mutations require editor roles.
- **Zero $N+1$ Query Architecture**: Aggressive ORM query optimization leveraging `select_related` for single-valued relations and `prefetch_related` for multi-valued relations.
- **Decoupled DTO Serializers**: Clean segregation of read representations (`DocumentSerializer`) from input validation schemas (`DocumentCreateUpdateSerializer` and `DocumentMemberAddSerializer`), with atomic server-side ownership injection (`request.user`).
- **Serverless PostgreSQL**: Cloud database provisioning via Neon with connection-aware schema migrations.
- **Strict Quality Enforcement**: Static typing enforced across all modules via `mypy` (`django-stubs`, `djangorestframework-stubs`), fast code style and import hygiene via `ruff`, and strict environment validation via Pydantic Settings.

---

## Tech Stack

| Component | Technology |
| :--- | :--- |
| **Framework** | Django 5.2 + Django REST Framework |
| **Database** | PostgreSQL (hosted on Neon Serverless) |
| **Type Checking** | `mypy` (`django-stubs`, `djangorestframework-stubs`) |
| **Linting & Formatting** | `ruff` |
| **Configuration** | Pydantic Settings |
| **Authentication** | `djangorestframework-simplejwt` |

---

## Architecture & Relational Domain Model

### Entity-Relationship Diagram

```text
+-----------------------+
|      CustomUser       |
+-----------------------+
| id (UUID, PK)         |
| email (unique)        |
+-----------------------+
       | 1             | 1
       | (owner)       | (member)
       | N             | N
       v               v
+-----------------------+       +-----------------------------+
|       Document        |       |       DocumentMember        |
+-----------------------+       +-----------------------------+
| id (UUID, PK)         |       | id (UUID, PK)               |
| title (indexed)       |       | document_id (FK -> Document)|
| content (text)        |<------| user_id (FK -> CustomUser)  |
| owner_id (FK)         | 1     | role (enum: viewer | editor)|
| created_at (index)    |       | created_at                  |
+-----------------------+       +-----------------------------+
                                Constraint: UNIQUE(doc, user)
```

### Relational Design Decisions

1. **Cascade Lifecycles (`on_delete=models.CASCADE`)**:
   - Deleting an **owner** cascades to purge all their authored `Document` instances.
   - Deleting a **member user** cleans up their membership access record (`DocumentMember`) without deleting or corrupting the shared `Document`.
   - Deleting a **document** automatically cascades to all associated `DocumentMember` entries, preventing orphaned ACL rows.

2. **Compound Unique Constraints**:
   - Enforced at the database engine level via `models.UniqueConstraint(fields=["document", "user"], name="unique_document_member")` to prevent race conditions during permission assignment.

3. **Indexing Strategy**:
   - Dedicated indexes on `owner_id`, `created_at`, and `title` to accelerate `WHERE` filtering and ordered pagination scans (`ORDER BY created_at DESC`).

---

## Role-Based Access Control (RBAC) Matrix

Object-level access rules enforced via `IsDocumentCollaborator`:

| Operation | HTTP Method | Document Owner | Collaborator (`editor`) | Collaborator (`viewer`) | Non-Member / Anonymous |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **View Document** | `GET`, `HEAD`, `OPTIONS` | Allowed | Allowed | Allowed | `404 Not Found` / `401` |
| **Update Document** | `PUT`, `PATCH` | Allowed | Allowed | `403 Forbidden` | `404 Not Found` / `401` |
| **Delete Document** | `DELETE` | Allowed | `403 Forbidden` | `403 Forbidden` | `404 Not Found` / `401` |
| **Manage Members** | `POST /members/` | Allowed | `403 Forbidden` | `403 Forbidden` | `404 Not Found` / `401` |

---

## Performance & Query Optimization (Preventing $N+1$ Traps)

When serializing relational models with nested representations, naïve ORM queries trigger the **$N+1$ query problem**, firing 1 initial query for the list and $N$ individual queries for each related foreign key:

```text
# Naïve execution without eager loading (50 records):
SELECT * FROM documents;                          -- 1 query
SELECT * FROM users WHERE id = ...;               -- 50 additional queries
SELECT * FROM document_members WHERE ...;         -- 50 additional queries
Total: 101 queries (Scales linearly with row count)
```

### Production Query Strategy

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

| Method | Target Relationship | SQL Execution Mechanism | Optimization Effect |
| :--- | :--- | :--- | :--- |
| `select_related("owner")` | Single-valued (`ForeignKey`, `OneToOne`) | SQL `INNER JOIN` | Collapses owner lookup into the primary query |
| `prefetch_related("memberships__user")` | Multi-valued (`Reverse FK`, `ManyToMany`) | Batched SQL `WHERE id IN (...)` | Fetches all memberships and nested users in 2 constant queries |

**Result:** Total database roundtrips remain strictly **constant ($\mathcal{O}(1)$)** regardless of whether the endpoint returns 10 or 1,000 documents.

---

## Security Architecture: Ownership Injection & Scope Isolation

1. **Scope Isolation (`get_queryset`)**:
   Clients cannot access documents outside their authorization boundary. Queries are filtered using an `OR` condition (`Q(owner=request.user) | Q(memberships__user=request.user)`) combined with `.distinct()`, preventing leakage of private documents across tenants. Requests attempting to access unauthorized UUIDs return `404 Not Found` to prevent object existence enumeration.

2. **Server-Side Ownership Injection (`perform_create`)**:
   Clients are **never** trusted to provide the `owner` field in the request payload. The input serializer (`DocumentCreateUpdateSerializer`) strictly limits input fields to `["title", "content"]`, while `perform_create` automatically binds the verified JWT principal (`request.user`) server-side:
   ```python
   def perform_create(self, serializer: Any) -> None:
       serializer.save(owner=self.request.user)
   ```

3. **Decoupled Read/Write DTOs (`get_serializer_class`)**:
   - `DocumentCreateUpdateSerializer`: Sanitized write-only boundary that ignores read-only metadata.
   - `DocumentSerializer`: Detailed read-only DTO exposing full nested user profiles and membership ACL details.
   - `DocumentMemberAddSerializer`: Validates target collaborator email and role constraints before updating membership tables.

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
```

### 3. Migrations & Server

```powershell
# Run migrations against Neon PostgreSQL
python manage.py makemigrations
python manage.py migrate

# Start the dev server
python manage.py runserver
```

---

## Environment Variables Reference

| Variable | Description |
| :--- | :--- |
| `SECRET_KEY` | Django cryptographic secret key |
| `DEBUG` | Set to `False` in production |
| `DATABASE_URL` | PostgreSQL connection string (Neon Serverless) |

---

## API Endpoints

### Authentication & Identity

#### Register New User
`POST /api/auth/register`

- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "StrongPassword123!"
  }
  ```
- **Validation Rules:** Valid RFC-compliant email, unique; password 8–128 characters.
- **Success Response (`201 Created`):**
  ```json
  {
    "id": "f3241155-ebda-4355-bfab-ec06bc45cee1",
    "email": "user@example.com",
    "is_active": true,
    "date_joined": "2026-09-26T11:34:43.068015Z"
  }
  ```

#### Obtain JWT Pair (Login)
`POST /api/auth/token`

- **Success Response (`200 OK`):**
  ```json
  {
    "access": "<jwt_access_token>",
    "refresh": "<jwt_refresh_token>"
  }
  ```
  *(Access tokens expire in 15 minutes; refresh tokens expire in 1 day)*

#### Refresh Access Token
`POST /api/auth/token/refresh`

- **Success Response (`200 OK`):**
  ```json
  {
    "access": "<new_jwt_access_token>"
  }
  ```

#### Get Current User Profile
`GET /api/users/me`

- **Headers:** `Authorization: Bearer <access_token>`
- **Success Response (`200 OK`):**
  ```json
  {
    "id": "f3241155-ebda-4355-bfab-ec06bc45cee1",
    "email": "user@example.com",
    "is_active": true,
    "date_joined": "2026-09-26T11:34:43.068015Z"
  }
  ```

---

### Collaborative Documents API

All document endpoints require `Authorization: Bearer <access_token>`.

#### List Accessible Documents
`GET /api/documents/`

- Returns all documents where the caller is either the owner or an active member.
- **Optimized via `select_related` and `prefetch_related` (zero $N+1$ queries).**

#### Create Document
`POST /api/documents/`

- **Request Body:**
  ```json
  {
    "title": "Architecture Blueprint",
    "content": "Sprint planning notes..."
  }
  ```
- **Ownership:** `owner` is automatically injected from `request.user`.
- **Success Response (`201 Created`):**
  ```json
  {
    "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "title": "Architecture Blueprint",
    "content": "Sprint planning notes...",
    "owner": {
      "id": "f3241155-ebda-4355-bfab-ec06bc45cee1",
      "email": "user@example.com"
    },
    "memberships": [],
    "created_at": "2026-09-30T13:14:00Z",
    "updated_at": "2026-09-30T13:14:00Z"
  }
  ```

#### Retrieve Document Detail
`GET /api/documents/<uuid:id>/`

- Returns detailed representation with nested member roles. Returns `404 Not Found` if user does not own or belong to the document.

#### Update Document
`PUT /api/documents/<uuid:id>/` or `PATCH /api/documents/<uuid:id>/`

- Validated via `DocumentCreateUpdateSerializer`.
- Permitted for **Document Owner** and **Editors**. Returns `403 Forbidden` if attempted by a `viewer`.

#### Delete Document
`DELETE /api/documents/<uuid:id>/`

- Restricted strictly to **Document Owner**. Returns `403 Forbidden` for all collaborators (`viewer` or `editor`).
- **Success Response:** `204 No Content`

#### Add / Update Document Member
`POST /api/documents/<uuid:id>/members/`

- Restricted to **Document Owner**.
- **Request Body:**
  ```json
  {
    "email": "collaborator@example.com",
    "role": "viewer"
  }
  ```
- **Validation Rules:**
  - Owner cannot add themselves as a collaborator (`400 Bad Request`).
  - Target user must exist (`404 Not Found`).
- **Success Response (`201 Created` / `200 OK`):**
  ```json
  {
    "id": "7a35e89a-05a2-4a0b-8d48-9366df0285a8",
    "user": {
      "id": "c138f28d-71b5-4122-b586-b4845e2ad611",
      "email": "collaborator@example.com"
    },
    "role": "viewer",
    "created_at": "2026-10-08T02:04:05Z"
  }
  ```

---

## Development Checks

Run these static checks prior to committing or creating pull requests:

```powershell
# Run type checks across all domain apps
mypy core config documents

# Lint and check import formatting
ruff check .
```

---

## Ticket Reference & Engineering Sprints

- **`AUTH-201`**: Custom User Model with UUID Primary Key, PostgreSQL Integration, and Zero Schema Drift.
- **`AUTH-202`**: User Registration Endpoint with Serializer Validation & Transaction Boundaries.
- **`AUTH-203`**: Stateless JWT Authentication & Protected Profile Endpoint.
- **`DOC-301`**: Domain Modeling, Relational Integrity & Query Performance (Document entity, role-based `DocumentMember`, compound unique constraints, and B-tree indexing).
- **`DOC-302`**: Documents CRUD API, Atomic Ownership Ingestion, Multi-Tenant Scope Isolation & $N+1$ Query Elimination (`select_related`, `prefetch_related`).
- **`DOC-303`**: Granular Object-Level Permissions (`IsDocumentCollaborator`), Member Delegation Endpoint (`/members/`), and Owner-Only Destruction Protections.