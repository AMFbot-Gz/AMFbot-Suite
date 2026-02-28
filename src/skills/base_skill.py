"""
Skill — Interface de base pour toutes les compétences de JARVIS.

Chaque skill est un module autonome qui :
  - Déclare ses métadonnées (nom, description, risque)
  - Implémente run() (exécution réelle)
  - Peut implémenter simulate() (dry-run pour preview)
  - Peut implémenter undo() (rollback si possible)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

RiskLevel = Literal["low", "medium", "high", "critical"]


# ── Contexte d'exécution ──────────────────────────────────────────────────────

@dataclass
class ExecutionContext:
    """Contexte injecté dans chaque skill lors de l'exécution."""
    user_id: Optional[str]  = None
    session_id: str         = ""
    dry_run: bool           = False
    confirmed: bool         = False
    metadata: Dict[str, Any] = field(default_factory=dict)


# ── Résultat d'exécution ──────────────────────────────────────────────────────

@dataclass
class SkillResult:
    """Résultat retourné par skill.run()."""
    success: bool
    message: str
    data: Dict[str, Any]     = field(default_factory=dict)
    undo_token: Optional[str] = None  # Token pour le rollback éventuel

    @classmethod
    def ok(cls, message: str, **data) -> "SkillResult":
        return cls(success=True, message=message, data=data)

    @classmethod
    def error(cls, message: str, **data) -> "SkillResult":
        return cls(success=False, message=message, data=data)


# ── Interface Skill ───────────────────────────────────────────────────────────

class Skill(ABC):
    """
    Classe de base abstraite pour tous les skills JARVIS.

    Exemple minimal :
        class GreetSkill(Skill):
            name = "greet"
            description = "Dit bonjour"
            examples = ["dis bonjour", "salut"]
            params_schema = {"type": "object", "properties": {}, "required": []}
            risk_level = "low"
            requires_confirmation = False

            async def run(self, params: dict, ctx: ExecutionContext) -> SkillResult:
                return SkillResult.ok("Bonjour !")
    """

    # ── Métadonnées (à définir dans chaque sous-classe) ───────────────────────

    name: str                     # Identifiant unique (snake_case)
    description: str              # Description courte pour le LLM
    examples: List[str]           # Phrases exemples pour le LLM
    params_schema: dict           # JSON Schema des paramètres
    risk_level: RiskLevel         # Niveau de risque
    requires_confirmation: bool   # Forcer confirmation même si risk=medium
    is_third_party: bool = False  # True = skill externe → sandboxé (timeout strict)

    # ── Interface obligatoire ─────────────────────────────────────────────────

    @abstractmethod
    async def run(self, params: dict, ctx: ExecutionContext) -> SkillResult:
        """Exécute le skill. Doit être idempotent si possible."""
        ...

    # ── Interface optionnelle ─────────────────────────────────────────────────

    async def simulate(self, params: dict) -> SkillResult:
        """
        Dry-run : décrit ce qui serait fait sans l'exécuter.
        Implémentation par défaut : retourne un message générique.
        """
        return SkillResult.ok(
            f"[SIMULATION] {self.name} serait exécuté avec {params}"
        )

    async def undo(self, params: dict, ctx: ExecutionContext) -> bool:
        """
        Rollback de la dernière exécution si possible.
        Retourne True si le rollback a réussi, False sinon.
        Implémentation par défaut : non supporté.
        """
        return False

    def validate_params(self, params: dict) -> List[str]:
        """
        Valide les paramètres contre params_schema.
        Retourne une liste d'erreurs (vide = OK).
        """
        errors = []
        required = self.params_schema.get("required", [])
        properties = self.params_schema.get("properties", {})

        for req_field in required:
            if req_field not in params:
                errors.append(f"Paramètre requis manquant: '{req_field}'")

        for param_name, param_value in params.items():
            if param_name in properties:
                expected_type = properties[param_name].get("type")
                if expected_type == "string" and not isinstance(param_value, str):
                    errors.append(f"'{param_name}' doit être une string")
                elif expected_type == "integer" and not isinstance(param_value, int):
                    errors.append(f"'{param_name}' doit être un entier")

        return errors

    def __repr__(self) -> str:
        return f"<Skill:{self.name} risk={self.risk_level}>"
