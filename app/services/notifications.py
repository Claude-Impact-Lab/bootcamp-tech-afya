"""Notificações substituíveis por console ou SMTP."""

import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol


logger = logging.getLogger(__name__)


class NotificationPublisher(Protocol):
    def account_status_changed(self, user_id: int, email: str, new_status: str) -> None:
        """Publica uma mudança de status em um canal configurado."""

    def password_reset_requested(self, email: str, reset_url: str) -> None:
        """Entrega o endereço temporário para redefinição da senha."""


class NullNotificationPublisher:
    """Implementação local intencionalmente silenciosa."""

    def account_status_changed(self, user_id: int, email: str, new_status: str) -> None:
        return None

    def password_reset_requested(self, email: str, reset_url: str) -> None:
        return None


class ConsoleNotificationPublisher:
    """Mostra notificações no terminal durante desenvolvimento e aulas."""

    def account_status_changed(self, user_id: int, email: str, new_status: str) -> None:
        logger.warning(
            "Notificação de cadastro: user_id=%s email=%s status=%s",
            user_id,
            email,
            new_status,
        )

    def password_reset_requested(self, email: str, reset_url: str) -> None:
        logger.warning("Recuperação de senha para %s: %s", email, reset_url)


class SMTPNotificationPublisher:
    """Envia mensagens usando qualquer servidor SMTP configurado por ambiente."""

    def __init__(
        self,
        host: str,
        port: int,
        sender: str,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.sender = sender
        self.username = username
        self.password = password
        self.use_tls = use_tls

    def _send(self, recipient: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
                if self.use_tls:
                    smtp.starttls()
                if self.username:
                    smtp.login(self.username, self.password or "")
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException):
            logger.exception("Não foi possível enviar a notificação para %s", recipient)

    def account_status_changed(self, user_id: int, email: str, new_status: str) -> None:
        labels = {
            "active": "aprovado e ativo",
            "approved_incomplete": "aprovado; falta completar o perfil",
            "rejected": "rejeitado",
        }
        status = labels.get(new_status, new_status)
        self._send(
            email,
            "Atualização do seu cadastro",
            f"O status do seu cadastro foi atualizado para: {status}.\n\nAcesse o portal para consultar os detalhes.",
        )

    def password_reset_requested(self, email: str, reset_url: str) -> None:
        self._send(
            email,
            "Recuperação de senha",
            f"Use o endereço abaixo para criar uma nova senha. O link expira em uma hora.\n\n{reset_url}",
        )
