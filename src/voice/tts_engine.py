"""
TTSEngine v2 — Synthèse vocale avec streaming par phrases.

Nouveau : speak_async_stream() lit les tokens LLM depuis une Queue
et parle dès qu'une phrase complète est détectée — réduit la latence
de plusieurs secondes à ~300ms (temps d'arrivée de la 1ère phrase).
"""

import asyncio
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Marqueurs de fin de phrase pour le découpage du stream
SENTENCE_ENDINGS = re.compile(r"(?<=[.!?;:\n])\s+|(?<=[,])\s{2,}")


class TTSEngine:
    """
    Synthèse vocale piper-tts + fallback say(macOS).

    Méthodes :
        speak(text)                  — phrase complète, bloquant
        speak_stream(queue)          — queue de phrases complètes
        speak_async_stream(queue)    — queue de TOKENS LLM bruts
                                       (découpe en phrases automatiquement)
    """

    def __init__(
        self,
        voice: str = "fr_FR-siwis-medium",
        models_dir: Optional[Path] = None,
        speed: float = 1.0,
    ):
        self.voice      = voice
        self.models_dir = models_dir or (Path.home() / "jarvis_antigravity" / "models" / "tts")
        self.speed      = speed
        self._piper_bin = "piper"
        self._speaking  = asyncio.Lock()

    # ── Synthèse d'une phrase ──────────────────────────────────────────────────

    async def speak(self, text: str) -> None:
        """Synthétise et joue une phrase complète."""
        text = text.strip()
        if not text:
            return
        logger.info("TTS speak: '%s'", text[:60])
        async with self._speaking:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._speak_sync, text)

    def _speak_sync(self, text: str) -> None:
        model_path = self.models_dir / f"{self.voice}.onnx"
        try:
            if not model_path.exists():
                logger.debug("Modèle TTS absent — fallback say()")
                subprocess.run(["say", "-r", "200", text], check=False, timeout=30)
                return

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = Path(tmp.name)

            result = subprocess.run(
                [
                    self._piper_bin,
                    "--model",        str(model_path),
                    "--output_file",  str(tmp_path),
                    "--length_scale", str(1.0 / self.speed),
                ],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.error("Piper: %s", result.stderr.decode()[:100])
                subprocess.run(["say", text], check=False)
                return

            subprocess.run(["afplay", str(tmp_path)], check=False)
            tmp_path.unlink(missing_ok=True)

        except FileNotFoundError:
            subprocess.run(["say", "-r", "200", text], check=False)
        except Exception as e:
            logger.error("TTS error: %s", e)

    # ── Queue de phrases complètes ─────────────────────────────────────────────

    async def speak_stream(self, text_queue: asyncio.Queue) -> None:
        """
        Consomme une queue de phrases complètes et les synthétise.
        None dans la queue = signal d'arrêt.
        """
        while True:
            text = await text_queue.get()
            if text is None:
                break
            await self.speak(text)

    # ── Streaming de tokens LLM ────────────────────────────────────────────────

    async def speak_async_stream(self, token_queue: asyncio.Queue) -> None:
        """
        Consomme un flux de TOKENS LLM bruts depuis token_queue.
        Accumule les tokens et parle dès qu'une phrase est complète.

        Stratégie de découpage :
        1. Fin de phrase dure  (.  !  ?  \\n) → parler immédiatement
        2. Fin de phrase molle (, ; :)        → parler si buffer > 40 chars
        3. Timeout 3s sans nouveau token      → parler le buffer restant
        4. None dans la queue                 → vider le buffer et s'arrêter

        Résultat : latence ~300ms (1ère phrase) au lieu d'attendre toute la réponse.
        """
        HARD_ENDINGS = frozenset(".!?\n")
        SOFT_ENDINGS = frozenset(",;:")
        SOFT_MIN_LEN = 40
        FLUSH_TIMEOUT = 3.0

        buffer = ""

        while True:
            try:
                token = await asyncio.wait_for(token_queue.get(), timeout=FLUSH_TIMEOUT)
            except asyncio.TimeoutError:
                # Aucun token depuis FLUSH_TIMEOUT secondes → vider le buffer
                if buffer.strip():
                    await self.speak(buffer.strip())
                    buffer = ""
                continue

            if token is None:
                # Signal de fin — vider ce qui reste
                if buffer.strip():
                    await self.speak(buffer.strip())
                break

            buffer += token

            # Vérifier si on peut parler
            last_char = buffer.rstrip()[-1] if buffer.rstrip() else ""

            if last_char in HARD_ENDINGS:
                sentence = buffer.strip()
                if sentence:
                    await self.speak(sentence)
                buffer = ""

            elif last_char in SOFT_ENDINGS and len(buffer) >= SOFT_MIN_LEN:
                sentence = buffer.strip()
                if sentence:
                    await self.speak(sentence)
                buffer = ""
