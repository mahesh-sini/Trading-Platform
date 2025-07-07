# Multi-stage build for ML Service
FROM python:3.10-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TA_LIB_VER=0.4.0

# Install system dependencies for ML libraries and TA-Lib
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    pkg-config \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install TA-Lib
# RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
#     tar -xvzf ta-lib-0.4.0-src.tar.gz && \
#     cd ta-lib-0.4.0/ && \
#     ./configure --prefix=/usr && \
#     make && \
#     make install && \
#     cd .. && \
#     rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Use curl -L to follow redirects, and name the file correctly
RUN curl -L -o ta-lib-0.4.0-src.tar.gz http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib && \
    ./configure --prefix=/usr && \
    make && make install && \
    cd .. && rm -rf ta-lib*


ENV LD_LIBRARY_PATH=/usr/lib
# Create and use non-root user
RUN useradd --create-home --shell /bin/bash app
USER app
WORKDIR /home/app

RUN pip install --no-build-isolation --no-cache-dir numpy==1.23.5
# Copy requirements and install Python dependencies
COPY --chown=app:app requirements.txt ./
RUN pip install --user --no-build-isolation --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.10-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/app/.local/bin:$PATH" \
    TF_CPP_MIN_LOG_LEVEL=2

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libopenblas0 \
    liblapack3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app
WORKDIR /home/app

# Copy Python packages from builder stage
COPY --from=builder --chown=app:app /home/app/.local /home/app/.local

# Copy application code
COPY --chown=app:app . .

# Create directories for models and logs
RUN mkdir -p models logs

# Expose port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "2"]