# 🌐 Déploiement Multi-Nœuds (Sovereign Suite)

AMF-OS est conçu pour évoluer d'un seul serveur vers un réseau distribué de "nœuds de pensée".

## 🏗️ L'Architecture Distribuée

### 1. Le Control Plane (Nœud Maître)
Le master héberge l'orchestrateur central, la base de données LanceDB principale et le bridge Telegram. Il coordonne les tâches et agrège les résultats.

### 2. Les Nœuds d'Exécution (Workers)
Les workers sont des instances légères (`scripts/bootstrap-node.sh`) qui n'hébergent que le Kernel et Ollama. 
- Ils reçoivent des instructions chiffrées du Master.
- Ils exécutent les tâches système locales.
- Ils renvoient les patterns de succès pour enrichir la mémoire centrale.

## 📡 Communication Sécurisée
La communication entre les nœuds s'effectue via un tunnel chiffré (VPN type Wireguard recommandé) utilisant le protocole natif de Bun pour les WebSockets haut débit.

## 🚀 Scénario de Déploiement
1.  **Configurez le Master** : Installez AMF-OS v2.3 normalement.
2.  **Préparez un Nœud** : Sur un nouveau VPS, lancez `bash setup/install.sh --node-only`.
3.  **Appairage** : Échangez les clés de sécurité dans vos fichiers `.env`.
4.  **Action** : "Exécute `apt update` sur tous les nœuds de la zone EU-West."

---
⚠️ *Note : Cette fonctionnalité est actuellement en cours de développement intensif (Phase 3 de la Roadmap).*
