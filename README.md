<div align="center">

<img src="web/assets/logo-dragon.png" alt="AMFbot Sovereign Dragon" width="200">

# 🛸 AMFbot SOVEREIGN ELITE
### Blueprint 2026.1 - "The Elite Era" (v2.6.0)
**Infrastructure d'IA Souveraine, Multi-Plateforme & Ultra-Accessible**

[![Security](https://img.shields.io/badge/Security-Zero--Trust-red.svg)](#-sécurité-élite)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue.svg)](#-compatibilité-windows-native)
[![Privacy](https://img.shields.io/badge/Privacy-Zero%20Data%20Leakage-magenta.svg)](#-notre-manifeste)

**AMFbot v2.6 marque le passage du projet GitHub à une infrastructure de calibre industriel.**
*Libérez-vous du cloud. Prenez le contrôle total avec le Dragon's Kernel.*

[Démarrage Elite](#-le-setup-elite-en-un-clic) • [Guide Connecteurs](docs/connectors.md) • [Architecture Elite](docs/ARCHITECTURE.md) • [Sécurité](docs/security-deep-dive.md)

</div>

---

## 🐲 L'Identité Elite
AMFbot n'est plus seulement un bot, c'est une **marque de confiance**. Unifiée à travers toutes ses interfaces (CLI, Web, Telegram), elle repose sur trois piliers indéboulonnables :
1.  **Souveraineté Totale** : Vos clés, vos données, votre matériel.
2.  **Accessibilité Industrielle** : Prêt pour Windows, Linux et macOS dès la sortie de boîte.
3.  **Puissance Agentique** : Une boucle ReAct optimisée avec le support de modèles de pointe comme **Kimi k2.5**.

---

## 🚀 Le Setup Elite en Un Clic
L'installateur intelligent s'occupe de tout : hardening de sécurité, détection GPU et configuration MCP.

```bash
# Invoquez le Dragon instantanément
curl -fsSL https://amf-elite.sh/install.sh | bash
```

---

## 🛡️ Sécurité Élite : Zero Data Leakage
La version 2.6 introduit des mesures de sécurité de grade militaire :
*   **Protection LFI Native** : Un validateur de chemin surveille chaque accès fichier pour prévenir les fuites de données locales.
*   **Audit Logger Normalisé** : Chaque action agentique est tracée dans un log JSON exploitable par des outils tiers (SIEM).
*   **Privilèges Restreints** : Le mode Superuser est désormais encadré par des frontières de sécurité strictes.

---

## 🪟 Compatibilité Windows Native
AMFbot Elite supporte désormais officiellement Windows.
*   **Chemins Normalisés** : Gestion transparente des séparateurs de dossiers et des profils utilisateurs.
*   **CLI Autopick** : Détection automatique de PowerShell ou Bash pour une expérience sans friction.

---

## 🔌 Ubiquité & Connectivité Elite
Ne soyez plus jamais déconnecté de votre intelligence souveraine.
*   **Telegram Sync** : Synchronisation en temps réel de vos sessions entre votre machine et votre mobile.
*   **MCP Auto-Discovery** : AMFbot scanne et connecte automatiquement vos serveurs Model Context Protocol locaux.
*   **Modèles Synthétiques** : Routage intelligent vers Kimi k2.5 pour les tâches d'architecture complexes.

---

## 🏗️ Architecture Blueprint 2026.1

```mermaid
graph TD
    User((Utilisateur)) --> CLI[Elite CLI]
    User --> Web[Web UI Glass]
    User --> TG[Telegram Elite]
    
    subgraph "Sovereign Kernel (v2.6)"
        SK[Dragon's Kernel]
        AV[Audit & Validator]
        MM[Tactical Memory]
    end
    
    CLI & Web & TG --> SK
    SK --> AV
    AV --> MM
    SK --> LLM[Local LLM: Kimi/Llama/Qwen]
    SK --> MCP[MCP Hub: Plugins Autonomes]
```

---

## 🎬 Scénarios d'Usage Elite
> **Ops** : "Vérifie la santé de mon cluster et bloque les IPs suspectes via la passerelle Telegram."
> **Dev** : "Génère un boilerplate NestJS avec auth JWT et valide-le dans une sandbox isolée."
> **Data** : "Scrape les actus sur l'IA souveraine et stocke une synthèse vectorielle dans ma Tactical Memory."

---

<footer>
<div align="center">
Built for the event-driven future. AMFbot-Suite is an open infrastructure for sovereign intelligence.
</div>
</footer>


---

# Jarvis AntiGravity

Assistant IA local, vocal et autonome — overlay PyQt6, pipeline ReAct, mémoire sémantique, 19 skills.

---

## Prérequis

- **macOS** (testé sur macOS 15+)
- **Python 3.11+** (`python3 --version`)
- **Ollama** installé et en cours d'exécution :
  ```bash
  ollama serve
  ```
- Modèle téléchargé (`llama3` ou `mistral`) :
  ```bash
  ollama pull llama3
  # ou
  ollama pull mistral
  ```

---

## Installation unique

```bash
# 1. Clonez le dépôt (ou déplacez le dossier jarvis_antigravity)
git clone <url-du-repo>
cd jarvis_antigravity

# 2. Créez l'environnement virtuel
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Lancez JARVIS
./launch.command
```

Ou, après la première installation, **double-cliquez sur `launch.command`** depuis le Finder.

---

## Configuration

Éditez `.env` pour ajuster vos préférences :

| Variable | Description | Défaut |
|---|---|---|
| `LLM_MODEL` | Modèle Ollama (`llama3`, `mistral`…) | `llama3` |
| `GUI_ENABLED` | Overlay PyQt6 (`true`/`false`) | `true` |
| `USE_REACT` | Boucle ReAct (`true`/`false`) | `true` |
| `STT_MODEL` | Modèle Whisper (`tiny`, `small`, `medium`) | `small` |
| `EMAIL_USER` / `EMAIL_PASSWORD` | Gmail App Password pour le skill email | — |
| `DEBUG` | Logs détaillés | `false` |

---

## Architecture

```
jarvis_main.py          ← Point d'entrée (Qt main thread + asyncio pipeline)
src/
  core/                 ← Orchestrateur, EventBus, StateManager
  llm/                  ← LLMClient (Ollama), ActionPlanner (ReAct), ContextManager
  memory/               ← MemoryManager (épisodique JSONL + sémantique ChromaDB)
  skills/               ← 19 skills (apps, browser, email, code, screenshot…)
  voice/                ← STT (faster-whisper), TTS (piper), VAD, wake word
  gui/                  ← OverlayWindow PyQt6, GUIManager thread-safe
  api/                  ← Dashboard FastAPI (http://127.0.0.1:7070)
```

---

## Dashboard

Interface web disponible pendant l'exécution : [http://127.0.0.1:7070](http://127.0.0.1:7070)
