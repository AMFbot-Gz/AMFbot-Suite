# Rapport d'Audit — Jarvis AntiGravity
**Date** : 2026-02-28
**Analyste** : Claude Code (Staff SE)
**Version analysée** : v3.0 (Phase 3 — Agent intelligent)

---

## Résumé Exécutif

Jarvis AntiGravity est un assistant IA local bien conçu, avec une architecture modulaire solide, un EventBus pub/sub, un cycle ReAct et un système de mémoire hybride (épisodique + sémantique). Le code est lisible et majoritairement bien structuré. **Trois points critiques à adresser en priorité** : (1) absence de `.gitignore` à la racine, exposant le fichier `.env` (credentials email, config LLM) à un commit accidentel ; (2) couverture de tests quasi-nulle hors SafetyGuard — aucun test sur ActionPlanner ni MemoryManager ; (3) appel déprécié `asyncio.get_event_loop()` dans EventBus, qui causera des erreurs sur Python 3.12+.

---

## 1. Architecture & Conception

- **Évaluation** : ✅ Excellent (avec réserves ⚠️)

### Analyse
La structure modulaire est claire et bien découpée :
```
src/core/       → Pipeline (EventBus, StateManager, Orchestrator, SafetyGuard)
src/llm/        → Raisonnement (LLMClient, ActionPlanner, Dispatcher, ContextManager)
src/memory/     → Mémoire (MemoryManager, EpisodicMemory, SemanticMemory)
src/skills/     → 19 compétences autonomes + Registry + BaseSkill
src/voice/      → Pipeline audio (STT, TTS, VAD, WakeWord)
src/gui/        → Overlay PyQt6 thread-safe
src/api/        → Dashboard FastAPI
```

