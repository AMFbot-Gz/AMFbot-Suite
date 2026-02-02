# 🌐 Ubiquité Souveraine : Guide des Connecteurs

L'AMF-OS Sovereign Elite est conçu pour être accessible partout, tout en gardant vos données sur votre matériel.

## 📪 Connecteurs Actuels
- **CLI** : Interface native ultra-performante.
- **Telegram** : Pont sécurisé (Admin-only) via `src/adapters/telegram.ts`.

## 🚀 Expansion (Inspiration OpenClaw)
Pour atteindre une ubiquité totale comme OpenClaw (WhatsApp, Slack, Discord), nous recommandons l'utilisation de passerelles souveraines ou d'outils d'automatisation auto-hébergés :

### 1. n8n (Solution Recommandée)
Déployez **n8n** en local ou sur votre VPS maître pour créer des ponts entre AMF-OS et :
- **WhatsApp** (via Twilio ou API locale).
- **Discord / Slack**.
- **Signal / iMessage**.

### 2. Custom Bridges
Vous pouvez créer un nouvel adapter dans `src/adapters/` en suivant le pattern `TelegramBridge`.
L'interface `AMFAgent` fournit une méthode `.chat(sessionId, prompt)` qui retourne un `AsyncGenerator`, facilitant l'intégration dans n'importe quel système de messagerie.

## 🛡️ Sécurité
Chaque nouveau connecteur doit implémenter un **Whitelist Check** (comme fait pour Telegram) pour garantir que seul le propriétaire souverain peut commander le Kernel.
