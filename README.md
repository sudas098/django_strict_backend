Collaborative Document Backend API
A strict, production-grade Django REST Framework backend built with security, relational data integrity, and static type safety as first-class architectural concerns.
---
Features
Custom Identity & Security: Custom User model using UUIDv4 primary keys (neutralizing ID enumeration attacks), email-based authentication, and atomic transaction boundaries during user provisioning.
Stateless JWT Flow: Short-lived access tokens (15 minutes) with rolling refresh tokens (1 day) using standard asymmetric or symmetric signing.
Collaborative Domain Modeling: Relational multi-tenant document architecture supporting document ownership and granular role-based memberships (`viewer`, `editor`).
Database-Level Integrity Guarantees: Compound unique constraints preventing duplicate role allocations, explicit foreign key cascade lifecycles, and composite B-tree indexes for fast filtering and sorted lookups.
Serverless PostgreSQL: Cloud database provisioning via Neon with connection-aware schema migrations.
Strict Quality Enforcement: Static typing enforced across all modules via `mypy` (`django-stubs`), fast code style and import hygiene via `ruff`, and strict environment validation via Pydantic Settings.
---
Tech Stack
Framework: Django 5.2 + Django REST Framework
Database: PostgreSQL (hosted on Neon Serverless)
Type Checking: `mypy` (with `django-stubs`, `djangorestframework-stubs`)
Linting & Code Formatting: `ruff`
Configuration Management: Pydantic Settings
Authentication: `djangorestframework-simplejwt`
---
Architecture & Relational Domain Model
Entity-Relationship Architecture
```text
       +-----------------------+
       |      CustomUser       |
       |-----------------------|
       | id (UUID, PK)         |
       | email (unique)        |
       +-----------------------+
             | 1           | 1
             | (owner)     | (member)
             | N           | N
             v             v
   +-------------------+  +--------------------------------+
   |     Document      |  |         DocumentMember         |
   |-------------------|  |--------------------------------|
   | id (UUID, PK)     |  | id (UUID, PK)                  |
   | title (indexed)   |  | document_id (FK -> Document)   |
   | content (text)    |<-| user_id (FK -> CustomUser)     |
   | owner_id (FK)     |1 | role (enum: viewer | editor)   |
   | created_at (index)|  | created_at                     |
   +-------------------+  +--------------------------------+
                             Constraint: UNIQUE(doc, user)
```
Relational Design Decisions
Cascade Lifecycles (`on_delete=models.CASCADE`):
Deleting an owner cascades to purge all their authored `Document` instances.
Deleting a member user cleans up their membership access record (`DocumentMember`) without deleting or corrupting the shared `Document`.
Deleting a document automatically cascades to all associated `DocumentMember` entries, preventing orphaned ACL records.
Compound Unique Constraint:
Enforced at the database engine level via `models.UniqueConstraint(fields=["document", "user"], name="unique_document_member")` to prevent race conditions during permission assignment.
Indexing Strategy:
Dedicated indexes on `owner_id`, `created_at`, and `title` to accelerate `WHERE` filtering and ordered pagination scans (`ORDER BY created_at DESC`).
---
Setup & Local Development
1. Environment & Dependencies
```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows PowerShell
# source .venv/bin/activate # Linux/macOS

# Install locked dependencies
pip install -r requirements.txt
```
2. Environment Variables
Create a `.env` file in the project root:
```env
SECRET_KEY=your-super-secret-key-change-me
DEBUG=True
DATABASE_URL=postgresql://<user>:<password>@<neon-endpoint>.neon.tech/<dbname>?sslmode=require
```
3. Migrations & Server
```powershell
# Ensure Neon instance is awake, then run migrations
python manage.py makemigrations
python manage.py migrate

# Start the dev server
python manage.py runserver
```
---
Environment Variables Reference
Variable	Description
`SECRET_KEY`	Django's cryptographic secret key
`DEBUG`	Set to `False` in production
`DATABASE_URL`	PostgreSQL connection string (Neon Serverless)
---
API Endpoints
Authentication & Identity
Register New User
`POST /api/auth/register`
Creates a new user account. Passwords are hashed before storage and the operation is wrapped in an atomic database transaction.
Request Body:
```json
  {
    "email": "user@example.com",
    "password": "StrongPassword123!"
  }
  ```
Validation Rules:
Email must be valid and unique
Password must be 8–128 characters
Success Response (`201 Created`):
```json
  {
    "id": "f3241155-ebda-4355-bfab-ec06bc45cee1",
    "email": "user@example.com",
    "is_active": true,
    "date_joined": "2026-09-26T11:34:43.068015Z"
  }
  ```
Note: The password hash is never included in the response.
---
Obtain JWT Pair (Login)
`POST /api/auth/token`
Authenticates a user with email and password, returning a short-lived access token and a longer-lived refresh token.
Request Body:
```json
  {
    "email": "user@example.com",
    "password": "StrongPassword123!"
  }
  ```
Success Response (`200 OK`):
```json
  {
    "access": "ey...<jwt_access_token>",
    "refresh": "ey...<jwt_refresh_token>"
  }
  ```
Access tokens expire after 15 minutes
Refresh tokens expire after 1 day
---
Refresh Access Token
`POST /api/auth/token/refresh`
Exchanges a valid refresh token for a new access token without requiring re-authentication.
Request Body:
```json
  {
    "refresh": "ey...<jwt_refresh_token>"
  }
  ```
Success Response (`200 OK`):
```json
  {
    "access": "ey...<new_jwt_access_token>"
  }
  ```
---
Get Current User Profile
`GET /api/users/me`
Returns the profile of the currently authenticated user. Requires a valid access token.
Headers:
```http
  Authorization: Bearer <access_token>
  ```
Success Response (`200 OK`):
```json
  {
    "id": "f3241155-ebda-4355-bfab-ec06bc45cee1",
    "email": "user@example.com",
    "is_active": true,
    "date_joined": "2026-09-26T11:34:43.068015Z"
  }
  ```
Error Response (`401 Unauthorized`): If the token is missing, invalid, or expired.
---
Code Quality & Development Checks
Before committing or pushing changes, run:
```powershell
# Type checking across all active domains
mypy core config documents

# Linting and import formatting
ruff check .
```
---
Ticket Reference & Engineering Sprints
`AUTH-201`: Custom User Model with UUID Primary Key, PostgreSQL Integration, and Zero Schema Drift.
`AUTH-202`: User Registration Endpoint with Serializer Validation & Transaction Boundaries.
`AUTH-203`: Stateless JWT Authentication & Protected Profile Endpoint.
`DOC-301`: Domain Modeling, Relational Integrity & Query Performance (Document entity, role-based `DocumentMember`, compound unique constraints, and B-tree indexing).