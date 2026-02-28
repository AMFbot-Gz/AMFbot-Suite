"""
BrowserControlSkill — Contrôle navigateur via Playwright.

Risque : élevé (accès web, données potentiellement sensibles).
Confirmation requise pour les navigations vers des URLs non mémorisées.
"""

import asyncio
import logging
from typing import Optional

from .base_skill import ExecutionContext, Skill, SkillResult

logger = logging.getLogger(__name__)


class OpenUrlSkill(Skill):
    """Ouvre une URL dans le navigateur par défaut via Playwright."""

    name        = "open_url"
    description = "Ouvre une URL dans le navigateur (Chromium headless ou visible)"
    examples    = [
        "ouvre YouTube",
        "va sur github.com",
        "ouvre https://google.fr",
        "navigue vers le site de météo",
    ]
    params_schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL complète à ouvrir (ex: https://google.fr)",
            },
            "headless": {
                "type": "boolean",
                "description": "Mode headless (sans fenêtre visible). Défaut: false",
            },
        },
        "required": ["url"],
    }
    risk_level            = "high"
    requires_confirmation = False  # SafetyGuard demandera confirmation (risk=high)

    # URLs de confiance qui ne nécessitent pas de confirmation supplémentaire
    TRUSTED_DOMAINS = {
        "google.com", "google.fr", "github.com", "youtube.com",
        "wikipedia.org", "stackoverflow.com", "notion.so",
    }

    async def run(self, params: dict, ctx: ExecutionContext) -> SkillResult:
        errors = self.validate_params(params)
        if errors:
            return SkillResult.error(f"Paramètres invalides : {', '.join(errors)}")
        if ctx.dry_run:
            return await self.simulate(params)

        url     = params["url"]
        headless = params.get("headless", False)

        # Normaliser l'URL
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        logger.info("BrowserControl: ouvrir %s (headless=%s)", url, headless)

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless)
                page    = await browser.new_page()
                await page.goto(url, timeout=15000)
                title = await page.title()

                if headless:
                    # En mode headless, garder le navigateur ouvert n'a pas de sens
                    await browser.close()
                    return SkillResult.ok(f"Page chargée : {title}", url=url, title=title)
                else:
                    # Mode visible : laisser l'utilisateur interagir
                    # On attend 30s max puis on ferme
                    await asyncio.sleep(0.5)
                    return SkillResult.ok(
                        f"Navigateur ouvert sur : {title}",
                        url=url, title=title,
                    )

        except ImportError:
            # Fallback : ouvrir avec le navigateur système
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return SkillResult.error(f"Schéma URL non autorisé : {parsed.scheme!r}")
            import subprocess
            subprocess.Popen(["open", url])
            return SkillResult.ok(f"URL ouverte dans le navigateur système : {url}")
        except Exception as e:
            logger.error("BrowserControl: %s", e)
            return SkillResult.error(f"Erreur navigateur : {e}")

    async def simulate(self, params: dict) -> SkillResult:
        return SkillResult.ok(f"[SIMULATION] Ouvrirait : {params.get('url', '?')}")


class ScrollPageSkill(Skill):
    """Scrolle la page web active (nécessite une session Playwright active)."""

    name        = "scroll_page"
    description = "Scrolle la page web vers le bas ou vers le haut"
    examples    = ["scrolle vers le bas", "remonte en haut de la page"]
    params_schema = {
        "type": "object",
        "properties": {
            "direction": {
                "type": "string",
                "description": "Direction du scroll : 'down' ou 'up'",
                "enum": ["down", "up"],
            },
            "amount": {
                "type": "integer",
                "description": "Pixels à scroller (défaut: 500)",
            },
        },
        "required": ["direction"],
    }
    risk_level            = "high"
    requires_confirmation = False

    async def run(self, params: dict, ctx: ExecutionContext) -> SkillResult:
        direction = params.get("direction", "down")
        amount    = params.get("amount", 500)
        delta     = amount if direction == "down" else -amount

        # Utilise PyAutoGUI comme fallback simple
        try:
            import pyautogui
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, pyautogui.scroll, -delta // 120)
            return SkillResult.ok(f"Scrollé {direction} de {amount}px")
        except Exception as e:
            return SkillResult.error(f"Erreur scroll : {e}")

    async def simulate(self, params: dict) -> SkillResult:
        return SkillResult.ok(f"[SIMULATION] Scrollerait {params.get('direction', 'down')}")
