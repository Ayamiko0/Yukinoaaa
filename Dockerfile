# Stage 1: Build & Dependencies
FROM python:3.13-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml ./
COPY src ./src
COPY README.md ./

# Install the application and runtime dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Stage 2: Production Runtime
FROM python:3.13-slim as runtime

WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_ENV="production"

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
COPY scripts /app/scripts

# Attempt command registration at Docker build step (non-fatal if secrets unset)
RUN python /app/scripts/register_discord_commands.py --auto || true

# Create a non-root user for security (Least Privilege)
RUN chmod +x /app/scripts/docker-entrypoint.sh && \
    groupadd -r yukinoaaa && useradd -r -g yukinoaaa -d /app -s /sbin/nologin yukinoaaa && \
    chown -R yukinoaaa:yukinoaaa /app
USER yukinoaaa

# Default entrypoint and command
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["python", "-m", "yukinoaaa"]
