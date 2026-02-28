"""
SkillRegistry v2 — Registre avec hot-reload via watchdog.

Nouveauté : surveille src/skills/ en temps réel.
Quand un fichier .py est modifié, recharge automatiquement les skills
avec importlib.reload() sans redémarrer JARVIS.
"""

import importlib
import importlib.util
import inspect
import logging
import sys
import threading
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional

from .base_skill import Skill

logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    Registre des skills avec hot-reload optionnel.

    Utilisation :
        registry = SkillRegistry()
        registry.register(OpenAppSkill())
        registry.start_hot_reload(Path("src/skills"))   # optionnel
        skill = registry.get("open_app")
    """

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._lock = threading.Lock()
        self._observer = None
        self._on_reload_callbacks: List[Callable] = []

    # ── Enregistrement ────────────────────────────────────────────────────────

    # Timeout pour les skills tiers (secondes)
    THIRD_PARTY_TIMEOUT = 10.0

    def register(self, skill: Skill) -> None:
        with self._lock:
            if skill.name in self._skills:
                logger.debug("Skill '%s' mis à jour dans le registry", skill.name)
            else:
                tp = " [tiers]" if getattr(skill, "is_third_party", False) else ""
                logger.info("Skill enregistré: %s [%s]%s", skill.name, skill.risk_level, tp)
            self._skills[skill.name] = skill

    def unregister(self, name: str) -> bool:
        with self._lock:
            if name in self._skills:
                del self._skills[name]
                logger.info("Skill désenregistré: %s", name)
                return True
            return False

    # ── Accès ─────────────────────────────────────────────────────────────────

    def get(self, name: str) -> Optional[Skill]:
        with self._lock:
            return self._skills.get(name)

    def all(self) -> List[Skill]:
        with self._lock:
            return list(self._skills.values())

    def by_risk(self, risk_level: str) -> List[Skill]:
        with self._lock:
            return [s for s in self._skills.values() if s.risk_level == risk_level]

    def on_reload(self, callback: Callable) -> None:
        """Callback appelé après chaque rechargement de skill."""
        self._on_reload_callbacks.append(callback)

    def __len__(self) -> int:
        return len(self._skills)

    def __iter__(self) -> Iterator[Skill]:
        with self._lock:
            return iter(list(self._skills.values()))

    def list_names(self) -> List[str]:
        with self._lock:
            return list(self._skills.keys())

    async def run_skill(
        self,
        name: str,
        params: dict,
        ctx,
        timeout: Optional[float] = None,
    ):
        """
        Exécute un skill avec sandboxing automatique pour les skills tiers.

        Les skills marqués is_third_party=True sont soumis à un timeout strict
        de THIRD_PARTY_TIMEOUT secondes (ou la valeur fournie).
        """
        import asyncio
        from .base_skill import SkillResult

        skill = self.get(name)
        if skill is None:
            return SkillResult.error(f"Skill inconnu : {name}")

        is_third_party = getattr(skill, "is_third_party", False)
        effective_timeout = timeout or (self.THIRD_PARTY_TIMEOUT if is_third_party else None)

        if effective_timeout:
            try:
                return await asyncio.wait_for(
                    skill.run(params, ctx),
                    timeout=effective_timeout,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Skill tiers '%s' timeout après %.1fs", name, effective_timeout
                )
                return SkillResult.error(
                    f"Timeout ({effective_timeout}s) — skill tiers '{name}' annulé"
                )
        else:
            return await skill.run(params, ctx)

    def summary(self) -> str:
        with self._lock:
            lines = [f"SkillRegistry ({len(self._skills)} skills):"]
            for skill in sorted(self._skills.values(), key=lambda s: s.risk_level):
                lines.append(f"  [{skill.risk_level:8}] {skill.name}: {skill.description}")
            return "\n".join(lines)

    # ── Hot-reload ────────────────────────────────────────────────────────────

    def start_hot_reload(self, skills_dir: Path) -> bool:
        """
        Lance watchdog pour surveiller skills_dir.
        Recharge automatiquement les skills à chaque modification .py.
        Retourne False si watchdog n'est pas installé.
        """
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            registry_ref = self

            class SkillFileHandler(FileSystemEventHandler):
                def on_modified(self, event):
                    if not event.is_directory and event.src_path.endswith(".py"):
                        path = Path(event.src_path)
                        logger.info("Hot-reload: %s modifié", path.name)
                        registry_ref._reload_file(path)

                def on_created(self, event):
                    if not event.is_directory and event.src_path.endswith(".py"):
                        path = Path(event.src_path)
                        logger.info("Hot-reload: nouveau fichier %s", path.name)
                        registry_ref._reload_file(path)

            self._observer = Observer()
            self._observer.schedule(SkillFileHandler(), str(skills_dir), recursive=True)
            self._observer.daemon = True
            self._observer.start()
            logger.info("Hot-reload actif sur: %s", skills_dir)
            return True

        except ImportError:
            logger.warning("watchdog non installé — hot-reload désactivé")
            return False
        except Exception as e:
            logger.error("Erreur démarrage hot-reload: %s", e)
            return False

    def stop_hot_reload(self) -> None:
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join(timeout=2)
            logger.info("Hot-reload arrêté")

    def _reload_file(self, path: Path) -> None:
        """Recharge dynamiquement tous les skills d'un fichier .py modifié."""
        try:
            # Convertir le path en module name relatif à src/
            # Ex: src/skills/clipboard_skill.py → skills.clipboard_skill
            module_name = self._path_to_module(path)
            if not module_name:
                return

            if module_name in sys.modules:
                module = importlib.reload(sys.modules[module_name])
            else:
                spec = importlib.util.spec_from_file_location(module_name, path)
                if not spec:
                    return
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

            # Trouver et réenregistrer les classes Skill dans le module
            reloaded = []
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, Skill)
                    and obj is not Skill
                    and hasattr(obj, "name")
                    and obj.name
                ):
                    instance = obj()
                    self.register(instance)
                    reloaded.append(obj.name)

            if reloaded:
                logger.info("Skills rechargés: %s", reloaded)
                for cb in self._on_reload_callbacks:
                    try:
                        cb(reloaded)
                    except Exception:
                        pass

        except Exception as e:
            logger.error("Erreur hot-reload %s: %s", path.name, e)

    def _path_to_module(self, path: Path) -> Optional[str]:
        """Convertit un chemin de fichier en nom de module Python."""
        try:
            # Chercher 'src' dans le chemin
            parts = path.parts
            if "src" in parts:
                idx   = list(parts).index("src")
                rel   = parts[idx + 1:]
                module = ".".join(rel).replace(".py", "")
                return module
        except Exception:
            pass
        return None
