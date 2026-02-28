"""
Config — Gestion centralisée de la configuration via .env + valeurs par défaut.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

BASE_DIR = Path.home() / "jarvis_antigravity"
load_dotenv(BASE_DIR / ".env")


@dataclass
class AudioConfig:
    sample_rate: int   = 16000
    channels: int      = 1
    chunk_size: int    = 512
    input_device: Optional[str] = None


@dataclass
class STTConfig:
    model_name: str    = "small"
    device: str        = "cpu"
    compute_type: str  = "int8"
    language: str      = "fr"


@dataclass
class TTSConfig:
    voice: str         = "fr_FR-siwis-medium"
    speed: float       = 1.0


@dataclass
class LLMConfig:
    model: str         = "mistral"
    host: str          = "http://localhost:11434"
    temperature: float = 0.1
    max_tokens: int    = 1024


@dataclass
class Config:
    """Configuration globale de JARVIS Antigravity."""

    # Chemins
    base_dir:    Path = BASE_DIR
    models_dir:  Path = BASE_DIR / "models"
    logs_dir:    Path = BASE_DIR / "logs"
    data_dir:    Path = BASE_DIR / "data"

    # Wake word
    wake_words: List[str] = field(default_factory=lambda: ["jarvis", "hey jarvis"])

    # Sous-configs
    audio: AudioConfig = field(default_factory=AudioConfig)
    stt:   STTConfig   = field(default_factory=STTConfig)
    tts:   TTSConfig   = field(default_factory=TTSConfig)
    llm:   LLMConfig   = field(default_factory=LLMConfig)

    # Debug
    debug: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        """Charge la configuration depuis les variables d'environnement."""
        return cls(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            audio=AudioConfig(
                sample_rate=int(os.getenv("AUDIO_SAMPLE_RATE", "16000")),
            ),
            stt=STTConfig(
                model_name=os.getenv("STT_MODEL", "small"),
                language=os.getenv("STT_LANGUAGE", "fr"),
            ),
            tts=TTSConfig(
                voice=os.getenv("TTS_VOICE", "fr_FR-siwis-medium"),
            ),
            llm=LLMConfig(
                model=os.getenv("LLM_MODEL", "mistral"),
                host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            ),
        )
