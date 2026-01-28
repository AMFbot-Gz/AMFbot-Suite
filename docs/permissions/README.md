# 🔐 Guide des Permissions macOS pour AMFbot

> **Attention**: Sans ces permissions, AMFbot sera "aveugle et paralysé". Ce guide est essentiel pour un fonctionnement complet.

## 📋 Permissions Requises

AMFbot nécessite **trois permissions** pour un contrôle total du système :

| Permission | Pourquoi ? | Impact si absente |
|------------|------------|-------------------|
| **Accessibilité** | Cliquer, taper, contrôler les applications | Aucune automatisation possible |
| **Enregistrement d'écran** | Voir ce qui se passe à l'écran | Mode "aveugle" - pas de capture d'écran |
| **Accès complet au disque** | Lire/écrire tous les fichiers | Accès limité aux fichiers utilisateur |

---

## 🎯 Étape 1 : Accessibilité

L'accessibilité permet à AMFbot de :
- ✅ Cliquer sur des boutons et liens
- ✅ Taper du texte dans les applications
- ✅ Naviguer entre les fenêtres
- ✅ Exécuter des raccourcis clavier

### Comment activer :

1. Ouvrez **Réglages Système** (ou Préférences Système sur les anciennes versions)
2. Allez dans **Confidentialité et sécurité** → **Accessibilité**
3. Cliquez sur le **🔒 cadenas** en bas pour déverrouiller
4. Cliquez sur **+** et ajoutez :
   - **Terminal** (ou iTerm, Warp, selon votre terminal)
   - **Docker Desktop** (si vous utilisez Docker)
   - **AMFbot.app** (si installé via l'application)

```
📍 Chemin : Réglages Système → Confidentialité et sécurité → Accessibilité
```

### Vérification :
```bash
# Tester si l'accessibilité fonctionne
osascript -e 'tell application "System Events" to keystroke "a"'
```

---

## 📸 Étape 2 : Enregistrement d'écran

L'enregistrement d'écran permet à AMFbot de :
- ✅ Prendre des captures d'écran
- ✅ Voir le contenu des fenêtres
- ✅ Détecter les éléments visuellement
- ✅ Enregistrer des vidéos de démonstration

### Comment activer :

1. Ouvrez **Réglages Système**
2. Allez dans **Confidentialité et sécurité** → **Enregistrement d'écran**
3. Déverrouillez avec le **🔒 cadenas**
4. Ajoutez les mêmes applications qu'à l'étape 1

```
📍 Chemin : Réglages Système → Confidentialité et sécurité → Enregistrement d'écran
```

### Note importante :
> ⚠️ Après avoir ajouté une application, vous devez **redémarrer cette application** pour que la permission prenne effet.

---

## 💾 Étape 3 : Accès complet au disque

L'accès complet au disque permet à AMFbot de :
- ✅ Lire tous les fichiers de votre Mac
- ✅ Accéder aux bases de données des applications
- ✅ Modifier des fichiers système (avec confirmation)
- ✅ Travailler avec des dossiers protégés (Documents, Bureau, etc.)

### Comment activer :

1. Ouvrez **Réglages Système**
2. Allez dans **Confidentialité et sécurité** → **Accès complet au disque**
3. Déverrouillez avec le **🔒 cadenas**
4. Ajoutez votre terminal et Docker

```
📍 Chemin : Réglages Système → Confidentialité et sécurité → Accès complet au disque
```

---

## 🚀 Script de Vérification Automatique

Exécutez ce script pour vérifier toutes les permissions :

```bash
#!/bin/bash
# Vérification des permissions AMFbot

echo "🔍 Vérification des permissions macOS pour AMFbot..."
echo ""

# Test Accessibilité
echo "1️⃣  Test d'Accessibilité..."
if osascript -e 'tell application "System Events" to return name of first process' &>/dev/null; then
    echo "   ✅ Accessibilité: OK"
else
    echo "   ❌ Accessibilité: NON CONFIGURÉE"
    echo "      → Ajoutez votre terminal dans Réglages > Confidentialité > Accessibilité"
fi

# Test Enregistrement d'écran
echo "2️⃣  Test d'Enregistrement d'écran..."
if screencapture -x /tmp/amfbot_test.png 2>/dev/null && [ -f /tmp/amfbot_test.png ]; then
    rm /tmp/amfbot_test.png
    echo "   ✅ Enregistrement d'écran: OK"
else
    echo "   ❌ Enregistrement d'écran: NON CONFIGURÉ"
    echo "      → Ajoutez votre terminal dans Réglages > Confidentialité > Enregistrement d'écran"
fi

# Test Accès disque
echo "3️⃣  Test d'Accès au disque..."
if ls ~/Library/Mail &>/dev/null; then
    echo "   ✅ Accès complet au disque: OK"
else
    echo "   ⚠️  Accès complet au disque: Limité (optionnel)"
fi

echo ""
echo "🎉 Vérification terminée!"
```

Sauvegardez ce script et exécutez-le :
```bash
bash scripts/check_permissions.sh
```

---

## 🔧 Dépannage

### "Opération non autorisée" lors de l'exécution de commandes

**Solution** : Ajoutez votre terminal dans Accessibilité et redémarrez-le.

### Les captures d'écran sont noires ou vides

**Solution** : Ajoutez votre terminal dans Enregistrement d'écran et redémarrez-le.

### "Permission denied" sur certains fichiers

**Solution** : Ajoutez votre terminal dans Accès complet au disque.

### Docker ne peut pas accéder aux volumes

**Solution** : 
1. Ajoutez Docker Desktop dans les trois catégories de permissions
2. Allez dans Docker Desktop → Préférences → Ressources → File Sharing
3. Ajoutez les dossiers que vous voulez partager

---

## 📱 Commande Rapide pour Ouvrir les Réglages

```bash
# Ouvrir directement les réglages de sécurité
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
```

---

## ✅ Checklist Finale

Avant de lancer AMFbot, vérifiez :

- [ ] Terminal ajouté dans **Accessibilité**
- [ ] Terminal ajouté dans **Enregistrement d'écran**
- [ ] Terminal ajouté dans **Accès complet au disque** (optionnel mais recommandé)
- [ ] Docker Desktop ajouté (si utilisé)
- [ ] Applications redémarrées après ajout des permissions

---

> 💡 **Astuce** : Si vous changez de terminal (ex: de Terminal vers iTerm), vous devrez refaire ces étapes pour le nouveau terminal.
