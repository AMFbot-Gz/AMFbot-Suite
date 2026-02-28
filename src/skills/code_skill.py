"""
CodeSkill — Manipulation de fichiers et exécution de code.

Skills :
    open_in_editor  → ouvre un fichier dans VSCode / éditeur configuré
    run_code        → exécute un script Python ou un fichier
    read_file       → lit le contenu d'un fichier texte
    write_file      → crée/écrase un fichier texte
"""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from .base_skill import ExecutionContext, Skill, SkillResult

logger = logging.getLogger(__name__)


class OpenInEditorSkill(Skill):
    name        = "open_in_editor"
    description = "Ouvre un fichier ou dossier dans VSCode (ou l'éditeur configuré)"
    examples    = [
        "ouvre le fichier main.py dans VSCode",
        "édite ~/project/config.json",
    ]
    risk_level  = "low"

    params_schema = {
        "path":   "Chemin du fichier ou dossier à ouvrir (obligatoire)",
        "editor": "Éditeur à utiliser : code, nano, vim (défaut: code)",
    }

    async def run(self, params: Dict[str, Any], ctx: ExecutionContext) -> SkillResult:
        path_str = params.get("path", "").strip()
        editor   = params.get("editor", os.getenv("DEFAULT_EDITOR", "code"))

        if not path_str:
            return SkillResult.error("Paramètre 'path' obligatoire")

        path = Path(path_str).expanduser().resolve()

        try:
            proc = await asyncio.create_subprocess_exec(
                editor, str(path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            if proc.returncode and proc.returncode != 0 and stderr:
                return SkillResult.error(
                    f"Erreur ouverture : {stderr.decode('utf-8', errors='replace')[:200]}"
                )
            return SkillResult.ok(f"Ouvert dans {editor} : {path}")
        except FileNotFoundError:
            return SkillResult.error(
                f"Éditeur '{editor}' introuvable. Installez VSCode ou changez DEFAULT_EDITOR."
            )
        except asyncio.TimeoutError:
            return SkillResult.ok(f"Ouvert dans {editor} : {path}")
        except Exception as e:
            return SkillResult.error(f"Erreur : {e}")


class RunCodeSkill(Skill):
    name        = "run_code"
    description = "Exécute un fichier Python ou une commande shell simple"
    examples    = [
        "exécute le script test.py",
        "lance python ~/scripts/backup.py",
    ]
    risk_level  = "high"
    requires_confirmation = True

    params_schema = {
        "path":      "Chemin du fichier à exécuter",
        "command":   "Commande shell directe (alternative à path)",
        "timeout":   "Timeout en secondes (défaut: 30)",
        "cwd":       "Répertoire de travail",
    }

    # Commandes shell autorisées (liste positive)
    ALLOWED_COMMANDS = frozenset([
        "python", "python3", "node", "npm", "npx",
        "bash", "sh", "make", "pytest", "ruff", "mypy",
    ])

    async def run(self, params: Dict[str, Any], ctx: ExecutionContext) -> SkillResult:
        path_str    = params.get("path", "").strip()
        command_str = params.get("command", "").strip()
        timeout     = float(params.get("timeout", 30))
        cwd         = params.get("cwd")

        if not path_str and not command_str:
            return SkillResult.error("Paramètre 'path' ou 'command' obligatoire")

        if path_str:
            path = Path(path_str).expanduser().resolve()
            if not path.exists():
                return SkillResult.error(f"Fichier introuvable : {path}")
            cmd = [sys.executable, str(path)]
        else:
            parts = command_str.split()
            if parts[0] not in self.ALLOWED_COMMANDS:
                return SkillResult.error(
                    f"Commande non autorisée : '{parts[0]}'. "
                    f"Autorisées : {', '.join(sorted(self.ALLOWED_COMMANDS))}"
                )
            cmd = parts

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(Path(cwd).expanduser()) if cwd else None,
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                return SkillResult.error(f"Timeout ({timeout}s) — processus tué")

            output = stdout.decode("utf-8", errors="replace").strip()
            rc = proc.returncode

            if rc == 0:
                preview = output[:500] if output else "(pas de sortie)"
                return SkillResult.ok(
                    f"Exécution réussie (code 0) :\n{preview}",
                    data={"output": output, "returncode": rc}
                )
            else:
                preview = output[:500] if output else "(aucune erreur capturée)"
                return SkillResult.error(
                    f"Échec (code {rc}) :\n{preview}"
                )
        except Exception as e:
            logger.error("RunCode error: %s", e)
            return SkillResult.error(f"Erreur : {e}")


class ReadFileSkill(Skill):
    name        = "read_file"
    description = "Lit le contenu d'un fichier texte"
    examples    = ["lis le fichier config.json", "affiche le contenu de notes.txt"]
    risk_level  = "low"

    params_schema = {
        "path":  "Chemin du fichier à lire (obligatoire)",
        "lines": "Nombre de lignes à lire (défaut: toutes)",
    }

    async def run(self, params: Dict[str, Any], ctx: ExecutionContext) -> SkillResult:
        path_str = params.get("path", "").strip()
        lines    = params.get("lines")

        if not path_str:
            return SkillResult.error("Paramètre 'path' obligatoire")

        path = Path(path_str).expanduser().resolve()
        if not path.exists():
            return SkillResult.error(f"Fichier introuvable : {path}")
        if not path.is_file():
            return SkillResult.error(f"'{path}' n'est pas un fichier")

        try:
            content = await asyncio.to_thread(path.read_text, encoding="utf-8", errors="replace")
        except Exception as e:
            return SkillResult.error(f"Erreur lecture : {e}")

        if lines:
            content_lines = content.splitlines()[:int(lines)]
            content = "\n".join(content_lines)

        preview = content[:1000]
        truncated = len(content) > 1000
        msg = f"Contenu de {path.name} ({len(content)} car.):\n{preview}"
        if truncated:
            msg += "\n[... tronqué]"

        return SkillResult.ok(msg, data={"content": content, "path": str(path)})


class WriteFileSkill(Skill):
    name        = "write_file"
    description = "Crée ou écrase un fichier texte avec le contenu fourni"
    examples    = [
        "crée un fichier notes.txt avec ce contenu",
        "écris 'Hello World' dans test.txt",
    ]
    risk_level  = "high"
    requires_confirmation = True

    params_schema = {
        "path":    "Chemin du fichier à écrire (obligatoire)",
        "content": "Contenu à écrire (obligatoire)",
        "append":  "Ajouter à la fin plutôt qu'écraser (défaut: false)",
    }

    async def run(self, params: Dict[str, Any], ctx: ExecutionContext) -> SkillResult:
        path_str = params.get("path", "").strip()
        content  = params.get("content", "")
        append   = str(params.get("append", "false")).lower() == "true"

        if not path_str:
            return SkillResult.error("Paramètre 'path' obligatoire")

        path = Path(path_str).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)

        mode = "a" if append else "w"
        action = "Ajouté à" if append else "Écrit dans"

        try:
            await asyncio.to_thread(
                lambda: path.open(mode, encoding="utf-8").write(content) or path.open(mode, encoding="utf-8").close()
            )
            # Simpler approach:
            def _write():
                with path.open(mode, encoding="utf-8") as f:
                    f.write(content)

            await asyncio.to_thread(_write)
        except Exception as e:
            return SkillResult.error(f"Erreur écriture : {e}")

        return SkillResult.ok(
            f"{action} {path.name} ({len(content)} caractères)",
            data={"path": str(path), "size": len(content)}
        )
