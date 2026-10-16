FROM python:3.13-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (compiler, libpq for PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies first for caching layers
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy repository source code
COPY . /app/

# Expose Django port
EXPOSE 8000

# Default command runs Uvicorn ASGI server (or Django runserver)
CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000"]