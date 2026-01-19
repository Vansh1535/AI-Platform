# Backend Dockerfile - Optimized for Railway 4GB limit
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies (minimal set)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install dependencies to a temporary location with aggressive cleanup
RUN pip install --no-cache-dir --user -r requirements.txt && \
    find /root/.local -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true && \
    find /root/.local -type f -name '*.pyc' -delete && \
    find /root/.local -type f -name '*.pyo' -delete && \
    find /root/.local -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true

# Final stage - minimal runtime image
FROM python:3.11-slim

WORKDIR /app

# Install only critical runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /var/cache/apt/*

# Copy installed packages from builder (cleaned)
COPY --from=builder /root/.local /root/.local

# Update PATH to use pip packages
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy application code (exclude unnecessary files)
COPY app ./app
COPY alembic ./alembic
COPY artifacts ./artifacts

# Create necessary directories
RUN mkdir -p data/uploads data/vector_store

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
