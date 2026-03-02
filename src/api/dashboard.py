"""
Dashboard FastAPI — Interface web de monitoring JARVIS.

Endpoints :
  GET  /              → UI HTML
  GET  /api/history   → 50 dernières interactions
  GET  /api/config    → Configuration actuelle
  POST /api/config    → Mise à jour config (subset)
  GET  /api/status    → État système temps réel
  GET  /api/skills    → Liste des skills enregistrés
  GET  /api/cache     → Statistiques du cache LRU
"""

import asyncio
import html
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ── App FastAPI ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="JARVIS Antigravity Dashboard",
    version="2.0",
    description="Interface de monitoring et configuration de JARVIS",
)

# État partagé (injecté depuis jarvis_main.py)
_state = {
    "orchestrator":   None,
    "registry":       None,
    "cache":          None,
    "config":         None,
    "state_manager":  None,
    "action_planner": None,
    "main_loop":      None,
    "start_time":     datetime.now().isoformat(),
}


def inject_dependencies(orchestrator=None, registry=None, cache=None, config=None,
                        state_manager=None, action_planner=None, main_loop=None):
    """Injecte les dépendances depuis jarvis_main.py."""
    _state["orchestrator"]   = orchestrator
    _state["registry"]       = registry
    _state["cache"]          = cache
    _state["config"]         = config
    _state["state_manager"]  = state_manager
    _state["action_planner"] = action_planner
    _state["main_loop"]      = main_loop
    logger.info("Dashboard: dépendances injectées")


# ── Static files ──────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_STATIC_DIR   = _PROJECT_ROOT / "static"
_STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# ── Templates ─────────────────────────────────────────────────────────────────

TEMPLATES_DIR = _PROJECT_ROOT / "templates"
templates     = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ── Modèles Pydantic ──────────────────────────────────────────────────────────

class ConfigUpdate(BaseModel):
    llm_model:    Optional[str]   = None
    stt_model:    Optional[str]   = None
    tts_voice:    Optional[str]   = None
    tts_speed:    Optional[float] = None
    vad_threshold: Optional[float] = None
    wake_words:   Optional[list]  = None


class CommandRequest(BaseModel):
    text: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard_ui(request: Request):
    """Sert la page HTML principale."""
    context = {
        "request":    request,
        "title":      "JARVIS Antigravity",
        "start_time": _state["start_time"],
    }
    try:
        return templates.TemplateResponse("index.html", context)
    except Exception:
        # Fallback si le template n'existe pas encore
        return HTMLResponse(content=_fallback_html(), status_code=200)


@app.get("/api/history")
async def get_history() -> JSONResponse:
    """Retourne les 50 dernières interactions."""
    orch = _state.get("orchestrator")
    if orch is None:
        return JSONResponse({"history": [], "count": 0})
    history = orch.history[-50:]
    return JSONResponse({"history": history, "count": len(history)})


@app.get("/api/config")
async def get_config() -> JSONResponse:
    """Retourne la configuration actuelle."""
    cfg = _state.get("config")
    if cfg is None:
        return JSONResponse({"error": "Config non disponible"}, status_code=503)
    return JSONResponse({
        "llm": {
            "model": cfg.llm.model,
            "host":  cfg.llm.host,
        },
        "stt": {
            "model":    cfg.stt.model_name,
            "language": cfg.stt.language,
        },
        "tts": {
            "voice": cfg.tts.voice,
            "speed": cfg.tts.speed,
        },
        "wake_words": cfg.wake_words,
        "debug":      cfg.debug,
    })


@app.post("/api/config")
async def update_config(update: ConfigUpdate) -> JSONResponse:
    """
    Met à jour un sous-ensemble de la configuration en temps réel.
    Certains changements (modèle STT) nécessitent un redémarrage.
    """
    cfg = _state.get("config")
    if cfg is None:
        raise HTTPException(status_code=503, detail="Config non disponible")

    changed = {}
    if update.llm_model is not None:
        cfg.llm.model = update.llm_model
        changed["llm_model"] = update.llm_model
    if update.tts_voice is not None:
        cfg.tts.voice = update.tts_voice
        changed["tts_voice"] = update.tts_voice
    if update.tts_speed is not None:
        cfg.tts.speed = update.tts_speed
        changed["tts_speed"] = update.tts_speed
    if update.wake_words is not None:
        cfg.wake_words = update.wake_words
        changed["wake_words"] = update.wake_words

    logger.info("Config mise à jour : %s", changed)
    return JSONResponse({"updated": changed, "status": "ok"})


@app.get("/api/status")
async def get_status() -> JSONResponse:
    """État système en temps réel."""
    orch     = _state.get("orchestrator")
    registry = _state.get("registry")
    cache    = _state.get("cache")

    state_name = "UNKNOWN"
    if orch and orch.state:
        state_name = orch.state.current.name

    skills_count = len(registry) if registry else 0

    cache_stats = {}
    if cache:
        cache_stats = cache.stats

    return JSONResponse({
        "status":       state_name,
        "start_time":   _state["start_time"],
        "skills_count": skills_count,
        "history_count": len(orch.history) if orch else 0,
        "cache":        cache_stats,
    })


