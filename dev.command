#!/bin/bash
# ╔══════════════════════════════════════════════╗
# ║    J.A.R.V.I.S. ANTIGRAVITY — Dev Mode      ║
# ╚══════════════════════════════════════════════╝

CYAN='\033[0;36m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║    J.A.R.V.I.S. ANTIGRAVITY — DEV MODE              ║${NC}"
echo -e "${CYAN}║    Logs DEBUG · GUI désactivée · REPL actif          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || { echo -e "${RED}[ERREUR] Dossier JARVIS introuvable.${NC}"; exit 1; }

if [ ! -f "venv/bin/activate" ]; then
    echo -e "${RED}[ERREUR] venv introuvable. Lancez d'abord : python3 -m venv venv && pip install -r requirements.txt${NC}"
    read -p "Appuyez sur Entrée pour fermer..."; exit 1
fi

source venv/bin/activate
echo -e "${GREEN}[OK] venv activé.${NC}"

export PYTHONPATH="$SCRIPT_DIR/src"
echo -e "${GREEN}[OK] PYTHONPATH=$PYTHONPATH${NC}"
echo -e "${YELLOW}[>>] Démarrage en mode développeur (--dev)...${NC}"
echo ""

python jarvis_main.py --dev

echo ""
echo -e "${CYAN}[DEV] Session terminée.${NC}"
read -p "Appuyez sur Entrée pour fermer..."
