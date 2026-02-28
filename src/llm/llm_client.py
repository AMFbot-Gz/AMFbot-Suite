"""
LLMClient v2 — Client Ollama avec function calling, streaming, cache et tool_choice.
"""

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Dict, List, Literal, Optional

import aiohttp

logger = logging.getLogger(__name__)

OLLAMA_HOST = "http://localhost:11434"
ToolChoice  = Literal["auto", "none", "required"]


class LLMResponse:
    def __init__(
        self,
        text: str,
        tool_calls: Optional[List[dict]] = None,
        raw: dict = None,
        cached: bool = False,
    ):
        self.text       = text
        self.tool_calls = tool_calls or []
        self.raw        = raw or {}
        self.cached     = cached

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0

    def __repr__(self) -> str:
        return f"<LLMResponse text={self.text[:40]!r} tools={len(self.tool_calls)} cached={self.cached}>"


class LLMClient:
    """
    Client Ollama v2 :
    - function calling avec tool_choice (auto / none / required)
    - streaming token-by-token avec generate_stream()
    - historique de conversation géré
    - cache LRU injecté optionnellement
    """

    SYSTEM_PROMPT = """Tu es JARVIS, un assistant IA personnel sur macOS.
Langue : français. Sois concis et précis.
Utilise les outils disponibles pour les actions système.
Pour les actions destructives ou irréversibles, demande confirmation.
Ne génère jamais de code source non sollicité."""

    def __init__(
        self,
        model: str = "mistral",
        host: str = OLLAMA_HOST,
        temperature: float = 0.1,
        max_tokens: int = 1024,
        timeout: int = 60,
        cache=None,
    ):
        self.model       = model
        self.host        = host.rstrip("/")
        self.temperature = temperature
        self.max_tokens  = max_tokens
        self.timeout     = timeout
        self._cache      = cache          # utils.cache.LRUCache optionnel
        self._history: List[Dict[str, str]] = []

    # ── Disponibilité ─────────────────────────────────────────────────────────

    async def is_available(self) -> bool:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    f"{self.host}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=3),
                ) as r:
                    return r.status == 200
        except Exception:
            return False

    # ── Génération principale ──────────────────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        tools: Optional[List[dict]] = None,
        tool_choice: ToolChoice = "auto",
        use_history: bool = True,
        use_cache: bool = True,
    ) -> LLMResponse:
        """
        Génère une réponse avec support function calling.

        Args:
            prompt:      Message utilisateur
            tools:       Définitions d'outils (format Ollama/OpenAI)
            tool_choice: "auto" | "none" | "required"
            use_history: Inclure l'historique de conversation
            use_cache:   Vérifier le cache avant d'appeler le LLM
        """
        # Cache hit ?
        if use_cache and self._cache:
            cache_key = f"{self.model}:{prompt}"
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.info("Cache HIT: '%s'", prompt[:60])
                return LLMResponse(
                    text=cached.get("text", ""),
                    tool_calls=cached.get("tool_calls", []),
                    cached=True,
                )

        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        if use_history:
            messages.extend(self._history[-10:])
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }

        if tools:
            payload["tools"] = tools
            # Ollama ne supporte pas encore tool_choice nativement,
            # on l'ajoute dans le system prompt si "required"
            if tool_choice == "required" and tools:
                names = [t["function"]["name"] for t in tools if "function" in t]
                payload["messages"][0]["content"] += (
                    f"\nIMPORTANT: tu DOIS utiliser l'un des outils suivants : {', '.join(names)}."
                )

        logger.info(
            "LLM generate: '%s' tools=%d choice=%s",
            prompt[:60], len(tools or []), tool_choice,
        )

        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    f"{self.host}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as r:
                    if r.status != 200:
                        err = await r.text()
                        logger.error("LLM HTTP %d: %s", r.status, err[:200])
                        return LLMResponse(text=f"Erreur LLM ({r.status})")
                    data = await r.json()

        except asyncio.TimeoutError:
            return LLMResponse(text=f"Timeout LLM ({self.timeout}s)")
        except Exception as e:
            logger.error("LLM error: %s", e)
            return LLMResponse(text=f"Erreur: {e}")

        message    = data.get("message", {})
        text       = message.get("content", "")
        raw_calls  = message.get("tool_calls", [])

        tool_calls = [
            {
                "name":      tc.get("function", {}).get("name", ""),
                "arguments": tc.get("function", {}).get("arguments", {}),
            }
            for tc in raw_calls
        ]

        # Mettre à jour l'historique
        self._history.append({"role": "user",      "content": prompt})
        self._history.append({"role": "assistant",  "content": text})

        # Mettre en cache
        if self._cache and use_cache:
            self._cache.set(
                f"{self.model}:{prompt}",
                {"text": text, "tool_calls": tool_calls},
            )

        response = LLMResponse(text=text, tool_calls=tool_calls, raw=data)
        logger.info(
            "LLM response: '%s' tool_calls=%d",
            text[:60], len(tool_calls),
        )
        return response

    # ── Streaming ─────────────────────────────────────────────────────────────

    async def generate_stream(
        self,
        prompt: str,
        tools: Optional[List[dict]] = None,
    ) -> AsyncIterator[str]:
        """
        Génère en streaming et yielde les tokens au fur et à mesure.
        Si tools est fourni, le streaming est désactivé automatiquement
        (Ollama ne supporte pas le streaming + tool_calls simultanément).
        """
        if tools:
            # Fallback non-streaming pour les function calls
            resp = await self.generate(prompt, tools=tools, use_cache=False)
            yield resp.text
            return

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ]
        payload = {
            "model":   self.model,
            "messages": messages,
            "stream":  True,
            "options": {"temperature": self.temperature},
        }

        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    f"{self.host}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as r:
                    async for line in r.content:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                yield token
                            if chunk.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error("LLM stream error: %s", e)

    # ── Utilitaires ───────────────────────────────────────────────────────────

    def clear_history(self) -> None:
        self._history.clear()

    def inject_cache(self, cache) -> None:
        """Injecte un cache LRU après construction (évite la dépendance circulaire)."""
        self._cache = cache
