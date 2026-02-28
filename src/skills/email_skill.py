"""
EmailSkill — Lecture et envoi d'emails via IMAP/SMTP.

Configuration (via .env) :
    IMAP_SERVER   = imap.gmail.com
    IMAP_PORT     = 993
    SMTP_SERVER   = smtp.gmail.com
    SMTP_PORT     = 587
    EMAIL_USER    = votre@gmail.com
    EMAIL_PASSWORD = App Password Gmail (16 caractères)
"""

import asyncio
import email
import imaplib
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict

from .base_skill import ExecutionContext, Skill, SkillResult

logger = logging.getLogger(__name__)


class ReadEmailsSkill(Skill):
    name        = "read_emails"
    description = "Lit les N derniers emails non lus de la boîte de réception"
    examples    = ["lis mes derniers emails", "récupère mes nouveaux messages"]
    risk_level  = "low"

    params_schema = {
        "count": "Nombre d'emails à lire (défaut: 5)",
        "folder": "Dossier IMAP (défaut: INBOX)",
        "unread_only": "Seulement non lus (défaut: true)",
    }

    async def run(self, params: Dict[str, Any], ctx: ExecutionContext) -> SkillResult:
        count       = int(params.get("count", 5))
        folder      = params.get("folder", "INBOX")
        unread_only = str(params.get("unread_only", "true")).lower() != "false"

        imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")
        imap_port   = int(os.getenv("IMAP_PORT", "993"))
        user        = os.getenv("EMAIL_USER", "")
        password    = os.getenv("EMAIL_PASSWORD", "")

        if not user or not password:
            return SkillResult.error(
                "Configuration email manquante. Définissez EMAIL_USER et EMAIL_PASSWORD dans .env"
            )

        try:
            emails = await asyncio.to_thread(
                self._fetch_emails, imap_server, imap_port, user, password,
                folder, count, unread_only
            )
        except Exception as e:
            logger.error("ReadEmails error: %s", e)
            return SkillResult.error(f"Erreur IMAP : {e}")

        if not emails:
            return SkillResult.ok("Aucun email trouvé.", data={"emails": []})

        summary = "\n".join(
            f"[{i+1}] De: {e['from']}\n    Sujet: {e['subject']}\n    {e['snippet']}"
            for i, e in enumerate(emails)
        )
        return SkillResult.ok(
            f"{len(emails)} email(s) trouvé(s) :\n{summary}",
            data={"emails": emails}
        )

    def _fetch_emails(self, server, port, user, password, folder, count, unread_only):
        mail = imaplib.IMAP4_SSL(server, port)
        mail.login(user, password)
        mail.select(folder)

        criterion = "UNSEEN" if unread_only else "ALL"
        _, data = mail.search(None, criterion)

        ids = data[0].split()
        ids = ids[-count:]  # Derniers N

        results = []
        for uid in reversed(ids):
            _, msg_data = mail.fetch(uid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            subject = email.header.decode_header(msg["Subject"] or "")[0]
            if isinstance(subject[0], bytes):
                subject_str = subject[0].decode(subject[1] or "utf-8", errors="replace")
            else:
                subject_str = str(subject[0])

            from_addr = msg.get("From", "")
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

            results.append({
                "from":    from_addr,
                "subject": subject_str,
                "snippet": body[:200].strip(),
                "uid":     uid.decode(),
            })

        mail.logout()
        return results


class SendEmailSkill(Skill):
    name        = "send_email"
    description = "Envoie un email"
    examples    = ["envoie un email à paul@example.com", "réponds à ce mail"]
    risk_level  = "high"
    requires_confirmation = True

    params_schema = {
        "to":      "Adresse email du destinataire (obligatoire)",
        "subject": "Sujet de l'email",
        "body":    "Corps du message",
    }

    async def run(self, params: Dict[str, Any], ctx: ExecutionContext) -> SkillResult:
        to      = params.get("to", "").strip()
        subject = params.get("subject", "(Sans objet)")
        body    = params.get("body", "")

        if not to:
            return SkillResult.error("Paramètre 'to' (destinataire) obligatoire")

        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port   = int(os.getenv("SMTP_PORT", "587"))
        user        = os.getenv("EMAIL_USER", "")
        password    = os.getenv("EMAIL_PASSWORD", "")

        if not user or not password:
            return SkillResult.error(
                "Configuration email manquante. Définissez EMAIL_USER et EMAIL_PASSWORD dans .env"
            )

        try:
            await asyncio.to_thread(
                self._send, smtp_server, smtp_port, user, password, to, subject, body
            )
        except Exception as e:
            logger.error("SendEmail error: %s", e)
            return SkillResult.error(f"Erreur SMTP : {e}")

        return SkillResult.ok(f"Email envoyé à {to} : « {subject} »")

    def _send(self, server, port, user, password, to, subject, body):
        msg = MIMEMultipart()
        msg["From"]    = user
        msg["To"]      = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(server, port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(user, password)
            smtp.sendmail(user, to, msg.as_string())
