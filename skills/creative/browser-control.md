---
name: Browser Control
description: Advanced web navigation and data extraction capability.
domain: creative
tools: ["puppeteer", "playwright", "html-parser"]
version: 1.0.0
---

# 🌐 Browser Control Skill

Cette capacité permet à l'agent de sortir du système de fichiers local pour interagir avec le World Wide Web.

## 🚀 Capacités
1. **Navigation Autonome** : L'agent peut visiter n'importe quelle URL.
2. **Extraction de Données (Scraping)** : Analyse du DOM pour extraire des informations structurées.
3. **Automatisation de Formulaires** : Capacité à remplir des champs et soumettre des requêtes (ex: commande de VPS, recherche d'infos).
4. **Screenshots & Logs** : Preuve visuelle des actions effectuées.

## 🛡️ Sécurité Souveraine
- **Isolation** : Le navigateur tourne dans un processus enfant séparé.
- **VPN Ready** : Toutes les requêtes peuvent être routées via un proxy ou VPN local.
- **Anti-Tracking** : Blocage automatique des trackers publicitaires.

## 🛠️ Usage (ReAct Loop)
**Pensée** : Je dois trouver la documentation de l'API OpenClaw.
**Action** : browser.search("OpenClaw API documentation")
**Observation** : [Résultats de recherche...]
