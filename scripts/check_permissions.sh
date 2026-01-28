#!/bin/bash
#
# AMFbot - Vérification des permissions macOS
# Ce script vérifie que toutes les permissions nécessaires sont configurées
#

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         🔐 Vérification des Permissions macOS               ║"
echo "║                     pour AMFbot                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

ERRORS=0

# 1. Test Accessibilité
echo "1️⃣  Test d'Accessibilité..."
if osascript -e 'tell application "System Events" to return name of first process' &>/dev/null; then
    echo -e "   ${GREEN}✅ Accessibilité: OK${NC}"
else
    echo -e "   ${RED}❌ Accessibilité: NON CONFIGURÉE${NC}"
    echo "      → Ouvrez: Réglages Système > Confidentialité et sécurité > Accessibilité"
    echo "      → Ajoutez votre application terminal"
    ERRORS=$((ERRORS + 1))
fi

# 2. Test Enregistrement d'écran
echo ""
echo "2️⃣  Test d'Enregistrement d'écran..."
TEST_FILE="/tmp/amfbot_screen_test_$$.png"
if screencapture -x "$TEST_FILE" 2>/dev/null && [ -f "$TEST_FILE" ] && [ -s "$TEST_FILE" ]; then
    rm -f "$TEST_FILE"
    echo -e "   ${GREEN}✅ Enregistrement d'écran: OK${NC}"
else
    rm -f "$TEST_FILE" 2>/dev/null
    echo -e "   ${RED}❌ Enregistrement d'écran: NON CONFIGURÉ${NC}"
    echo "      → Ouvrez: Réglages Système > Confidentialité et sécurité > Enregistrement d'écran"
    echo "      → Ajoutez votre application terminal"
    ERRORS=$((ERRORS + 1))
fi

# 3. Test Accès complet au disque
echo ""
echo "3️⃣  Test d'Accès complet au disque..."
# Tester l'accès à un dossier protégé
if ls ~/Library/Mail &>/dev/null 2>&1; then
    echo -e "   ${GREEN}✅ Accès complet au disque: OK${NC}"
else
    echo -e "   ${YELLOW}⚠️  Accès complet au disque: Limité${NC}"
    echo "      → Optionnel mais recommandé pour un accès total"
    echo "      → Ouvrez: Réglages Système > Confidentialité et sécurité > Accès complet au disque"
fi

# 4. Vérification Docker (si installé)
echo ""
echo "4️⃣  Vérification Docker..."
if command -v docker &>/dev/null; then
    if docker info &>/dev/null; then
        echo -e "   ${GREEN}✅ Docker: OK et en cours d'exécution${NC}"
    else
        echo -e "   ${YELLOW}⚠️  Docker: Installé mais non démarré${NC}"
        echo "      → Lancez Docker Desktop"
    fi
else
    echo -e "   ${YELLOW}ℹ️  Docker: Non installé (optionnel)${NC}"
fi

# 5. Vérification Ollama (si installé)
echo ""
echo "5️⃣  Vérification Ollama..."
if command -v ollama &>/dev/null; then
    if curl -s http://localhost:11434/api/tags &>/dev/null; then
        echo -e "   ${GREEN}✅ Ollama: OK et en cours d'exécution${NC}"
    else
        echo -e "   ${YELLOW}⚠️  Ollama: Installé mais non démarré${NC}"
        echo "      → Exécutez: ollama serve"
    fi
else
    echo -e "   ${RED}❌ Ollama: Non installé${NC}"
    echo "      → Installez avec: brew install ollama"
    ERRORS=$((ERRORS + 1))
fi

# Résumé
echo ""
echo "═══════════════════════════════════════════════════════════════"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}🎉 Toutes les permissions sont correctement configurées !${NC}"
    echo ""
    echo "Vous pouvez maintenant lancer AMFbot :"
    echo "  amfbot start"
else
    echo -e "${RED}⚠️  $ERRORS problème(s) détecté(s)${NC}"
    echo ""
    echo "Corrigez les problèmes ci-dessus, puis relancez ce script."
    echo ""
    echo "Pour ouvrir les réglages de sécurité :"
    echo "  open 'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'"
fi
echo ""
