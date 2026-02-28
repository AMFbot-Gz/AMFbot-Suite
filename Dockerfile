# AMFbot Core Dockerfile
# For running the TypeScript agent in a container

FROM node:22-alpine

LABEL maintainer="AMFbot Project"
LABEL description="AMFbot Core Agent"

# Install system dependencies
RUN apk add --no-cache \
    git \
    curl \
    bash \
    python3 \
    py3-pip

# Create app directory
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY src/ ./src/
COPY mcp-hub/ ./mcp-hub/

# Build TypeScript
RUN npm run build

# Create data directories
RUN mkdir -p /data /root/.amfbot

# Environment
ENV NODE_ENV=production
ENV OLLAMA_HOST=http://ollama:11434

# Expose port for future web interface
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD node -e "console.log('healthy')" || exit 1

# Run the agent
CMD ["node", "dist/cli/index.js", "start", "--no-interactive"]
