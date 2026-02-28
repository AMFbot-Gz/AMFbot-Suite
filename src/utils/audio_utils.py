"""
AudioUtils — Utilitaires audio : conversion, normalisation, I/O.
"""

import asyncio
import logging
import wave
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AudioUtils:
    """Outils de manipulation audio pour le pipeline JARVIS."""

    SAMPLE_RATE = 16000
    CHANNELS    = 1
    SAMPLE_WIDTH = 2  # 16-bit

    @staticmethod
    def save_wav(audio_bytes: bytes, path: Path, sample_rate: int = 16000) -> Path:
        """Sauvegarde des bytes PCM bruts en fichier WAV."""
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(AudioUtils.CHANNELS)
            wf.setsampwidth(AudioUtils.SAMPLE_WIDTH)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_bytes)
        return path

    @staticmethod
    def load_wav(path: Path) -> bytes:
        """Charge un fichier WAV et retourne les bytes PCM bruts."""
        with wave.open(str(path), "rb") as wf:
            return wf.readframes(wf.getnframes())

    @staticmethod
    def bytes_to_duration_ms(audio_bytes: bytes, sample_rate: int = 16000) -> float:
        """Calcule la durée en ms d'un buffer PCM 16bit mono."""
        num_samples = len(audio_bytes) // 2  # 2 bytes par sample (16-bit)
        return (num_samples / sample_rate) * 1000

    @staticmethod
    async def record_microphone(
        duration_s: float,
        sample_rate: int = 16000,
        output_queue: Optional[asyncio.Queue] = None,
    ) -> Optional[bytes]:
        """
        Enregistre depuis le microphone.
        Nécessite sounddevice : pip install sounddevice
        """
        try:
            import sounddevice as sd
            import numpy as np

            logger.info("Enregistrement: %.1fs @ %dHz", duration_s, sample_rate)
            loop = asyncio.get_event_loop()

            audio = await loop.run_in_executor(
                None,
                lambda: sd.rec(
                    int(duration_s * sample_rate),
                    samplerate=sample_rate,
                    channels=1,
                    dtype="int16",
                    blocking=True,
                )
            )

            audio_bytes = audio.tobytes()

            if output_queue:
                await output_queue.put(audio_bytes)

            return audio_bytes

        except ImportError:
            logger.error("sounddevice non installé: pip install sounddevice")
            return None
        except Exception as e:
            logger.error("Erreur enregistrement: %s", e)
            return None
