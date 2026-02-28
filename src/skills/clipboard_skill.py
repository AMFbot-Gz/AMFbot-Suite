"""
ClipboardSkill — Lecture et écriture dans le presse-papiers via pyperclip.
"""

import asyncio
import logging
from typing import List

from .base_skill import ExecutionContext, Skill, SkillResult

logger = logging.getLogger(__name__)


class ReadClipboardSkill(Skill):
    """Lit le contenu actuel du presse-papiers."""

    name        = "read_clipboard"
    description = "Lit le contenu du presse-papiers"
    examples    = ["qu'est-ce qu'il y a dans mon presse-papiers", "lis le clipboard"]
    params_schema = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    risk_level            = "low"
    requires_confirmation = False

    async def run(self, params: dict, ctx: ExecutionContext) -> SkillResult:
        if ctx.dry_run:
            return await self.simulate(params)
        try:
            import pyperclip
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, pyperclip.paste)
            if not content:
                return SkillResult.ok("Le presse-papiers est vide.", content="")
            preview = content[:200] + ("…" if len(content) > 200 else "")
            return SkillResult.ok(f"Presse-papiers : {preview}", content=content)
        except Exception as e:
            logger.error("ReadClipboard: %s", e)
            return SkillResult.error(f"Impossible de lire le presse-papiers : {e}")

    async def simulate(self, params: dict) -> SkillResult:
        return SkillResult.ok("[SIMULATION] Lirait le presse-papiers")


class WriteClipboardSkill(Skill):
    """Écrit du texte dans le presse-papiers."""

    name        = "write_clipboard"
    description = "Copie du texte dans le presse-papiers"
    examples    = ["copie ça dans le presse-papiers", "mets ce texte dans le clipboard"]
    params_schema = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Texte à copier dans le presse-papiers",
            }
        },
        "required": ["text"],
    }
    risk_level            = "low"
    requires_confirmation = False

    async def run(self, params: dict, ctx: ExecutionContext) -> SkillResult:
        errors = self.validate_params(params)
        if errors:
            return SkillResult.error(f"Paramètres invalides : {', '.join(errors)}")
        if ctx.dry_run:
            return await self.simulate(params)
        try:
            import pyperclip
            text = params["text"]
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, pyperclip.copy, text)
            return SkillResult.ok(f"Copié dans le presse-papiers : {text[:60]}")
        except Exception as e:
            logger.error("WriteClipboard: %s", e)
            return SkillResult.error(f"Impossible d'écrire dans le presse-papiers : {e}")

    async def simulate(self, params: dict) -> SkillResult:
        return SkillResult.ok(f"[SIMULATION] Copierait : {params.get('text', '')[:60]}")
