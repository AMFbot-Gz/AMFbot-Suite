#!/bin/bash
# 🛸 AMFbot v2.6 "Elite Era" - Universal One-Click Installer
# Unified Brand: Sovereign, Secure, Seamless.

set -e

# Colors for Brand Unification
MAGENTA='\033[1;35m'
CYAN='\033[1;36m'
GREEN='\033[1;32m'
GRAY='\033[1;30m'
NC='\033[0m'

echo -e "${MAGENTA}"
echo "   🛸 AMFbot SOVEREIGN ELITE SETUP"
echo "   ───────────────────────────────"
echo "   Blueprint 2026.1 | v2.6.0"
echo -e "${NC}"

# 1. Environment Check
echo -e "${CYAN}🌀 Initializing Sovereign Environment...${NC}"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    OS="Windows"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
else
    OS="Linux"
fi
echo -e "${GRAY}Detected OS: $OS${NC}"

# 2. Dependency Audit
echo -e "${CYAN}📦 Auditing Dependencies...${NC}"
if ! command -v bun &> /dev/null; then
    echo -e "${CYAN}Installing Bun Runtime...${NC}"
    curl -fsSL https://bun.sh/install | bash
    source $HOME/.bashrc || true
fi

# 3. Kernel Bootstrapping
echo -e "${CYAN}🌀 Synchronizing Sovereign Kernel...${NC}"
bun install --quiet

# 4. Security Hardening (Elite Measure)
echo -e "${CYAN}🛡️  HardENING: Configuring Zero-Trust Boundaries...${NC}"
mkdir -p "$HOME/.amfbot/logs"
touch "$HOME/.amfbot/audit.log"
chmod 600 "$HOME/.amfbot/audit.log" || true

# 5. Model Matrix Synchronization
echo -e "${CYAN}🧠 Syncing Model Matrix (Ollama)...${NC}"
if command -v ollama &> /dev/null; then
    echo -e "${GRAY}Pulling Elite Models: llama4:8b, qwen3:coder, qwen3:0.5b...${NC}"
    ollama pull llama4:8b --quiet
    ollama pull qwen3:coder --quiet
    ollama pull qwen3:0.5b --quiet
else
    echo -e "${CYAN}⚠️ Ollama not found. Local inference will require manual setup.${NC}"
fi

echo -e "\n${GREEN}✅ AMFbot Sovereign Elite Installed Successfully.${NC}"
echo -e "${GRAY}Type 'amfbot start' to enter the Sovereign Era.${NC}\n"
