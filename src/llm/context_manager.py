"""
ContextManager — Résolution de coréférences et enrichissement du contexte.

Résout les pronoms et références implicites dans la requête courante
en s'appuyant sur le dernier tour de conversation.

Exemples :
    Tour précédent: "ouvre Chrome"
    Requête courante: "ferme-le" → "ferme Chrome"

    Tour précédent: "cherche la météo à Paris"
    Requête courante: "et pour demain ?" → "météo à Paris pour demain"
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# Pronoms/expressions qui signalent une référence au tour précédent
REFERENCE_PATTERNS = [
    # Pronoms directs
    r"\ble\b", r"\bla\b", r"\bles\b", r"\blui\b", r"\bleur\b",
    r"\by\b", r"\ben\b",
    # Expressions déictiques
    r"\bça\b", r"\bcela\b", r"\bceci\b", r"\bc'est\b",
    r"\bde ça\b", r"\bde cela\b",
    # Références temporelles relatives
    r"\bmaintenant\b", r"\baprès ça\b", r"\bensuite\b",
    # Ellipses (phrases commençant par une conjonction)
    r"^et ", r"^mais ", r"^aussi ", r"^alors ",
    # Anaphores courtes (phrases très courtes sans sujet explicite)
]

# Mots de sujets explicites (si présents, pas besoin de résolution)
EXPLICIT_SUBJECTS = [
    "chrome", "firefox", "safari", "slack", "spotify", "vscode", "terminal",
    "finder", "mail", "calendrier", "notes",
    "google", "youtube", "github", "claude",
]


class ContextManager:
    """
    Résolution de coréférences et enrichissement de la requête courante.

    Utilisation :
        ctx_mgr = ContextManager()
        resolved = ctx_mgr.resolve(
            current_query="ferme-le",
            last_turn="ouvre Chrome"
        )
        # → "ferme Chrome"
    """

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: optionnel — utilisé pour une résolution avancée via LLM.
                        Sans LLM, utilise des heuristiques légères.
        """
        self._llm = llm_client

    def resolve(
        self,
        current_query: str,
        last_user_turn: Optional[str] = None,
        last_jarvis_turn: Optional[str] = None,
    ) -> str:
        """
        Résout les références dans la requête courante.

        Retourne la requête enrichie (ou inchangée si aucune référence détectée).
        """
        if not current_query.strip():
            return current_query

        # Aucun contexte disponible → pas de résolution possible
        if not last_user_turn and not last_jarvis_turn:
            return current_query

        query_lower = current_query.lower().strip()

        # Détecter si la résolution est nécessaire
        if not self._needs_resolution(query_lower):
            return current_query

        # Heuristique : extraction du sujet du dernier tour
        subject = self._extract_subject(last_user_turn or "")
        if not subject:
            subject = self._extract_subject(last_jarvis_turn or "")

        if not subject:
            logger.debug("ContextManager: référence détectée mais sujet introuvable")
            return current_query

        resolved = self._inject_subject(current_query, subject)
        if resolved != current_query:
            logger.info("ContextManager: '%s' → '%s' (sujet: %s)",
                        current_query[:60], resolved[:60], subject)
        return resolved

    # ── Heuristiques ──────────────────────────────────────────────────────────

    def _needs_resolution(self, query_lower: str) -> bool:
        """Détecte si la requête contient une référence implicite."""
        # Requête très courte (< 4 mots) sans sujet explicite
        words = query_lower.split()
        if len(words) <= 4:
            has_explicit = any(s in query_lower for s in EXPLICIT_SUBJECTS)
            if not has_explicit:
                return True

        # Présence d'un pattern de référence
        for pattern in REFERENCE_PATTERNS:
            if re.search(pattern, query_lower):
                return True

        return False

    def _extract_subject(self, text: str) -> str:
        """
        Extrait le sujet principal d'un texte.
        Stratégie : chercher d'abord les apps connues, puis le premier nom.
        """
        text_lower = text.lower()

        # Apps et entités connues (priorité)
        for subject in EXPLICIT_SUBJECTS:
            if subject in text_lower:
                # Retourner avec la casse d'origine
                idx = text_lower.index(subject)
                return text[idx: idx + len(subject)]

        # Heuristique : premier mot après un verbe d'action
        action_verbs = ["ouvre", "ferme", "lance", "arrête", "affiche",
                        "cherche", "trouve", "envoie", "lis", "écris"]
        for verb in action_verbs:
            m = re.search(rf"\b{verb}\b\s+(\w+)", text_lower)
            if m:
                word = m.group(1)
                if len(word) > 2:  # Ignorer les mots très courts
                    # Récupérer la casse originale
                    idx = text_lower.index(word)
                    return text[idx: idx + len(word)]

        return ""

    def _inject_subject(self, query: str, subject: str) -> str:
        """
        Injecte le sujet dans la requête en remplaçant les pronoms.
        """
        # Remplacement des pronoms les plus courants
        substitutions = [
            (r"\b(le|la|les|lui|leur)\b", subject),
            (r"\b(ça|cela|ceci)\b",       subject),
            (r"^(et|mais|aussi|alors)\s+", f"{subject}: "),
        ]

        result = query
        for pattern, replacement in substitutions:
            new_result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
            if new_result != result:
                result = new_result
                break  # Une seule substitution à la fois

        # Si la requête est très courte et n'a pas changé, ajouter le contexte
        if result == query and len(query.split()) <= 3:
            result = f"{query} {subject}"

        return result

    # ── Résolution avancée via LLM (optionnel) ────────────────────────────────

    async def resolve_with_llm(
        self,
        current_query: str,
        last_user_turn: Optional[str] = None,
        last_jarvis_turn: Optional[str] = None,
    ) -> str:
        """
        Version LLM de la résolution — plus précise mais plus lente.
        Appelée uniquement si self._llm est configuré.
        """
        if not self._llm:
            return self.resolve(current_query, last_user_turn, last_jarvis_turn)

        if not self._needs_resolution(current_query.lower()):
            return current_query

        prompt = f"""Reformule la requête courante de façon autonome (sans pronoms ni références implicites), en utilisant le contexte des tours précédents.

Tour utilisateur précédent : {last_user_turn or '(aucun)'}
Réponse JARVIS précédente : {last_jarvis_turn or '(aucune)'}
Requête courante : {current_query}

Requête reformulée (une seule ligne, sans explication) :"""

        try:
            response = await self._llm.generate(prompt)
            if response and response.text.strip():
                resolved = response.text.strip().splitlines()[0]
                logger.info("ContextManager LLM: '%s' → '%s'",
                            current_query[:60], resolved[:60])
                return resolved
        except Exception as e:
            logger.warning("ContextManager LLM error: %s", e)

        return self.resolve(current_query, last_user_turn, last_jarvis_turn)
