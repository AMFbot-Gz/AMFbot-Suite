# JARVIS AntiGravity — Guide Développeur

---

## Démarrage rapide

### Option A — script dédié
```bash
./dev.command
```
Lance JARVIS en mode dev : GUI désactivée, logs DEBUG complets, REPL Python interactif à la fin.

### Option B — alias shell
```bash
# Installation unique (à faire une seule fois)
bash setup_dev.sh
source ~/.zshrc

# Utilisation quotidienne
jarvis-dev                        # active venv + PYTHONPATH=src
python jarvis_main.py --dev       # lance le pipeline en mode dev
```

### Option C — commande directe
```bash
cd ~/jarvis_antigravity
source venv/bin/activate
export PYTHONPATH=src
python jarvis_main.py --dev
```

---

## Ce que fait `--dev`

| Comportement | Normal | --dev |
|---|---|---|
| GUI overlay | PyQt6 visible | `LoggingNullGUIManager` (no-op + logs) |
| Niveau de log | INFO | **DEBUG** (tout est visible) |
| Entrée | Prompt texte `[JARVIS] >` | **REPL Python interactif** |
| Signal SIGINT | Arrêt propre | Arrêt propre |

---

## REPL — Variables disponibles

Après le démarrage, un shell Python interactif s'ouvre avec accès à tous les composants :

```python
>>> # Tester la mémoire
>>> memory.add_interaction("J'aime le chocolat.", {"topic": "préférence"})
>>> memory.search_relevant_context("mon dessert préféré")

>>> # Tester l'ActionPlanner (ReAct)
>>> from skills.base_skill import ExecutionContext
>>> ctx = ExecutionContext(session_id="dev")
>>> import asyncio
>>> asyncio.run(action_planner.plan_and_execute("Résume mes 5 derniers emails", ctx))

>>> # Inspecter les skills enregistrés
>>> registry.list_skills()
>>> registry.get("take_screenshot")

>>> # Tester un skill directement
>>> from skills.base_skill import ExecutionContext
>>> ctx = ExecutionContext(session_id="dev")
>>> skill = registry.get("get_system_info")
>>> asyncio.run(skill.run({}, ctx))

>>> # Inspecter le cache LRU
>>> cache.stats()

>>> # Publier un événement sur l'EventBus
>>> asyncio.run(event_bus.publish("stt.result", {"text": "dis bonjour"}))
```

---

## Tests

```bash
# Tests unitaires
pytest tests/unit/ -v

# Tests avec couverture
pytest tests/ --cov=src --cov-report=term-missing

# Un seul fichier
pytest tests/unit/test_memory.py -v
```

---

## Typage statique

```bash
mypy src/ --strict
# ou plus permissif pour commencer :
mypy src/ --ignore-missing-imports
```

---

## Linting

```bash
# Ruff (rapide)
ruff check src/

# Auto-fix
ruff check src/ --fix

# Formatage
ruff format src/
```

---

## Tester un skill isolément

```bash
# Depuis le dossier racine (avec PYTHONPATH=src)
python -c "
from skills.clipboard_skill import ReadClipboardSkill
from skills.base_skill import ExecutionContext
import asyncio
skill = ReadClipboardSkill()
ctx = ExecutionContext(session_id='test')
result = asyncio.run(skill.run({}, ctx))
print(result)
"

# Screenshot
python -c "
from skills.screenshot_skill import TakeScreenshotSkill
from skills.base_skill import ExecutionContext
import asyncio
r = asyncio.run(TakeScreenshotSkill().run({}, ExecutionContext('test')))
print(r.message)
"
```

---

## Ajouter un skill

1. Créer `src/skills/mon_skill.py` en héritant de `BaseSkill`
2. L'enregistrer dans `jarvis_main.py` → section `registry.register(...)`
3. Le hot-reload watchdog le détectera automatiquement en dev

```python
# src/skills/mon_skill.py
from .base_skill import BaseSkill, SkillResult, ExecutionContext

class MonSkill(BaseSkill):
    name = "mon_skill"
    description = "Ce que fait mon skill"
    risk_level = "low"

    async def run(self, params: dict, ctx: ExecutionContext) -> SkillResult:
        return SkillResult(success=True, message="Fait !")
```

---

## Structure du projet

```
jarvis_antigravity/
├── jarvis_main.py       ← Point d'entrée (--dev pour mode dev)
├── launch.command       ← Lancement production (double-clic Finder)
├── dev.command          ← Lancement développement
├── setup_dev.sh         ← Configure l'alias jarvis-dev
├── .env                 ← Configuration (LLM_MODEL, GUI_ENABLED…)
├── src/
│   ├── core/            ← Orchestrateur, EventBus, StateManager, SafetyGuard
│   ├── llm/             ← LLMClient, ActionPlanner (ReAct), ContextManager
│   ├── memory/          ← MemoryManager (JSONL + ChromaDB)
│   ├── skills/          ← 19 skills (hot-reload actif)
│   ├── voice/           ← STT, TTS, VAD, WakeWord
│   ├── gui/             ← OverlayWindow, GUIManager
│   ├── api/             ← Dashboard FastAPI
│   └── utils/           ← Config, Cache LRU
├── tests/
│   └── unit/
└── logs/
    └── jarvis.log
```

---

## Logs en temps réel

```bash
# Dans un second terminal
tail -f ~/jarvis_antigravity/logs/jarvis.log

# Filtrer par composant
tail -f logs/jarvis.log | grep "ActionPlanner"
tail -f logs/jarvis.log | grep "memory"
```
