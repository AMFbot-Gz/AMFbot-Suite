#!/usr/bin/env python3
"""
J.A.R.V.I.S. ANTIGRAVITY v3.0 — Point d'entrée principal

Pipeline complet :
  Micro → VAD → STT ──────────────────────────────────┐
                                                        ↓
                              EventBus(stt.result) → Orchestrator
                                                        ↓
                                             ContextManager.resolve()
                                                        ↓
                                          MemoryManager.build_context_prompt()
                                                        ↓
                                          ActionPlanner.plan_and_execute()
                                               [ReAct: THINK → ACT → OBSERVE]
                                                  ↙              ↘
                                         token_queue        SkillRegistry.run()
                                              ↓                    ↓
                                    TTSEngine.speak_       MemoryManager.add()
                                    async_stream()

Composants démarrés :
  ✅ CoreOrchestrator  — pipeline asyncio
  ✅ MemoryManager     — épisodique (JSONL) + sémantique (ChromaDB)
  ✅ ActionPlanner     — boucle ReAct (Reason + Act)
  ✅ ContextManager    — résolution de coréférences
  ✅ GUIManager        — overlay PyQt6 (main thread)
  ✅ FastAPI Dashboard — http://127.0.0.1:7070
  ✅ Hot-reload        — watchdog sur src/skills/
  ✅ Cache LRU         — résultats LLM (TTL=5min)
"""

import argparse
import asyncio
import code
import logging
import os
import signal
import sys
import threading
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from utils.config import Config
from utils.cache  import LRUCache

from core.event_bus     import EventBus
from core.state_manager import StateManager, JarvisState
from core.orchestrator  import CoreOrchestrator
from core.safety_guard  import SafetyGuard

from llm.llm_client    import LLMClient
from llm.dispatcher    import FunctionDispatcher
from llm.action_planner import ActionPlanner
from llm.context_manager import ContextManager

from memory.memory_manager import MemoryManager

from skills.registry import SkillRegistry
from skills.examples.system_skill   import OpenAppSkill, GetSystemInfoSkill, GetTimeSkill
from skills.clipboard_skill         import ReadClipboardSkill, WriteClipboardSkill
from skills.browser_control_skill   import OpenUrlSkill, ScrollPageSkill
from skills.calendar_skill          import AddEventSkill, ListEventsSkill
from skills.notification_skill      import SendNotificationSkill
from skills.process_manager_skill   import ListProcessesSkill, KillProcessSkill
from skills.email_skill             import ReadEmailsSkill, SendEmailSkill
from skills.screenshot_skill        import TakeScreenshotSkill, OCRScreenSkill
from skills.code_skill              import OpenInEditorSkill, RunCodeSkill, ReadFileSkill, WriteFileSkill

from voice.stt_engine       import STTEngine
from voice.tts_engine       import TTSEngine
from voice.vad              import VADProcessor
from voice.wake_word_detector import WakeWordDetector

from gui.gui_manager import create_gui_manager, NullGUIManager
from api.dashboard   import app as dashboard_app, inject_dependencies


# ── LoggingNullGUIManager (mode dev) ─────────────────────────────────────────

class LoggingNullGUIManager:
    """
    GUIManager no-op pour le mode dev.
    Loggue chaque appel au niveau DEBUG — permet de vérifier le câblage
    sans avoir besoin de l'overlay Qt.
    """
    def start(self) -> bool:
        logger_dev.debug("[GUI] start() — no-op (dev mode)")
        return True
    def stop(self) -> None:
        logger_dev.debug("[GUI] stop()")
    def set_transcription(self, t: str) -> None:
        logger_dev.debug("[GUI] set_transcription(%r)", t)
    def set_llm_response(self, t: str) -> None:
        logger_dev.debug("[GUI] set_llm_response(%r)", t)
    def add_action(self, a: str) -> None:
        logger_dev.debug("[GUI] add_action(%r)", a)
    def set_status(self, s: str) -> None:
        logger_dev.debug("[GUI] set_status(%r)", s)
    def reset(self) -> None:
        logger_dev.debug("[GUI] reset()")

logger_dev = logging.getLogger("JARVIS.dev")


# ── Logging ───────────────────────────────────────────────────────────────────

