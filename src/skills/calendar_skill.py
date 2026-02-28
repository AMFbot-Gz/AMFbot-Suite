"""
CalendarSkill — Gestion d'événements via fichier .ics local.

Implémente lecture et ajout sans dépendance à iCloud/Google Calendar.
Format ICS standard (RFC 5545) — compatible avec Calendar.app macOS.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from .base_skill import ExecutionContext, Skill, SkillResult

logger = logging.getLogger(__name__)

CALENDAR_FILE = Path.home() / "jarvis_antigravity" / "config" / "jarvis_calendar.ics"


def _ensure_calendar(path: Path) -> None:
    """Crée le fichier ICS s'il n'existe pas."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "PRODID:-//JARVIS//JARVIS Antigravity//FR\r\n"
            "CALSCALE:GREGORIAN\r\n"
            "END:VCALENDAR\r\n",
            encoding="utf-8",
        )


def _format_dt(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")


class AddEventSkill(Skill):
    """Ajoute un événement dans le calendrier ICS local."""

    name        = "add_calendar_event"
    description = "Ajoute un événement dans le calendrier local (fichier .ics)"
    examples    = [
        "ajoute une réunion demain à 14h",
        "planifie un rdv le 15 mars à 10h",
        "rappelle-moi de faire X dans 2 heures",
    ]
    params_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Titre de l'événement",
            },
            "start_iso": {
                "type": "string",
                "description": "Date/heure de début ISO 8601 (ex: 2026-03-15T14:00:00)",
            },
            "duration_minutes": {
                "type": "integer",
                "description": "Durée en minutes (défaut: 60)",
            },
            "description": {
                "type": "string",
                "description": "Description optionnelle de l'événement",
            },
        },
        "required": ["title", "start_iso"],
    }
    risk_level            = "medium"
    requires_confirmation = False

    async def run(self, params: dict, ctx: ExecutionContext) -> SkillResult:
        errors = self.validate_params(params)
        if errors:
            return SkillResult.error(f"Paramètres invalides : {', '.join(errors)}")
        if ctx.dry_run:
            return await self.simulate(params)

        title    = params["title"]
        start_iso = params["start_iso"]
        duration  = params.get("duration_minutes", 60)
        desc      = params.get("description", "")

        try:
            start = datetime.fromisoformat(start_iso)
        except ValueError:
            return SkillResult.error(f"Format de date invalide : {start_iso}")

        end = start + timedelta(minutes=duration)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._add_event, title, start, end, desc)

        return SkillResult.ok(
            f"Événement ajouté : {title} le {start.strftime('%d/%m/%Y à %Hh%M')}",
            title=title, start=start_iso,
        )

    def _add_event(self, title: str, start: datetime, end: datetime, desc: str) -> None:
        _ensure_calendar(CALENDAR_FILE)
        content = CALENDAR_FILE.read_text(encoding="utf-8")

        vevent = (
            "BEGIN:VEVENT\r\n"
            f"UID:{uuid.uuid4()}@jarvis\r\n"
            f"DTSTAMP:{_format_dt(datetime.now())}\r\n"
            f"DTSTART:{_format_dt(start)}\r\n"
            f"DTEND:{_format_dt(end)}\r\n"
            f"SUMMARY:{title}\r\n"
        )
        if desc:
            vevent += f"DESCRIPTION:{desc}\r\n"
        vevent += "END:VEVENT\r\n"

        # Insérer avant END:VCALENDAR
        content = content.replace("END:VCALENDAR\r\n", vevent + "END:VCALENDAR\r\n")
        CALENDAR_FILE.write_text(content, encoding="utf-8")
        logger.info("Événement ICS ajouté : %s", title)

    async def simulate(self, params: dict) -> SkillResult:
        return SkillResult.ok(
            f"[SIMULATION] Ajouterait l'événement : {params.get('title')} "
            f"le {params.get('start_iso', '?')}"
        )


class ListEventsSkill(Skill):
    """Liste les prochains événements du calendrier ICS local."""

    name        = "list_calendar_events"
    description = "Liste les prochains événements du calendrier local"
    examples    = [
        "qu'est-ce que j'ai prévu cette semaine",
        "mes prochains rendez-vous",
        "agenda du jour",
    ]
    params_schema = {
        "type": "object",
        "properties": {
            "days_ahead": {
                "type": "integer",
                "description": "Nombre de jours à afficher (défaut: 7)",
            }
        },
        "required": [],
    }
    risk_level            = "low"
    requires_confirmation = False

    async def run(self, params: dict, ctx: ExecutionContext) -> SkillResult:
        days_ahead = params.get("days_ahead", 7)
        loop = asyncio.get_event_loop()
        events = await loop.run_in_executor(None, self._read_events, days_ahead)

        if not events:
            return SkillResult.ok(f"Aucun événement dans les {days_ahead} prochains jours.")

        lines = [f"• {e['start']} — {e['title']}" for e in events]
        return SkillResult.ok(
            f"{len(events)} événement(s) :\n" + "\n".join(lines),
            events=events,
        )

    def _read_events(self, days_ahead: int) -> List[dict]:
        if not CALENDAR_FILE.exists():
            return []

        content = CALENDAR_FILE.read_text(encoding="utf-8")
        events  = []
        now     = datetime.now()
        cutoff  = now + timedelta(days=days_ahead)

        # Parse simple sans icalendar lib
        current = {}
        for line in content.splitlines():
            line = line.strip()
            if line == "BEGIN:VEVENT":
                current = {}
            elif line == "END:VEVENT":
                if current.get("start") and current.get("title"):
                    try:
                        dt = datetime.strptime(current["start"], "%Y%m%dT%H%M%S")
                        if now <= dt <= cutoff:
                            events.append({
                                "title": current["title"],
                                "start": dt.strftime("%d/%m %Hh%M"),
                            })
                    except ValueError:
                        pass
            elif line.startswith("SUMMARY:"):
                current["title"] = line[8:]
            elif line.startswith("DTSTART:"):
                current["start"] = line[8:]

        events.sort(key=lambda e: e["start"])
        return events
