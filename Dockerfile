FROM python:3.11-slim

WORKDIR /app

# Install system deps for sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (layer caching)
COPY pyproject.toml .
COPY automation/__init__.py automation/__init__.py
RUN pip install --no-cache-dir -e .

# Copy the rest of the project
COPY . .

# Default entrypoint: run the swarm CLI
ENTRYPOINT ["python", "-m", "automation.main"]
CMD ["info"]