def setup_logging(config: Config) -> None:
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if config.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(config.logs_dir / "jarvis.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

logger = logging.getLogger("JARVIS.main")


# ── Dashboard (FastAPI dans thread séparé) ────────────────────────────────────

def start_dashboard(host: str, port: int) -> None:
    """Lance le serveur FastAPI dans un thread daemon."""
    import uvicorn
    config = uvicorn.Config(
        dashboard_app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)

    def run():
        asyncio.run(server.serve())

    thread = threading.Thread(target=run, daemon=True, name="JARVIS-Dashboard")
    thread.start()
    logger.info("Dashboard: http://%s:%d", host, port)


# ── Bootstrap ─────────────────────────────────────────────────────────────────

async def bootstrap(config: Config, gui_manager=None):
    """
    Instancie, câble et retourne tous les composants.

    gui_manager : si fourni (déjà créé + démarré sur le main thread Qt),
                  on ne recrée pas de GUIManager en interne.
    """

    # ── Cache LRU ──────────────────────────────────────────────────────────
    cache = LRUCache(
        max_size    = int(os.getenv("CACHE_MAX_SIZE",    "200")),
        ttl_seconds = float(os.getenv("CACHE_TTL_SECONDS", "300")),
    )

    # ── Infrastructure ──────────────────────────────────────────────────────
    event_bus     = EventBus()
    state_manager = StateManager()
    safety_guard  = SafetyGuard()

    # ── GUI ─────────────────────────────────────────────────────────────────
    if gui_manager is None:
        gui_enabled = os.getenv("GUI_ENABLED", "true").lower() == "true"
        gui_manager = create_gui_manager(enabled=gui_enabled)
        if gui_enabled:
            gui_manager.start()

    # ── Memory ──────────────────────────────────────────────────────────────
    memory = MemoryManager(storage_dir=config.data_dir / "memory")
    memory.load_semantic()   # Charge ChromaDB + embedder (async-friendly dans thread pool)
    logger.info("MemoryManager prêt — %s", memory.stats())

    # ── Skills ──────────────────────────────────────────────────────────────
    registry = SkillRegistry()
    for skill in [
        OpenAppSkill(),        GetSystemInfoSkill(),  GetTimeSkill(),
        ReadClipboardSkill(),  WriteClipboardSkill(),
        OpenUrlSkill(),        ScrollPageSkill(),
        AddEventSkill(),       ListEventsSkill(),
        SendNotificationSkill(),
        ListProcessesSkill(),  KillProcessSkill(),
        ReadEmailsSkill(),     SendEmailSkill(),
        TakeScreenshotSkill(), OCRScreenSkill(),
        OpenInEditorSkill(),   RunCodeSkill(),
        ReadFileSkill(),       WriteFileSkill(),
    ]:
        registry.register(skill)

    # Hot-reload watchdog
    registry.start_hot_reload(ROOT / "src" / "skills")

    logger.info(registry.summary())

    # ── LLM + Dispatcher + ActionPlanner ────────────────────────────────────
    llm_client = LLMClient(
        model    = config.llm.model,
        host     = config.llm.host,
        cache    = cache,
    )
    dispatcher     = FunctionDispatcher(registry)
    action_planner = ActionPlanner(llm_client, registry)
    context_mgr    = ContextManager(llm_client)

    # ── Voice ───────────────────────────────────────────────────────────────
    stt_engine = STTEngine(
        model_name = config.stt.model_name,
        language   = config.stt.language,
        models_dir = config.models_dir,
    )
    tts_engine = TTSEngine(
        voice      = config.tts.voice,
        speed      = config.tts.speed,
        models_dir = config.models_dir / "tts",
    )
    vad       = VADProcessor()
    wake_word = WakeWordDetector(keywords=config.wake_words)

    # ── Orchestrateur ────────────────────────────────────────────────────────
    orchestrator = CoreOrchestrator(
        event_bus       = event_bus,
        state_manager   = state_manager,
        safety_guard    = safety_guard,
        gui_manager     = gui_manager,
        memory_manager  = memory,
        context_manager = context_mgr,
    )

    # ── Câblage EventBus ─────────────────────────────────────────────────────

    # LLM request → ActionPlanner (ReAct) ou génération directe
    async def on_llm_request(event_type: str, data: dict):
        prompt        = data.get("prompt", "")
        context_block = data.get("context_block", "")

        use_react = os.getenv("USE_REACT", "true").lower() == "true"

        if use_react:
            # ── Mode ReAct : ActionPlanner orchestre la boucle ──────────────
            from skills.base_skill import ExecutionContext
            ctx = ExecutionContext(session_id="main")

            react_result = await action_planner.plan_and_execute(
                objective=prompt,
                ctx=ctx,
                context_block=context_block,
            )

            full_text = react_result.answer
            # Envoyer la réponse au TTS token par token
            tts_task = asyncio.create_task(
                tts_engine.speak_async_stream(orchestrator.token_queue)
            )
            for token in (full_text.split() if full_text else []):
                await orchestrator.token_queue.put(token + " ")
            await orchestrator.token_queue.put(None)

            # Publier la réponse (pas de plan — ReAct a déjà exécuté les skills)
            await event_bus.publish("llm.response", {
                "plan":   None,
                "text":   full_text,
                "intent": prompt,
            })

            try:
                await asyncio.wait_for(tts_task, timeout=60)
            except asyncio.TimeoutError:
                pass

        else:
            # ── Mode classique : FunctionDispatcher ─────────────────────────
            tools = dispatcher.get_tool_definitions()
            tts_task = asyncio.create_task(
                tts_engine.speak_async_stream(orchestrator.token_queue)
            )

            full_text  = ""
            tool_calls = []

            if tools:
                full_prompt = f"{context_block}\n\n{prompt}" if context_block else prompt
                response    = await llm_client.generate(full_prompt, tools=tools, tool_choice="auto")
                full_text   = response.text
                tool_calls  = response.tool_calls
                for token in (full_text.split() if full_text else []):
                    await orchestrator.token_queue.put(token + " ")
            else:
                async for token in llm_client.generate_stream(prompt):
                    full_text += token
                    await orchestrator.token_queue.put(token)

            await orchestrator.token_queue.put(None)

            from llm.llm_client import LLMResponse
            resp   = LLMResponse(text=full_text, tool_calls=tool_calls)
            result = dispatcher.parse_response(resp, intent=prompt)

            await event_bus.publish("llm.response", {
                "plan":   result.plan if result.is_action else None,
                "text":   result.text,
                "intent": prompt,
            })

            try:
                await asyncio.wait_for(tts_task, timeout=60)
            except asyncio.TimeoutError:
                pass

    # Skill execute
    async def on_skill_execute(event_type: str, data: dict):
        from core.safety_guard import ExecutionPlan
        from skills.base_skill import ExecutionContext

        plan: ExecutionPlan = data.get("plan")
        intent = data.get("intent", "")
        ctx    = ExecutionContext(session_id="main", confirmed=data.get("confirmed", False))

        last_result = None
        for step in plan.steps:
            skill = registry.get(step.skill_name)
            if skill is None:
                await event_bus.publish("skill.error", {"error": f"Skill inconnu : {step.skill_name}"})
                return
            result = await skill.run(step.params, ctx)
            last_result = result
            if not result.success:
                await event_bus.publish("skill.error", {"error": result.message, "skill_name": step.skill_name})
                return

        msg = last_result.message if last_result else "Fait."
        await event_bus.publish("skill.done", {
            "message":    msg,
            "intent":     intent,
            "skill_name": plan.steps[-1].skill_name if plan.steps else "",
        })

    # TTS speak (non-streaming)
    async def on_tts_speak(event_type: str, data: dict):
        text = data.get("text", "")
        await tts_engine.speak(text)
        await state_manager.transition(JarvisState.IDLE)

    event_bus.subscribe("llm.request",   on_llm_request)
    event_bus.subscribe("skill.execute", on_skill_execute)
    event_bus.subscribe("tts.speak",     on_tts_speak)

    # ── Dashboard ────────────────────────────────────────────────────────────
    inject_dependencies(
        orchestrator   = orchestrator,
        registry       = registry,
        cache          = cache,
        config         = config,
        state_manager  = state_manager,
        action_planner = action_planner,
        main_loop      = asyncio.get_event_loop(),
    )

    return {
        "event_bus":      event_bus,
        "state_manager":  state_manager,
        "orchestrator":   orchestrator,
        "stt_engine":     stt_engine,
        "tts_engine":     tts_engine,
        "vad":            vad,
        "wake_word":      wake_word,
        "llm_client":     llm_client,
        "registry":       registry,
        "cache":          cache,
        "gui_manager":    gui_manager,
        "memory":         memory,
        "action_planner": action_planner,
    }


# ── REPL interactif (mode dev) ────────────────────────────────────────────────

async def _dev_repl(components: dict):
    """
    Lance un shell Python interactif avec accès à tous les composants JARVIS.
    S'exécute dans un executor pour ne pas bloquer la boucle asyncio.
    """
    banner = """
╔══════════════════════════════════════════════════════╗
║    J.A.R.V.I.S. DEV MODE — Python REPL              ║
║    Tapez exit() ou Ctrl+D pour quitter               ║
╠══════════════════════════════════════════════════════╣
║  Variables disponibles :                             ║
║    orchestrator   memory         registry            ║
║    llm_client     action_planner context_mgr         ║
║    event_bus      tts_engine     stt_engine          ║
║    gui_manager    cache          asyncio             ║
╚══════════════════════════════════════════════════════╝

Exemples :
  >>> memory.search_relevant_context("mon dessert préféré")
  >>> registry.list_skills()
  >>> asyncio.run(action_planner.plan_and_execute("dis bonjour", ctx))
"""
    local_vars = {**components, "asyncio": asyncio}
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        lambda: code.interact(banner=banner, local=local_vars, exitmsg="\n[DEV] REPL fermé. Au revoir.")
    )


