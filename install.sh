#!/bin/bash
# AMF-OS Sovereign Elite - Universal Bootstrapper
# This script is a wrapper for setup/install.sh

set -e

# Colors
MAGENTA='\033[1;35m'
CYAN='\033[1;36m'
NC='\033[0m'

echo -e "${MAGENTA}🛸 AMF-OS SOVEREIGN ELITE : Initiating Installation Protocol...${NC}"
echo -e "${CYAN}------------------------------------------------------------${NC}"

if [ ! -f "setup/install.sh" ]; then
    echo "❌ Error: setup/install.sh not found. Ensure you are in the project root."
    exit 1
fi

# Execute the actual installer
bash setup/install.sh "$@"

echo -e "${MAGENTA}✅ Installation wrapper complete.${NC}"