**Points forts :**
- Découplage fort via EventBus : les modules ne se connaissent pas directement
- Pattern Facade sur MemoryManager (masque l'implémentation ChromaDB/JSONL)
- Plugin architecture avec hot-reload dans SkillRegistry
- SafetyGuard comme couche transversale de sécurité bien isolée
- Pattern ReAct (THINK → ACT → OBSERVE) correctement implémenté

**Points faibles :**
- `asyncio.get_event_loop()` utilisé dans EventBus (déprécié depuis Python 3.10, supprimé en 3.12) au lieu de `asyncio.get_running_loop()`
- Couplage implicite : `jarvis_main.py` crée et câble tous les composants manuellement — à terme, un IoC container simplifierait la configuration
- `CoreOrchestrator` gère trop de responsabilités (state, memory, LLM routing, TTS) → candidat à une décomposition future

### Exemples de code
```python
# event_bus.py:63 — DÉPRÉCIÉ en Python 3.10+, ERREUR en 3.12+
loop = asyncio.get_event_loop()
tasks.append(asyncio.create_task(
    loop.run_in_executor(None, handler, event_type, data)
))
# CORRECTION : utiliser asyncio.get_running_loop()
```

### Recommandations
1. Remplacer `asyncio.get_event_loop()` par `asyncio.get_running_loop()` dans `event_bus.py`
2. Extraire la logique de routing LLM de l'orchestrateur vers un `LLMRouter` dédié
3. Documenter les contrats d'interface entre modules dans `DEV_GUIDE.md`

---

## 2. Qualité du Code & Maintenabilité

- **Évaluation** : ⚠️ À Améliorer

### Analyse

**Points forts :**
- Nommage cohérent (snake_case, noms descriptifs)
- Dataclasses utilisées pour les structures de données (`ReActStep`, `SafetyReport`, etc.)
- Complexité cyclomatique raisonnable — la majorité des méthodes < 20 lignes
- Code DRY sur les skills (BaseSkill avec validate_params commun)

**Points faibles :**
- **Argument mutable par défaut** (bug potentiel classique) dans `memory_manager.py:74` :
  ```python
  # PROBLÈME : la liste est partagée entre tous les appels !
  def add_interaction(self, ..., actions: List[str] = None, metadata: dict = None):
  ```
- **Typo** dans `llm_client.py:138` — `IMPORATNT` au lieu de `IMPORTANT`
- **Type hint incomplet** : `raw: dict = None` au lieu de `Optional[dict] = None` dans `LLMResponse.__init__`
- **`_transcribe_sync`** dans `stt_engine.py` n'a pas de `try/except` — une exception non gérée remonte jusqu'à l'appelant async sans contexte utile
- La méthode `plan_and_execute` dans `action_planner.py` est correctement décomposée en méthodes privées (`_llm_think`, `_execute_action`), mais l'extraction de `_is_task_complete` améliorerait encore la lisibilité

### Exemples de code
```python
# memory_manager.py:74 — argument mutable par défaut
def add_interaction(self, text: str, role: str = "user",
                    actions: List[str] = None,  # ← PROBLÈME
                    metadata: dict = None):

# CORRECTION :
def add_interaction(self, text: str, role: str = "user",
                    actions: Optional[List[str]] = None,
                    metadata: Optional[dict] = None):

# llm_client.py:138 — typo
payload["messages"][0]["content"] += (
    f"\nIMPORATNT: tu DOIS utiliser l'un des outils suivants : ..."
    # ^^^^^^^^^^^^^ IMPORTANT
)
```

### Recommandations
1. Corriger le typo `IMPORATNT` → `IMPORTANT` dans `llm_client.py`
2. Utiliser `Optional[List[str]] = None` systématiquement pour les arguments mutables
3. Ajouter `try/except` dans `_transcribe_sync` avec logging explicite
4. Extraire `_is_task_complete(step)` dans ActionPlanner

---

## 3. Sécurité

- **Évaluation** : ❌ Critique

### Analyse

**Problème critique — Absence de `.gitignore` à la racine du projet :**

Il n'existe **aucun fichier `.gitignore` au niveau du projet**. Seul un `.gitignore` auto-généré dans `.pytest_cache/` est présent. Le fichier `.env` contenant des credentials est donc exposé à un `git add .` accidentel :
```ini
# .env — FICHIER SENSIBLE SANS PROTECTION GIT
EMAIL_PASSWORD=xxxx-xxxx-xxxx-xxxx
EMAIL_USER=votre@gmail.com
IMAP_SERVER=imap.gmail.com
```

**Points forts du SafetyGuard :**
- Règles de sécurité en couches (forbidden_paths, blacklist, whitelist, risk_levels)
- Validation des paramètres dans BaseSkill
- Confirmation obligatoire pour les actions `high`
- Blocage total des actions `critical`

**Autres points de vigilance :**
- `subprocess.Popen(["open", url])` dans `browser_control_skill.py:92` (fallback) ne valide pas l'URL — risque de `open://malicious` sur macOS
- `run_code` skill : malgré des vérifications, l'exécution de code arbitraire reste risquée
- Credentials email en clair dans `.env` (acceptable localement, mais `.gitignore` est critique)

### Exemples de code
```python
# browser_control_skill.py:92 — Exécution sans validation d'URL
except ImportError:
    import subprocess
    subprocess.Popen(["open", url])  # ← 'url' peut être n'importe quoi

# CORRECTION :
from urllib.parse import urlparse
parsed = urlparse(url)
if parsed.scheme in ("http", "https"):
    subprocess.Popen(["open", url])
else:
    return SkillResult.error(f"Schéma URL non autorisé : {parsed.scheme}")
```

### Recommandations
1. **[CRITIQUE]** Créer `/Users/wiaamhadara/jarvis_antigravity/.gitignore` incluant `.env`, `logs/`, `models/`, `memory/`, `venv/`
2. Valider le schéma URL avant `subprocess.Popen(["open", url])`
3. Envisager `python-dotenv` avec un `.env.example` versionné

---

## 4. Gestion des Dépendances

- **Évaluation** : ⚠️ À Améliorer

### Analyse

**Aucun `requirements.txt` à la racine du projet.** Le projet utilise un `venv` Python 3.12 mais sans fichier de dépendances formalisé, rendant toute reconstruction de l'environnement impossible sans le venv complet.

**Dépendances détectées à l'usage :**
```
aiohttp            → llm_client.py (HTTP async vers Ollama)
faster-whisper     → stt_engine.py
piper-tts          → tts_engine.py
chromadb           → semantic_memory.py
sentence-transformers → semantic_memory.py
playwright         → browser_control_skill.py
pyautogui          → scroll_page_skill (sans requirements!)
PyQt6              → gui/
fastapi + uvicorn  → api/dashboard.py
watchdog           → skills/registry.py
```

**Import guards** utilisés correctement (lazy imports avec `try/except ImportError`), mais sans `requirements.txt`, les versions ne sont pas épinglées.

### Recommandations
1. **[HAUTE]** Créer `requirements.txt` avec `pip freeze > requirements.txt` dans le venv
2. Séparer `requirements.txt` (prod) et `requirements-dev.txt` (tests, outils)
3. Ajouter `pyautogui` aux dépendances explicites (utilisé dans `scroll_page` sans guard)

---

## 5. Performance & Scalabilité

- **Évaluation** : ✅ Excellent

### Analyse

**Points forts :**
- `asyncio` utilisé correctement tout au long du pipeline
- Appels bloquants (STT, TTS, embedding) correctement déportés dans `loop.run_in_executor(None, ...)`
- Cache LRU avec TTL pour les réponses LLM (`utils/cache.py`)
- Streaming TTS phrase-par-phrase pour réduire la latence perçue (~300ms vs 5-10s)
- VAD silero pré-filtrage pour éviter de transcrire les silences
- ChromaDB avec index HNSW pour recherche vectorielle O(log n)

**Points d'attention :**
- L'historique de conversation dans `LLMClient` est une liste non bornée (`self._history`) — en session longue, peut grossir indéfiniment
- `CoreOrchestrator` maintient `interaction_history` (max 50) correctement borné
- `SkillRegistry` utilise `threading.Lock` (sync) dans un contexte async — à migrer vers `asyncio.Lock` pour la cohérence

### Exemples de code
```python
# llm_client.py:69 — Historique non borné
self._history: List[Dict[str, str]] = []

# Actuellement, seuls les 10 derniers sont utilisés (ligne 118) :
messages.extend(self._history[-10:])
# Mais _history grossit sans limite — ajouter un trim périodique
```

### Recommandations
1. Borner `_history` à 20 entrées max ou effectuer un trim périodique
2. Migrer `threading.Lock` du SkillRegistry vers `asyncio.Lock`
3. Profiler la première transcription (chargement modèle Whisper peut prendre 5-10s à froid)

---

## 6. Tests & Robustesse

- **Évaluation** : ❌ Critique

### Analyse

**Couverture actuelle :**
- ✅ `tests/unit/test_safety_guard.py` : 30+ tests, bonne couverture de SafetyGuard
- ❌ Aucun test pour `ActionPlanner` (composant le plus critique du pipeline)
- ❌ Aucun test pour `MemoryManager` / `SemanticMemory` / `EpisodicMemory`
- ❌ Aucun test pour `LLMClient`
- ❌ `tests/integration/` et `tests/benchmarks/` sont vides

**Gestion des erreurs manquante :**
- `stt_engine.py._transcribe_sync` : aucun `try/except` → une exception raw remonte
- `stt_engine.py.transcribe_stream` : le `NamedTemporaryFile` peut rester si exception
- `llm_client.py.generate_stream` : `except Exception as e` catch-all sans logging adequat des types spécifiques

**Points positifs :**
- SafetyGuard est 100% pur Python (pas de dépendances externes) → facilement testable
- ActionPlanner utilise l'injection de dépendances (llm_client, registry passés au constructeur) → mockable
- MemoryManager séparé des détails d'implémentation → testable avec mocks

### Recommandations
1. **[CRITIQUE]** Créer `tests/integration/test_action_planner.py` avec mocks LLM
2. **[CRITIQUE]** Créer `tests/integration/test_memory_manager.py` avec ChromaDB temporaire
3. Ajouter `try/except` dans `_transcribe_sync` avec gestion de `FileNotFoundError` et `RuntimeError`
4. Configurer `pytest-cov` pour mesurer la couverture de code

---

## 7. Documentation

- **Évaluation** : ✅ Excellent

### Analyse

**Points forts :**
- `README.md` et `DEV_GUIDE.md` bien rédigés et complets
- `QUICKSTART.md` pour les tests rapides
- Module-level docstrings présents sur tous les fichiers Python
- Docstrings de classe présentes sur les composants principaux
- Commentaires inline clairs et pertinents (ex: `# Cache hit ?`, `# Règle 1 : chemins interdits`)
- Format de réponse ReAct documenté en tête du fichier `action_planner.py`

**Points d'amélioration :**
- Certaines méthodes n'ont pas de docstring avec Args/Returns (format Google/NumPy)
- `MemoryManager.add_interaction` : manque de documentation sur le format `actions`
- `EventBus` : les types d'événements connus sont commentés mais pas dans une enum ou constante formelle

### Exemples de code
```python
# memory_manager.py:67 — docstring sans Args/Returns formels
def add_interaction(self, text: str, role: str = "user", ...):
    """
    Stocke une interaction dans la mémoire épisodique ET sémantique.
    La mémoire sémantique ne stocke que les textes contenant des faits...
    """
    # Manque : Args: text (str): ..., Returns: None
```

### Recommandations
1. Adopter le format Google pour les docstrings (Args, Returns, Raises, Example)
2. Créer une enum `EventType` dans `event_bus.py` pour typer les événements
3. Ajouter un `CHANGELOG.md` pour suivre les évolutions

---

## 8. Conformité & Bonnes Pratiques

- **Évaluation** : ⚠️ À Améliorer

### Analyse

**Type hints :**
- Présents sur la majorité des méthodes publiques
- Manquants ou incorrects sur certains endroits :
  ```python
  # llm_client.py:23 — pas Optional
  raw: dict = None
  # event_bus.py:27 — Callable sans paramètres de type
  self._subscribers: Dict[str, List[Callable]]
  ```

**SOLID :**
- **S** (Single Responsibility) : Orchestrator fait trop (à décomposer)
- **O** (Open/Closed) : SkillRegistry + BaseSkill respectent bien ce principe
- **L** (Liskov) : BaseSkill bien défini, sous-classes cohérentes
- **I** (Interface Segregation) : OK
- **D** (Dependency Inversion) : ActionPlanner reçoit llm_client et registry par injection ✅

**PEP8 / Ruff :**
- Formatage globalement propre
- Typo `IMPORATNT` dans llm_client.py
- Quelques lignes longues (>88 chars) probables

### Recommandations
1. Ajouter `ruff.toml` ou section `[tool.ruff]` dans `pyproject.toml` avec configuration stricte
2. Ajouter `mypy` en CI avec `strict = true` progressivement
3. Créer `pyproject.toml` comme point central de configuration (ruff, mypy, pytest)
4. Extraire les responsabilités de `CoreOrchestrator` vers des classes dédiées

---

## Plan d'Action Priorisé

### [CRITIQUE] — À faire immédiatement

1. **Créer `.gitignore`** à la racine du projet — protéger `.env`, `logs/`, `models/`, `memory/`, `venv/` d'un commit accidentel
2. **Créer `tests/integration/test_action_planner.py`** avec mocks LLM — couvrir le composant le plus critique sans tests
3. **Créer `tests/integration/test_memory_manager.py`** avec ChromaDB en base temporaire

### [HAUTE] — À faire cette semaine

4. **Créer `requirements.txt`** via `pip freeze` dans le venv (environnement non reproductible)
5. **Corriger `asyncio.get_event_loop()`** → `asyncio.get_running_loop()` dans `event_bus.py:63`
6. **Ajouter `try/except`** dans `stt_engine._transcribe_sync` et `generate_stream` de `llm_client`
7. **Valider le schéma URL** avant `subprocess.Popen(["open", url])` dans `browser_control_skill.py`

### [MOYENNE] — Sprint suivant

8. **Corriger typo** `IMPORATNT` → `IMPORTANT` dans `llm_client.py:138`
9. **Corriger arguments mutables** `actions: List[str] = None` → `Optional[List[str]] = None`
10. **Ajouter docstrings Google-format** sur `MemoryManager` et `ActionPlanner`
11. **Borner `_history`** dans LLMClient (actuellement non borné)
12. **Ajouter `_is_task_complete()`** dans ActionPlanner pour clarifier la logique de fin de boucle

### [FAIBLE] — Améliorations continues

13. Créer `pyproject.toml` avec config ruff + mypy + pytest centralisée
14. Migrer `threading.Lock` du SkillRegistry vers `asyncio.Lock`
15. Créer enum `EventType` dans `event_bus.py` pour typer les événements
16. Décomposer `CoreOrchestrator` en sous-responsabilités
17. Ajouter `pytest-cov` et fixer un seuil de couverture minimum à 60%

---

*Rapport généré par analyse statique + lecture de code complète. Aucun outil d'analyse dynamique (profiler, fuzzer) n'a été utilisé dans cette phase.*
