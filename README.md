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
