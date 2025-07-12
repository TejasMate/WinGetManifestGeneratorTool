# Multi-stage build for production Docker image
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt requirements-dev.txt ./
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY config/ ./config/

# Install the package
RUN pip install -e .

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.local/bin:$PATH"

# Install system dependencies for runtime
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application files
COPY --from=builder /app/src ./src
COPY --from=builder /app/config ./config
COPY --from=builder /app/pyproject.toml ./

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/output && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from winget_automation.monitoring import check_all_health; import sys; sys.exit(0 if check_all_health()['overall_status'] == 'healthy' else 1)"

# Expose port for health checks (if needed)
EXPOSE 8080

# Default command
CMD ["wmat", "--help"]

# Development stage
FROM builder as development

# Install development dependencies
RUN pip install -r requirements-dev.txt

# Copy test files and scripts
COPY tests/ ./tests/
COPY scripts/ ./scripts/
COPY examples/ ./examples/
COPY Makefile ./

# Set development-specific environment
ENV ENVIRONMENT=development

# Default command for development
CMD ["bash"]
