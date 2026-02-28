"""
NotificationSkill — Notifications desktop macOS.

Utilise osascript (natif macOS) en priorité, plyer en fallback.
"""

import asyncio
import logging
import subprocess

from .base_skill import ExecutionContext, Skill, SkillResult

logger = logging.getLogger(__name__)


class SendNotificationSkill(Skill):
    """Envoie une notification desktop sur macOS."""

    name        = "send_notification"
    description = "Envoie une notification desktop macOS"
    examples    = [
        "envoie-moi une notification dans 5 minutes",
        "notifie-moi quand c'est prêt",
        "affiche une alerte : réunion dans 10 minutes",
    ]
    params_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Titre de la notification",
            },
            "message": {
                "type": "string",
                "description": "Corps de la notification",
            },
            "subtitle": {
                "type": "string",
                "description": "Sous-titre (optionnel)",
            },
        },
        "required": ["title", "message"],
    }
    risk_level            = "low"
    requires_confirmation = False

    async def run(self, params: dict, ctx: ExecutionContext) -> SkillResult:
        errors = self.validate_params(params)
        if errors:
            return SkillResult.error(f"Paramètres invalides : {', '.join(errors)}")
        if ctx.dry_run:
            return await self.simulate(params)

        title    = params["title"]
        message  = params["message"]
        subtitle = params.get("subtitle", "")

        logger.info("Notification: %s — %s", title, message)

        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None, self._notify_sync, title, message, subtitle
        )

        if success:
            return SkillResult.ok(f"Notification envoyée : {title}")
        return SkillResult.error("Impossible d'envoyer la notification")

    def _notify_sync(self, title: str, message: str, subtitle: str = "") -> bool:
        # Méthode 1 : osascript (macOS natif, le plus fiable)
        try:
            script_parts = [f'display notification "{message}"']
            script_parts.append(f'with title "{title}"')
            if subtitle:
                script_parts.append(f'subtitle "{subtitle}"')
            script = " ".join(script_parts)
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return True
        except Exception as e:
            logger.debug("osascript failed: %s", e)

        # Méthode 2 : plyer
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                app_name="JARVIS",
                timeout=5,
            )
            return True
        except Exception as e:
            logger.error("plyer failed: %s", e)

        return False

    async def simulate(self, params: dict) -> SkillResult:
        return SkillResult.ok(
            f"[SIMULATION] Notifierait : {params.get('title')} — {params.get('message')}"
        )
