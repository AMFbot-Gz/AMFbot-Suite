"""
SystemSkill — Skill système multi-OS : ouvrir des applications.

Exemple concret d'implémentation de l'interface Skill.
Compatible macOS (priorité), Linux, Windows.
"""

import asyncio
import logging
import platform
import subprocess
from datetime import datetime
from typing import List

from ..base_skill import ExecutionContext, Skill, SkillResult

logger = logging.getLogger(__name__)

OS = platform.system()  # "Darwin", "Linux", "Windows"


class OpenAppSkill(Skill):
    """Ouvre une application par son nom."""

    name        = "open_app"
    description = "Ouvre une application sur macOS/Linux/Windows"
    examples    = [
        "ouvre Chrome",
        "lance VSCode",
        "ouvre le terminal",
        "démarre Slack",
    ]
    params_schema = {
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "description": "Nom de l'application à ouvrir (ex: Chrome, VSCode)",
            }
        },
        "required": ["app_name"],
    }
    risk_level            = "low"
    requires_confirmation = False

    # Aliases communs
    APP_ALIASES = {
        "chrome":    "Google Chrome",
        "vscode":    "Visual Studio Code",
        "terminal":  "Terminal",
        "iterm":     "iTerm",
        "finder":    "Finder",
        "slack":     "Slack",
        "notion":    "Notion",
        "spotify":   "Spotify",
    }

    async def run(self, params: dict, ctx: ExecutionContext) -> SkillResult:
        errors = self.validate_params(params)
        if errors:
            return SkillResult.error(f"Paramètres invalides: {', '.join(errors)}")

        app_name = params["app_name"]
        # Résoudre l'alias
        resolved = self.APP_ALIASES.get(app_name.lower(), app_name)

        if ctx.dry_run:
            return await self.simulate(params)

        logger.info("Ouverture de '%s' (→ '%s') sur %s", app_name, resolved, OS)

        try:
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, self._open_sync, resolved)

            if success:
                return SkillResult.ok(f"{resolved} ouvert.")
            else:
                return SkillResult.error(f"Impossible d'ouvrir {resolved}.")

        except Exception as e:
            logger.error("OpenApp error: %s", e)
            return SkillResult.error(f"Erreur: {e}")

    def _open_sync(self, app_name: str) -> bool:
        try:
            if OS == "Darwin":
                result = subprocess.run(
                    ["open", "-a", app_name],
                    capture_output=True, timeout=10
                )
                return result.returncode == 0

            elif OS == "Linux":
                result = subprocess.run(
                    [app_name.lower()],
                    capture_output=True, timeout=10
                )
                return result.returncode == 0

            elif OS == "Windows":
                subprocess.Popen(["start", app_name], shell=True)
                return True

        except Exception as e:
            logger.error("_open_sync: %s", e)
            return False

    async def simulate(self, params: dict) -> SkillResult:
        app_name = params.get("app_name", "?")
        return SkillResult.ok(f"[SIMULATION] Ouvrirait l'application: {app_name}")


class GetSystemInfoSkill(Skill):
    """Retourne des informations système (CPU, RAM, disque)."""

    name        = "get_system_info"
    description = "Obtient les informations système : CPU, RAM, disque"
    examples    = [
        "quel est l'état du système",
        "combien de RAM il reste",
        "utilisation disque",
    ]
    params_schema = {
        "type": "object",
        "properties": {
            "info_type": {
                "type": "string",
                "description": "Type d'info: cpu, ram, disk, all",
                "enum": ["cpu", "ram", "disk", "all"],
            }
        },
        "required": [],
    }
    risk_level            = "low"
    requires_confirmation = False

    async def run(self, params: dict, ctx: ExecutionContext) -> SkillResult:
        info_type = params.get("info_type", "all")
        loop = asyncio.get_event_loop()

        if info_type in ("cpu", "all"):
            cpu = await loop.run_in_executor(None, self._get_cpu)
        if info_type in ("ram", "all"):
            ram = await loop.run_in_executor(None, self._get_ram)
        if info_type in ("disk", "all"):
            disk = await loop.run_in_executor(None, self._get_disk)

        parts = []
        if info_type in ("cpu", "all"):
            parts.append(f"CPU: {cpu}")
        if info_type in ("ram", "all"):
            parts.append(f"RAM: {ram}")
        if info_type in ("disk", "all"):
            parts.append(f"Disque: {disk}")

        return SkillResult.ok(", ".join(parts))

    def _get_cpu(self) -> str:
        try:
            result = subprocess.run(
                ["top", "-l", "1", "-s", "0"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n"):
                if "CPU usage" in line:
                    return line.strip()
            return "N/A"
        except Exception:
            return "N/A"

    def _get_ram(self) -> str:
        try:
            result = subprocess.run(
                ["vm_stat"],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.split("\n")
            pages_free = 0
            for line in lines:
                if "Pages free" in line:
                    pages_free = int(line.split(":")[1].strip().rstrip("."))
            free_mb = (pages_free * 4096) // (1024 * 1024)
            return f"{free_mb} MB libres"
        except Exception:
            return "N/A"

    def _get_disk(self) -> str:
        try:
            result = subprocess.run(
                ["df", "-h", "/"],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                return f"{parts[3]} libres / {parts[1]} total"
            return "N/A"
        except Exception:
            return "N/A"


class GetTimeSkill(Skill):
    """Retourne la date et l'heure actuelles."""

    name        = "get_time"
    description = "Retourne la date et l'heure actuelles du système"
    examples    = [
        "quelle heure est-il",
        "quelle est la date",
        "quel jour sommes-nous",
    ]
    params_schema = {}
    risk_level            = "low"
    requires_confirmation = False

    async def run(self, params: dict, ctx: ExecutionContext) -> SkillResult:
        now = datetime.now()
        jours = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]
        mois  = ["janvier","février","mars","avril","mai","juin",
                 "juillet","août","septembre","octobre","novembre","décembre"]
        jour  = jours[now.weekday()]
        mois_ = mois[now.month - 1]
        result = f"Il est {now.strftime('%H:%M:%S')}, le {jour} {now.day} {mois_} {now.year}"
        return SkillResult.ok(result)
