#!/bin/bash
#
# AMFbot Suite - Universal Installation Script
# https://github.com/amfbot/amfbot-suite
#
# This script installs all dependencies for AMFbot:
# - Docker & Docker Compose
# - Node.js 22+
# - Python 3.11+
# - Ollama
# - macOS accessibility permissions (if applicable)
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/amfbot/amfbot-suite/main/scripts/setup_amf.sh | bash
#   OR
#   bash scripts/setup_amf.sh [--dry-run] [--skip-docker] [--skip-models]
#
# License: Apache-2.0

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
DRY_RUN=false
SKIP_DOCKER=false
SKIP_MODELS=false
SKIP_NODE=false
SKIP_PYTHON=false
SKIP_OLLAMA=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        --skip-models)
            SKIP_MODELS=true
            shift
            ;;
        --skip-node)
            SKIP_NODE=true
            shift
            ;;
        --skip-python)
            SKIP_PYTHON=true
            shift
            ;;
        --skip-ollama)
            SKIP_OLLAMA=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Banner
echo -e "${PURPLE}"
cat << 'EOF'
   █████╗ ███╗   ███╗███████╗██████╗  ██████╗ ████████╗
  ██╔══██╗████╗ ████║██╔════╝██╔══██╗██╔═══██╗╚══██╔══╝
  ███████║██╔████╔██║█████╗  ██████╔╝██║   ██║   ██║   
  ██╔══██║██║╚██╔╝██║██╔══╝  ██╔══██╗██║   ██║   ██║   
  ██║  ██║██║ ╚═╝ ██║██║     ██████╔╝╚██████╔╝   ██║   
  ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝     ╚═════╝  ╚═════╝    ╚═╝   
                                                        
              Universal Installation Script
EOF
echo -e "${NC}"

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        if [[ $(uname -m) == "arm64" ]]; then
            ARCH="arm64"
        else
            ARCH="x86_64"
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        ARCH=$(uname -m)
        
        # Detect distribution
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            DISTRO=$ID
        fi
    else
        echo -e "${RED}Unsupported operating system: $OSTYPE${NC}"
        exit 1
    fi
    
    echo -e "${CYAN}Detected: $OS ($ARCH)${NC}"
    if [ -n "$DISTRO" ]; then
        echo -e "${CYAN}Distribution: $DISTRO${NC}"
    fi
}

# Check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Execute or print command
run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would execute: $*${NC}"
    else
        echo -e "${BLUE}Executing: $*${NC}"
        eval "$@"
    fi
}

# Install Homebrew (macOS)
install_homebrew() {
    if [ "$OS" = "macos" ] && ! command_exists brew; then
        echo -e "${GREEN}Installing Homebrew...${NC}"
        run_cmd '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        
        # Add to PATH for Apple Silicon
        if [ "$ARCH" = "arm64" ]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    fi
}

# Install Docker
install_docker() {
    if [ "$SKIP_DOCKER" = true ]; then
        echo -e "${YELLOW}Skipping Docker installation${NC}"
        return
    fi
    
    if command_exists docker; then
        echo -e "${GREEN}✓ Docker already installed${NC}"
        docker --version
        return
    fi
    
    echo -e "${GREEN}Installing Docker...${NC}"
    
    if [ "$OS" = "macos" ]; then
        run_cmd 'brew install --cask docker'
        echo -e "${YELLOW}Please start Docker Desktop from Applications${NC}"
    elif [ "$OS" = "linux" ]; then
        if [ "$DISTRO" = "ubuntu" ] || [ "$DISTRO" = "debian" ]; then
            run_cmd 'sudo apt-get update'
            run_cmd 'sudo apt-get install -y ca-certificates curl gnupg'
            run_cmd 'sudo install -m 0755 -d /etc/apt/keyrings'
            run_cmd 'curl -fsSL https://download.docker.com/linux/$DISTRO/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg'
            run_cmd 'sudo chmod a+r /etc/apt/keyrings/docker.gpg'
            run_cmd 'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$DISTRO $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null'
            run_cmd 'sudo apt-get update'
            run_cmd 'sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin'
            run_cmd 'sudo usermod -aG docker $USER'
            echo -e "${YELLOW}Please log out and back in for Docker group to take effect${NC}"
        fi
    fi
}

# Install Node.js
install_nodejs() {
    if [ "$SKIP_NODE" = true ]; then
        echo -e "${YELLOW}Skipping Node.js installation${NC}"
        return
    fi
    
    if command_exists node; then
        NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
        if [ "$NODE_VERSION" -ge 22 ]; then
            echo -e "${GREEN}✓ Node.js $NODE_VERSION already installed${NC}"
            return
        fi
    fi
    
    echo -e "${GREEN}Installing Node.js 22+...${NC}"
    
    # Install via nvm
    if ! command_exists nvm; then
        run_cmd 'curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash'
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    fi
    
    run_cmd 'nvm install 22'
    run_cmd 'nvm use 22'
    run_cmd 'nvm alias default 22'
}

