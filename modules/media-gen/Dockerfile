FROM nvidia/cuda:12.2.2-runtime-ubuntu22.04

LABEL maintainer="AMFbot Project"
LABEL description="AMFbot Media Generation - LTX-Video & Flux.1"

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV AMFBOT_MODELS_DIR=/models
ENV AMFBOT_OUTPUT_DIR=/outputs

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    git \
    wget \
    curl \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[cuda]"

# Copy application code
COPY . .

# Create directories for models and outputs
RUN mkdir -p /models/ltx-video /models/flux /outputs

# Expose API port
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8765/health || exit 1

# Run the API server
CMD ["python", "-m", "api.server"]
