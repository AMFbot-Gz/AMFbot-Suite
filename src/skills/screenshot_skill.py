"""
ScreenshotSkill — Capture d'écran + OCR.

Dépendances :
    pyautogui  → capture écran
    pytesseract → OCR (nécessite tesseract-ocr installé sur le système)
    Pillow     → traitement image
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict

from .base_skill import ExecutionContext, Skill, SkillResult

logger = logging.getLogger(__name__)


class TakeScreenshotSkill(Skill):
    name        = "take_screenshot"
    description = "Prend une capture d'écran et la sauvegarde"
    examples    = ["prends une capture d'écran", "screenshot", "capture l'écran"]
    risk_level  = "low"

    params_schema = {
        "save_path": "Chemin de sauvegarde (défaut: ~/Desktop/screenshot.png)",
        "region": "Zone à capturer : [x, y, w, h] (défaut: plein écran)",
    }

    async def run(self, params: Dict[str, Any], ctx: ExecutionContext) -> SkillResult:
        save_path = params.get("save_path") or str(
            Path.home() / "Desktop" / "jarvis_screenshot.png"
        )
        region = params.get("region")  # [x, y, w, h] ou None

        try:
            import pyautogui
        except ImportError:
            return SkillResult.error("pyautogui non installé")

        try:
            path = await asyncio.to_thread(
                self._capture, save_path, region, pyautogui
            )
            return SkillResult.ok(
                f"Screenshot sauvegardé : {path}",
                data={"path": path}
            )
        except Exception as e:
            logger.error("Screenshot error: %s", e)
            return SkillResult.error(f"Erreur capture : {e}")

    def _capture(self, save_path: str, region, pyautogui) -> str:
        from PIL import Image

        if region and len(region) == 4:
            screenshot = pyautogui.screenshot(region=tuple(region))
        else:
            screenshot = pyautogui.screenshot()

        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        screenshot.save(save_path)
        return save_path


class OCRScreenSkill(Skill):
    name        = "ocr_screen"
    description = "Capture l'écran et extrait le texte visible via OCR"
    examples    = [
        "lis ce qui est écrit à l'écran",
        "récupère le texte de l'écran",
        "que dit l'erreur à l'écran ?",
    ]
    risk_level  = "low"

    params_schema = {
        "region":   "Zone à analyser : [x, y, w, h] (défaut: plein écran)",
        "lang":     "Langue OCR (défaut: fra+eng)",
        "save_img": "Sauvegarder l'image (défaut: false)",
    }

    async def run(self, params: Dict[str, Any], ctx: ExecutionContext) -> SkillResult:
        region   = params.get("region")
        lang     = params.get("lang", "fra+eng")
        save_img = str(params.get("save_img", "false")).lower() == "true"

        try:
            import pytesseract
            import pyautogui
        except ImportError as e:
            return SkillResult.error(f"Dépendance manquante : {e}")

        try:
            text, img_path = await asyncio.to_thread(
                self._ocr, region, lang, save_img, pytesseract, pyautogui
            )
        except Exception as e:
            logger.error("OCR error: %s", e)
            return SkillResult.error(f"Erreur OCR : {e}")

        if not text.strip():
            return SkillResult.ok("Aucun texte détecté à l'écran.", data={"text": ""})

        msg = f"Texte extrait ({len(text)} caractères) :\n{text[:800]}"
        if img_path:
            msg += f"\nImage sauvegardée : {img_path}"

        return SkillResult.ok(msg, data={"text": text, "img_path": img_path})

    def _ocr(self, region, lang, save_img, pytesseract, pyautogui) -> tuple:
        from PIL import Image

        if region and len(region) == 4:
            screenshot = pyautogui.screenshot(region=tuple(region))
        else:
            screenshot = pyautogui.screenshot()

        img_path = None
        if save_img:
            img_path = str(Path.home() / "Desktop" / "jarvis_ocr.png")
            screenshot.save(img_path)

        text = pytesseract.image_to_string(screenshot, lang=lang)
        return text, img_path