# ── Boucle principale ─────────────────────────────────────────────────────────

async def audio_capture_loop(components: dict):
    """
    Boucle d'entrée texte (dev).
    En production : remplacer par microphone + VAD + STT.
    """
    event_bus     = components["event_bus"]
    state_manager = components["state_manager"]
    stt_engine    = components["stt_engine"]

    logger.info("Pipeline audio prêt — mode texte (dev)")
    logger.info("Tapez une commande (Ctrl+C ou 'bye' pour quitter)\n")

    await state_manager.transition(JarvisState.IDLE)
    loop = asyncio.get_running_loop()

    while True:
        try:
            text = await loop.run_in_executor(None, input, "\n[JARVIS] > ")
            text = text.strip()
            if not text:
                continue
            if text.lower() in ("quit", "exit", "bye", "au revoir"):
                await event_bus.publish("system.shutdown", {})
                break

            await state_manager.transition(JarvisState.LISTENING)
            await event_bus.publish("stt.result", {"text": text})

        except KeyboardInterrupt:
            break
        except EOFError:
            # stdin fermé (mode daemon) — on garde le serveur web actif
            await asyncio.sleep(3600)
        except Exception as e:
            logger.error("audio_loop: %s", e)


# ── Pipeline asyncio (background thread quand GUI actif) ─────────────────────

