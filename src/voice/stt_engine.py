"""
STTEngine — Transcription audio via faster-whisper (CTranslate2).

Avantages faster-whisper vs openai-whisper :
  - 4x plus rapide, ~2x moins de mémoire
  - Support VAD intégré (silero-vad)
  - Compatible Apple Silicon (MPS) et CPU
"""

import asyncio
import logging
from pathlib import Path
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)


class STTEngine:
    """
    Moteur de reconnaissance vocale basé sur faster-whisper.

    Utilisation :
        engine = STTEngine(model_name="small")
        await engine.load()
        text = await engine.transcribe_file(Path("audio.wav"))
    """

    SUPPORTED_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]

    def __init__(
        self,
        model_name: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "fr",
        models_dir: Optional[Path] = None,
    ):
        self.model_name   = model_name
        self.device       = device
        self.compute_type = compute_type
        self.language     = language
        self.models_dir   = models_dir or (Path.home() / "jarvis_antigravity" / "models")
        self._model       = None
        self._loaded      = False

    async def load(self) -> None:
        """Charge le modèle Whisper en arrière-plan (non-bloquant)."""
        logger.info("Chargement STT: %s (%s/%s)", self.model_name, self.device, self.compute_type)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_sync)
        self._loaded = True
        logger.info("STT prêt: %s", self.model_name)

    def _load_sync(self) -> None:
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
                download_root=str(self.models_dir),
            )
        except ImportError:
            logger.error("faster-whisper non installé. Run: pip install faster-whisper")
            raise
        except Exception as e:
            logger.error(
                "STT: impossible de charger le modèle '%s' (modèle introuvable ?) : %s",
                self.model_name, e,
            )
            raise

    async def transcribe_file(self, audio_path: Path) -> str:
        """Transcrit un fichier audio. Retourne le texte."""
        if not self._loaded:
            await self.load()

        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, self._transcribe_sync, audio_path)
        logger.info("Transcription: '%s'", text[:80])
        return text

    def _transcribe_sync(self, audio_path: Path) -> str:
        try:
            segments, _info = self._model.transcribe(
                str(audio_path),
                language=self.language,
                vad_filter=True,           # Filtre silences avec silero-vad
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200,
                ),
            )
            return " ".join(seg.text.strip() for seg in segments).strip()
        except FileNotFoundError:
            logger.error("STT: fichier audio introuvable: %s", audio_path)
            return ""
        except RuntimeError as e:
            logger.error("STT: erreur faster-whisper (audio corrompu ?) : %s", e)
            return ""
        except Exception as e:
            logger.error("STT: erreur inattendue lors de la transcription: %s", e)
            return ""

    async def transcribe_stream(self, audio_queue: asyncio.Queue) -> AsyncIterator[str]:
        """
        Transcrit en continu depuis une queue d'audio (bytes PCM 16kHz).
        Yielde les transcriptions au fur et à mesure.

        Le producteur (VAD/microphone) place des chunks audio dans la queue.
        None dans la queue = fin du stream.
        """
        if not self._loaded:
            await self.load()

        import tempfile
        import wave

        buffer = bytearray()

        while True:
            chunk = await audio_queue.get()

            if chunk is None:
                # Fin du stream
                break

            buffer.extend(chunk)

            # Transcrit dès qu'on a ~2s d'audio (32000 bytes @ 16kHz 16bit mono)
            if len(buffer) >= 32000:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    with wave.open(tmp.name, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(16000)
                        wf.writeframes(bytes(buffer))
                    tmp_path = Path(tmp.name)

                text = await self.transcribe_file(tmp_path)
                tmp_path.unlink(missing_ok=True)
                buffer.clear()

                if text:
                    yield text
