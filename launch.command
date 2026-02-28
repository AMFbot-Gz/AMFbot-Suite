#!/bin/bash
# ╔══════════════════════════════════════════════╗
# ║    J.A.R.V.I.S. ANTIGRAVITY — Launcher      ║
# ╚══════════════════════════════════════════════╝

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      J.A.R.V.I.S. ANTIGRAVITY  v3.0                 ║${NC}"
echo -e "${CYAN}║      Initialisation du système...                    ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

# ── Aller dans le bon dossier ─────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || { echo -e "${RED}[ERREUR] Impossible d'accéder au dossier JARVIS.${NC}"; exit 1; }

echo -e "${YELLOW}[>>] Dossier : $SCRIPT_DIR${NC}"

# ── Activer l'environnement virtuel ───────────────────────────────────────────
if [ ! -f "venv/bin/activate" ]; then
    echo -e "${RED}[ERREUR] Environnement virtuel introuvable.${NC}"
    echo -e "${YELLOW}         Créez-le avec : python3 -m venv venv && pip install -r requirements.txt${NC}"
    echo ""
    read -p "Appuyez sur Entrée pour fermer..."
    exit 1
fi

source venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERREUR] Impossible d'activer le venv. Vérifiez votre installation Python.${NC}"
    echo ""
    read -p "Appuyez sur Entrée pour fermer..."
    exit 1
fi

echo -e "${GREEN}[OK] Environnement virtuel activé.${NC}"

# ── Vérifier Ollama (optionnel, avertissement seulement) ─────────────────────
if ! curl -s --max-time 2 http://localhost:11434 > /dev/null 2>&1; then
    echo -e "${YELLOW}[!]  Ollama ne répond pas sur localhost:11434.${NC}"
    echo -e "${YELLOW}     Lancez-le avec : ollama serve${NC}"
    echo ""
fi

# ── Lancer JARVIS ─────────────────────────────────────────────────────────────
echo -e "${GREEN}[>>] Démarrage de JARVIS...${NC}"
echo ""

python jarvis_main.py

# ── Fin (le terminal reste ouvert si lancé depuis Finder) ─────────────────────
echo ""
echo -e "${CYAN}[JARVIS] Session terminée.${NC}"
echo ""
read -p "Appuyez sur Entrée pour fermer ce terminal..."