# Install Python
install_python() {
    if [ "$SKIP_PYTHON" = true ]; then
        echo -e "${YELLOW}Skipping Python installation${NC}"
        return
    fi
    
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        if [ "$PYTHON_VERSION" = "3.11" ] || [ "$PYTHON_VERSION" = "3.12" ]; then
            echo -e "${GREEN}✓ Python $PYTHON_VERSION already installed${NC}"
            return
        fi
    fi
    
    echo -e "${GREEN}Installing Python 3.11+...${NC}"
    
    if [ "$OS" = "macos" ]; then
        run_cmd 'brew install python@3.11'
    elif [ "$OS" = "linux" ]; then
        if [ "$DISTRO" = "ubuntu" ] || [ "$DISTRO" = "debian" ]; then
            run_cmd 'sudo apt-get update'
            run_cmd 'sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip'
        fi
    fi
}

# Install Ollama
install_ollama() {
    if [ "$SKIP_OLLAMA" = true ]; then
        echo -e "${YELLOW}Skipping Ollama installation${NC}"
        return
    fi
    
    if command_exists ollama; then
        echo -e "${GREEN}✓ Ollama already installed${NC}"
        ollama --version
        return
    fi
    
    echo -e "${GREEN}Installing Ollama...${NC}"
    
    if [ "$OS" = "macos" ]; then
        run_cmd 'brew install ollama'
    elif [ "$OS" = "linux" ]; then
        run_cmd 'curl -fsSL https://ollama.com/install.sh | sh'
    fi
    
    # Pull default model
    echo -e "${CYAN}Pulling default LLM model (llama3.2)...${NC}"
    if [ "$DRY_RUN" = false ]; then
        # Start Ollama in background if not running
        if ! pgrep -x "ollama" > /dev/null; then
            ollama serve &
            sleep 5
        fi
        ollama pull llama3.2
    fi
}

# Setup macOS accessibility permissions
setup_macos_accessibility() {
    if [ "$OS" != "macos" ]; then
        return
    fi
    
    echo -e "${GREEN}Configuring macOS accessibility permissions...${NC}"
    echo -e "${YELLOW}"
    echo "To enable full system control, please:"
    echo "1. Open System Settings → Privacy & Security → Accessibility"
    echo "2. Enable the terminal application you're using"
    echo "3. If using Docker, also enable Docker Desktop"
    echo -e "${NC}"
    
    # Open System Settings (macOS 13+)
    if [ "$DRY_RUN" = false ]; then
        open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility" 2>/dev/null || \
        open "x-apple.systempreferences:com.apple.preference.security" 2>/dev/null || true
    fi
}

# Install AMFbot dependencies
install_amfbot() {
    echo -e "${GREEN}Installing AMFbot dependencies...${NC}"
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
    
    if [ -f "$PROJECT_DIR/package.json" ]; then
        echo -e "${CYAN}Installing Node.js dependencies...${NC}"
        run_cmd "cd '$PROJECT_DIR' && npm install"
    fi
    
    if [ -f "$PROJECT_DIR/modules/media-gen/pyproject.toml" ]; then
        echo -e "${CYAN}Installing Python dependencies...${NC}"
        run_cmd "cd '$PROJECT_DIR/modules/media-gen' && pip install -e '.[dev]'"
    fi
}

# Download AI models (optional, in background)
download_models() {
    if [ "$SKIP_MODELS" = true ]; then
        echo -e "${YELLOW}Skipping model downloads${NC}"
        return
    fi
    
    echo -e "${GREEN}Model downloads will be performed on first use.${NC}"
    echo -e "${CYAN}To download now, run: npm run download-models${NC}"
}

# Create configuration directory
setup_config() {
    echo -e "${GREEN}Setting up AMFbot configuration...${NC}"
    
    AMFBOT_DIR="$HOME/.amfbot"
    run_cmd "mkdir -p '$AMFBOT_DIR'"
    
    # Create default config if it doesn't exist
    if [ ! -f "$AMFBOT_DIR/config.json" ]; then
        cat > "$AMFBOT_DIR/config.json" << 'EOCONFIG'
{
  "model": "llama3.2",
  "ollamaHost": "http://localhost:11434",
  "mediaGen": {
    "videoBackend": "auto",
    "imageBackend": "auto"
  },
  "mcp": {
    "enabled": true
  }
}
EOCONFIG
        echo -e "${GREEN}Created default configuration at $AMFBOT_DIR/config.json${NC}"
    fi
}

# Main installation flow
main() {
    echo -e "${CYAN}Starting AMFbot installation...${NC}"
    echo ""
    
    detect_os
    echo ""
    
    if [ "$OS" = "macos" ]; then
        install_homebrew
        echo ""
    fi
    
    install_docker
    echo ""
    
    install_nodejs
    echo ""
    
    install_python
    echo ""
    
    install_ollama
    echo ""
    
    setup_config
    echo ""
    
    if [ "$OS" = "macos" ]; then
        setup_macos_accessibility
        echo ""
    fi
    
    install_amfbot
    echo ""
    
    download_models
    echo ""
    
    # Success message
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║                 🎉 AMFbot Installation Complete!             ║"
    echo "║                                                              ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    echo "║                                                              ║"
    echo "║  Next steps:                                                 ║"
    echo "║                                                              ║"
    echo "║  1. Start Ollama:     ollama serve                           ║"
    echo "║  2. Run wizard:       amfbot wizard                          ║"
    echo "║  3. Start AMFbot:     amfbot start                           ║"
    echo "║                                                              ║"
    echo "║  For Docker setup:    docker compose up -d                   ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Run main
main
