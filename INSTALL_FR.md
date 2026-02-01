# 🚀 Guide d'Installation Rapide - AMFbot Suite

Ce guide résume les étapes pour installer et configurer AMFbot Suite sur votre machine.

## 📋 Prérequis
- **Node.js** : Version 22 ou supérieure.
- **Docker** : Recommandé pour la génération de médias (images/vidéos).
- **Ollama** : Pour faire tourner les modèles d'IA localement.

## 🛠️ Étapes d'Installation

### 1. Cloner le dépôt
```bash
git clone https://github.com/AMFbot-Gz/AMFbot-Suite.git
cd AMFbot-Suite
```

### 2. Lancer le script d'installation automatique
Ce script installera les dépendances nécessaires et configurera l'environnement de base.
```bash
bash scripts/setup_amf.sh
```

### 3. Configurer l'Assistant (Wizard)
Lancez l'assistant interactif pour choisir votre modèle d'IA et configurer vos clés API (si nécessaire).
```bash
amfbot wizard
```

### 4. Démarrer AMFbot
Une fois configuré, vous pouvez lancer l'interface de discussion :
```bash
amfbot start
```

## 🌐 Interface Web (Optionnel)
Pour utiliser l'interface graphique moderne :
```bash
npm run dev
```
Puis ouvrez [http://localhost:3000](http://localhost:3000) dans votre navigateur.

## 📪 Intégration Telegram
1. Obtenez un jeton (token) via [@BotFather](https://t.me/botfather).
2. Ajoutez-le dans votre fichier `~/.amfbot/config.json`.
3. Le bot se connectera automatiquement au prochain démarrage.

## 🛡️ Sécurité & Audit
Toutes les actions sensibles sont enregistrées dans : `~/.amfbot/audit.log`. 
Vérifiez régulièrement ce fichier pour surveiller l'activité de votre assistant.

---
**Besoin d'aide ?** Consultez le [README.md](./README.md) complet ou ouvrez une issue sur GitHub.
