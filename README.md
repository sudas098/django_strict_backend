# Health Check API

A strict, production-grade Django backend built with security and 
type-safety as first-class concerns.

## Features

- Custom User model with UUID4 primary keys (prevents ID enumeration)
- Email-based authentication instead of username
- PostgreSQL database (hosted on Neon, serverless)
- Strict type checking with mypy
- Linting enforced with ruff
- Structured JSON logging

## Tech Stack

- **Framework:** Django 5.2 + Django REST Framework
- **Database:** PostgreSQL (via Neon)
- **Type Checking:** mypy
- **Linting:** ruff
- **Environment Management:** Pydantic Settings

## Setup

1. Clone the repository
2. Create a virtual environment:
    python -m venv .venv
    .venv\Scripts\activate # Windows
3. Install dependencies:
    pip install -r requirements.txt
4. Copy `.env.example` to `.env` and fill in your own values:
    cp .env.example .env
5. Run migrations:
    python manage.py migrate
6. Start the development server:
    python manage.py runserver


## Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django's cryptographic secret key |
| `DEBUG` | Set to `False` in production |
| `DATABASE_URL` | PostgreSQL connection string (Neon) |

## Development Checks

Before committing, run:
   mypy core config
   ruff check .


## Ticket Reference

- **AUTH-201** — Custom User Model with UUID Primary Key, 
  PostgreSQL Integration, and Zero Schema Drift