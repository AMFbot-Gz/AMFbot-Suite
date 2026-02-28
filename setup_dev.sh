#!/bin/bash
# setup_dev.sh — Configure l'alias jarvis-dev dans ~/.zshrc

ZSHRC="$HOME/.zshrc"
ALIAS_LINE='alias jarvis-dev="cd ~/jarvis_antigravity && source venv/bin/activate && export PYTHONPATH=src"'

if grep -q "alias jarvis-dev=" "$ZSHRC" 2>/dev/null; then
    echo "[INFO] L'alias jarvis-dev existe déjà dans $ZSHRC — rien à faire."
else
    echo "$ALIAS_LINE" >> "$ZSHRC"
    echo "[OK] Alias jarvis-dev ajouté à $ZSHRC"
fi

echo ""
echo "Pour activer l'alias immédiatement, lancez :"
echo "  source ~/.zshrc"
echo ""
echo "Ensuite, depuis n'importe quel terminal :"
echo "  jarvis-dev          # active venv + PYTHONPATH"
echo "  python jarvis_main.py --dev   # lance le mode dev"