async def _async_pipeline(gui_manager=None):
    """Pipeline asyncio complet. gui_manager optionnel (fourni par _start_with_qt_main_thread)."""
    config = Config.from_env()
    setup_logging(config)

    dash_host = os.getenv("DASHBOARD_HOST", "127.0.0.1")
    dash_port = int(os.getenv("DASHBOARD_PORT", "7070"))

    banner = f"""
╔══════════════════════════════════════════════════════╗
║      J.A.R.V.I.S. ANTIGRAVITY  v3.0                 ║
╠══════════════════════════════════════════════════════╣
║  LLM        {config.llm.model:<40}║
║  Ollama     {config.llm.host:<40}║
║  STT        faster-whisper/{config.stt.model_name:<29}║
║  TTS        piper-tts/{config.tts.voice:<33}║
║  Dashboard  http://{dash_host}:{dash_port:<30}║
╚══════════════════════════════════════════════════════╝
"""
    print(banner)

    # Démarrer le dashboard FastAPI
    start_dashboard(dash_host, dash_port)

    # Bootstrap tous les composants (gui_manager peut être None → créé en interne)
    components   = await bootstrap(config, gui_manager=gui_manager)
    orchestrator = components["orchestrator"]

    await orchestrator.start()

    # Graceful shutdown
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Signal d'arrêt reçu")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except (NotImplementedError, RuntimeError):
            pass  # Windows ou thread non-principal

    tasks = [
        asyncio.create_task(audio_capture_loop(components)),
        asyncio.create_task(stop_event.wait()),
    ]

    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()

    await orchestrator.stop()
    components["gui_manager"].stop()
    components["registry"].stop_hot_reload()
    logger.info("JARVIS Antigravity arrêté proprement.")
    print("\nAu revoir.")


# ── Démarrage avec Qt sur le main thread (requis macOS) ──────────────────────

def _start_with_qt_main_thread():
    """
    Lance Qt sur le main thread (obligation macOS / AppKit).

    1. Crée QApplication sur le main thread
    2. Crée + démarre GUIManager sur le main thread
    3. Lance _async_pipeline(gui_manager) dans un thread secondaire
    4. Démarre qt_app.exec() sur le main thread
    """
    from PyQt6.QtWidgets import QApplication

    qt_app = QApplication(sys.argv)

    gui_manager = create_gui_manager(enabled=True)
    gui_manager.start()

    # Lance le pipeline asyncio dans un thread daemon
    pipeline_thread = threading.Thread(
        target=lambda: asyncio.run(_async_pipeline(gui_manager)),
        daemon=True,
        name="JARVIS-AsyncPipeline",
    )
    pipeline_thread.start()

    # Main thread : boucle Qt (bloquant jusqu'à qt_app.quit())
    sys.exit(qt_app.exec())


# ── Point d'entrée ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    gui_enabled = os.getenv("GUI_ENABLED", "true").lower() == "true"
    if gui_enabled:
        _start_with_qt_main_thread()
    else:
        asyncio.run(_async_pipeline())
