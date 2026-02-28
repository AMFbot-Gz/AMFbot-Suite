"""
VADProcessor — Détection d'activité vocale via silero-vad.

Rôle : ne déclencher la transcription que quand quelqu'un parle.
Réduit drastiquement la charge CPU et les faux positifs STT.
"""

import asyncio
import logging
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)

# Paramètres silero-vad recommandés
VAD_THRESHOLD       = 0.5   # Probabilité min pour considérer comme parole
SAMPLE_RATE         = 16000
WINDOW_SIZE_SAMPLES = 512   # ~32ms à 16kHz


class VADProcessor:
    """
    Filtre un flux audio brut et ne transmet que les segments de parole.

    Utilisation :
        vad = VADProcessor()
        await vad.load()
        async for speech_chunk in vad.process(raw_audio_queue):
            await stt_queue.put(speech_chunk)
    """

    def __init__(
        self,
        threshold: float = VAD_THRESHOLD,
        sample_rate: int = SAMPLE_RATE,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 600,
    ):
        self.threshold                = threshold
        self.sample_rate              = sample_rate
        self.min_speech_duration_ms   = min_speech_duration_ms
        self.min_silence_duration_ms  = min_silence_duration_ms
        self._model                   = None
        self._loaded                  = False

    async def load(self) -> None:
        """Charge le modèle silero-vad (torch requis)."""
        logger.info("Chargement VAD silero...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_sync)
        self._loaded = True
        logger.info("VAD prêt")

    def _load_sync(self) -> None:
        try:
            import torch
            model, _ = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                onnx=False,
            )
            self._model = model
        except Exception as e:
            logger.error("Erreur chargement VAD: %s", e)
            raise

    def is_speech(self, audio_chunk: bytes) -> bool:
        """Retourne True si le chunk contient de la parole."""
        if not self._loaded or self._model is None:
            return True  # Fail-open : passer sans VAD

        try:
            import torch
            audio_tensor = torch.frombuffer(audio_chunk, dtype=torch.int16).float() / 32768.0
            confidence = self._model(audio_tensor, self.sample_rate).item()
            return confidence >= self.threshold
        except Exception:
            return True

    async def process(self, raw_queue: asyncio.Queue) -> AsyncIterator[bytes]:
        """
        Consomme la raw_queue, ne yielde que les chunks avec parole.
        None dans la queue = signal d'arrêt.
        """
        if not self._loaded:
            await self.load()

        speech_buffer = bytearray()
        silence_frames = 0
        is_speaking = False
        frames_per_ms = self.sample_rate // 1000

        while True:
            chunk = await raw_queue.get()

            if chunk is None:
                if speech_buffer:
                    yield bytes(speech_buffer)
                break

            if self.is_speech(chunk):
                speech_buffer.extend(chunk)
                silence_frames = 0
                is_speaking = True
            elif is_speaking:
                silence_frames += len(chunk) // (2 * frames_per_ms)  # ms approximatifs
                speech_buffer.extend(chunk)  # inclure silence post-parole

                if silence_frames >= self.min_silence_duration_ms:
                    # Silence assez long → fin d'utterance
                    if len(speech_buffer) > 0:
                        yield bytes(speech_buffer)
                    speech_buffer.clear()
                    silence_frames = 0
                    is_speaking = False
