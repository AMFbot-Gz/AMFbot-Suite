"""
ProcessManagerSkill — Gestion des processus via psutil.

RISQUE CRITIQUE : tuer un processus est irréversible.
SafetyGuard demandera confirmation systématique.
"""

import asyncio
import logging

from .base_skill import ExecutionContext, Skill, SkillResult

logger = logging.getLogger(__name__)


class ListProcessesSkill(Skill):
    """Liste les processus en cours avec leur consommation CPU/RAM."""

    name        = "list_processes"
    description = "Liste les processus système avec CPU et RAM"
    examples    = [
        "quels processus tournent",
        "qu'est-ce qui consomme le plus de CPU",
        "liste les applications actives",
    ]
    params_schema = {
        "type": "object",
        "properties": {
            "sort_by": {
                "type": "string",
                "description": "Critère de tri : cpu, memory, name (défaut: cpu)",
                "enum": ["cpu", "memory", "name"],
            },
            "limit": {
                "type": "integer",
                "description": "Nombre max de processus à retourner (défaut: 10)",
            },
        },
        "required": [],
    }
    risk_level            = "low"
    requires_confirmation = False

    async def run(self, params: dict, ctx: ExecutionContext) -> SkillResult:
        sort_by = params.get("sort_by", "cpu")
        limit   = params.get("limit", 10)

        try:
            import psutil
            loop = asyncio.get_event_loop()
            procs = await loop.run_in_executor(None, self._list_sync, sort_by, limit)
            lines = [f"• {p['name']:25} CPU:{p['cpu']:5.1f}%  RAM:{p['mem']:5.1f}%  PID:{p['pid']}" for p in procs]
            return SkillResult.ok(
                f"Top {limit} processus (tri: {sort_by}) :\n" + "\n".join(lines),
                processes=procs,
            )
        except ImportError:
            return SkillResult.error("psutil non installé : pip install psutil")
        except Exception as e:
            return SkillResult.error(f"Erreur liste processus : {e}")

    def _list_sync(self, sort_by: str, limit: int):
        import psutil
        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = proc.info
                procs.append({
                    "pid":  info["pid"],
                    "name": info["name"] or "?",
                    "cpu":  info["cpu_percent"] or 0.0,
                    "mem":  info["memory_percent"] or 0.0,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        key_map = {"cpu": "cpu", "memory": "mem", "name": "name"}
        reverse = sort_by != "name"
        procs.sort(key=lambda p: p[key_map.get(sort_by, "cpu")], reverse=reverse)
        return procs[:limit]


class KillProcessSkill(Skill):
    """Termine un processus par PID ou par nom."""

    name        = "kill_process"
    description = "Termine (kill) un processus système par PID ou nom"
    examples    = [
        "tue le processus Chrome",
        "kill le PID 1234",
        "force-quitte Spotify",
    ]
    params_schema = {
        "type": "object",
        "properties": {
            "pid": {
                "type": "integer",
                "description": "PID du processus à tuer",
            },
            "name": {
                "type": "string",
                "description": "Nom du processus à tuer (partiel accepté)",
            },
            "force": {
                "type": "boolean",
                "description": "Forcer avec SIGKILL (défaut: false = SIGTERM)",
            },
        },
        "required": [],
    }
    risk_level            = "critical"
    requires_confirmation = True

    async def run(self, params: dict, ctx: ExecutionContext) -> SkillResult:
        if not params.get("pid") and not params.get("name"):
            return SkillResult.error("Paramètre requis : 'pid' ou 'name'")
        if not ctx.confirmed and not ctx.dry_run:
            return SkillResult.error("Confirmation requise pour tuer un processus")
        if ctx.dry_run:
            return await self.simulate(params)

        force = params.get("force", False)
        try:
            import psutil, signal as sig
            loop = asyncio.get_event_loop()
            killed = await loop.run_in_executor(None, self._kill_sync, params, force)
            if killed:
                return SkillResult.ok(f"Processus terminé : {killed}")
            return SkillResult.error("Processus introuvable")
        except ImportError:
            return SkillResult.error("psutil non installé")
        except Exception as e:
            logger.error("KillProcess: %s", e)
            return SkillResult.error(f"Erreur : {e}")

    def _kill_sync(self, params: dict, force: bool) -> str:
        import psutil, signal as sig

        signal = sig.SIGKILL if force else sig.SIGTERM
        killed = []

        # Par PID
        if params.get("pid"):
            try:
                proc = psutil.Process(params["pid"])
                name = proc.name()
                proc.send_signal(signal)
                killed.append(f"{name} (PID {params['pid']})")
            except psutil.NoSuchProcess:
                pass

        # Par nom
        elif params.get("name"):
            pattern = params["name"].lower()
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    if pattern in (proc.info["name"] or "").lower():
                        proc.send_signal(signal)
                        killed.append(f"{proc.info['name']} (PID {proc.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        return ", ".join(killed) if killed else ""

    async def simulate(self, params: dict) -> SkillResult:
        target = params.get("name") or f"PID {params.get('pid')}"
        return SkillResult.ok(f"[SIMULATION] Tuerait le processus : {target}")
