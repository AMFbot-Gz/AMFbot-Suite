#!/bin/bash

# AMF-OS Sovereign Elite (Blueprint 2026.1)
# Universal Installer & Matrix Optimizer
# Version: 2.3.0

set -e

# Colors for terminal output
CYAN='\033[1;36m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}🛸 AMF-OS SOVEREIGN ELITE: Universal Installer Initializing...${NC}"

# --- Dependency Check ---
check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${YELLOW}⚠️  $1 is missing.${NC}"
        return 1
    fi
    return 0
}

# --- Install Bun if missing ---
if ! check_dependency "bun"; then
    echo -e "${CYAN}📦 Installing Bun runtime...${NC}"
    curl -fsSL https://bun.sh/install | bash
    source ~/.bashrc || source ~/.zshrc || true
    export PATH="$HOME/.bun/bin:$PATH"
fi

# --- Hardware Analysis ---
echo -e "${CYAN}🧠 Analyzing Hardware Kinetics...${NC}"

# Detect VRAM (NVIDIA)
if command -v nvidia-smi &> /dev/null; then
    VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n 1)
else
    VRAM=0
fi

# Detect RAM (Universal)
if [[ "$OSTYPE" == "darwin"* ]]; then
    RAM=$(sysctl -n hw.memsize | awk '{print int($1/1024/1024)}')
else
    RAM=$(free -m | awk '/^Mem:/{print $2}')
fi

echo -e "   - VRAM: ${GREEN}${VRAM}MB${NC}"
echo -e "   - RAM:  ${GREEN}${RAM}MB${NC}"

# --- Optimization Strategy ---
if [ "$VRAM" -gt 8000 ]; then
    echo -e "${GREEN}💎 High-End GPU Detected: Using q8_0 Quantization (Max Fidelity).${NC}"
    VERIFY_MODEL="llama4:8b-instruct-q8_0"
elif [ "$RAM" -gt 16000 ]; then
    echo -e "${YELLOW}🔋 Unified Memory Optimization: Using q6_K (Balanced).${NC}"
    VERIFY_MODEL="llama4:8b-instruct-q6_K"
else
    echo -e "${YELLOW}🔋 Efficiency Mode: Using q4_K_M (Fastest).${NC}"
    VERIFY_MODEL="llama4:8b-instruct-q4_K_M"
fi

# --- Ollama Readiness ---
if ! check_dependency "ollama"; then
    echo -e "${RED}❌ Error: Ollama is not installed. Please install it from https://ollama.com${NC}"
    exit 1
fi

# Ensure Ollama is running
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo -e "${YELLOW}⏳ Ollama is not running. Attempting to start...${NC}"
    # This varies by OS, but we can't easily start the desktop app. Just warn.
    echo -e "${RED}❌ Please start the Ollama application or service first.${NC}"
    exit 1
fi

# --- Model Sync ---
MODELS=("qwen3:0.5b-instruct-q4_K_M" "$VERIFY_MODEL" "qwen3:coder")

for model in "${MODELS[@]}"; do
    echo -e "${CYAN}🧠 Synchronizing model: ${NC}${WHITE}$model${NC}"
    ollama pull "$model"
done

# --- Environment Setup ---
if [ ! -f .env ]; then
    echo -e "${CYAN}📝 Creating .env from .env.example...${NC}"
    cp .env.example .env
fi

# --- Infrastructure ---
if check_dependency "docker-compose" || check_dependency "docker"; then
    echo -e "${CYAN}🐋 Syncing Docker Services (Memory & Cache)...${NC}"
    docker-compose up -d redis lancedb 2>/dev/null || docker compose up -d redis lancedb
else
    echo -e "${YELLOW}⚠️  Docker not found. Skipping Redis/LanceDB containers. System will use local fallback.${NC}"
fi

echo -e "${CYAN}📦 Installing project dependencies...${NC}"
bun install

echo -e "\n${GREEN}✅ AMF-OS SOVEREIGN ELITE SUCCESSFULLY DEPLOYED.${NC}"
echo -e "   Run ${CYAN}'bun start'${NC} to enter the Matrix.\n"