@app.get("/api/skills")
async def get_skills() -> JSONResponse:
    """Liste tous les skills enregistrés."""
    registry = _state.get("registry")
    if registry is None:
        return JSONResponse({"skills": []})

    skills = [
        {
            "name":        s.name,
            "description": s.description,
            "risk_level":  s.risk_level,
            "examples":    s.examples[:2],
        }
        for s in registry.all()
    ]
    return JSONResponse({"skills": skills, "count": len(skills)})


@app.post("/api/command")
async def send_command(cmd: CommandRequest) -> JSONResponse:
    """Injecte une commande texte dans le pipeline JARVIS (simule une entrée STT)."""
    orch = _state.get("orchestrator")
    if orch is None:
        raise HTTPException(status_code=503, detail="Orchestrateur non disponible")
    if not cmd.text.strip():
        raise HTTPException(status_code=400, detail="Commande vide")

    from core.state_manager import JarvisState
    sm = _state.get("state_manager")
    if sm:
        await sm.transition(JarvisState.LISTENING)
    await orch.bus.publish("stt.result", {"text": cmd.text.strip()})
    logger.info("Dashboard /api/command: '%s'", cmd.text[:80])
    return JSONResponse({"status": "dispatched", "command": cmd.text.strip()})


@app.post("/api/chat", response_class=HTMLResponse)
async def chat_endpoint(request: Request, text: str = Form(...)) -> HTMLResponse:
    """
    Interface de chat web — reçoit un message texte, exécute le pipeline JARVIS
    et retourne des éléments HTML pour HTMX (insertion dans #chat-messages).
    """
    text = text.strip()
    if not text:
        return HTMLResponse("")

    user_html   = html.escape(text)
    orch        = _state.get("orchestrator")
    action_plan = _state.get("action_planner")

    # ── Cas 1 : ActionPlanner disponible ──────────────────────────────────
    if action_plan is not None:
        main_loop = _state.get("main_loop")
        try:
            from skills.base_skill import ExecutionContext
            ctx = ExecutionContext(session_id="web-chat")

            if main_loop and main_loop.is_running():
                # Soumettre dans la boucle principale (même loop que aiohttp)
                future = asyncio.run_coroutine_threadsafe(
                    action_plan.plan_and_execute(objective=text, ctx=ctx),
                    main_loop,
                )
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: future.result(timeout=90)
                )
            else:
                result = await asyncio.wait_for(
                    action_plan.plan_and_execute(objective=text, ctx=ctx),
                    timeout=90.0,
                )
            jarvis_text = result.answer or "..."
        except Exception as e:
            jarvis_text = f"[Erreur : {e}]"

    # ── Cas 2 : Fallback via EventBus + polling de l'historique ───────────
    elif orch is not None:
        history_len = len(orch.history)
        try:
            await orch.bus.publish("stt.result", {"text": text})
        except Exception as e:
            jarvis_text = f"[Erreur dispatch : {e}]"
        else:
            jarvis_text = "[Commande envoyée — vérifiez l'onglet Dashboard]"
            for _ in range(40):
                await asyncio.sleep(0.5)
                if len(orch.history) > history_len:
                    entry = orch.history[-1]
                    jarvis_text = entry.get("response") or entry.get("text", "...")
                    break

    else:
        jarvis_text = "JARVIS n'est pas encore initialisé. Relancez le système."

    jarvis_html = html.escape(str(jarvis_text))
    return HTMLResponse(f"""
<div class="msg msg-user">
  <span class="role">VOUS</span>
  <p>{user_html}</p>
</div>
<div class="msg msg-jarvis">
  <span class="role">JARVIS</span>
  <p>{jarvis_html}</p>
</div>
""")


@app.get("/api/cache")
async def get_cache_stats() -> JSONResponse:
    """Statistiques du cache LRU."""
    cache = _state.get("cache")
    if cache is None:
        return JSONResponse({"error": "Cache non disponible"})
    return JSONResponse(cache.stats)


@app.delete("/api/cache")
async def clear_cache() -> JSONResponse:
    """Vide le cache LRU."""
    cache = _state.get("cache")
    if cache:
        cache.clear()
    return JSONResponse({"status": "cleared"})


# ── HTML fallback ─────────────────────────────────────────────────────────────

def _fallback_html() -> str:
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>JARVIS</title></head>
<body style="background:#0a0a14;color:#e0e8ff;font-family:monospace;padding:2rem">
<h1>JARVIS Antigravity Dashboard</h1>
<p>Template non trouvé — accédez aux APIs directement :</p>
<ul>
  <li><a href="/api/status" style="color:#64aaff">/api/status</a></li>
  <li><a href="/api/history" style="color:#64aaff">/api/history</a></li>
  <li><a href="/api/skills" style="color:#64aaff">/api/skills</a></li>
  <li><a href="/docs" style="color:#64aaff">/docs (Swagger)</a></li>
</ul>
</body></html>"""
