"""Ponto de extensão para notificações futuras, sem enviar mensagens nesta versão."""

from typing import Protocol


class NotificationPublisher(Protocol):
    def account_status_changed(self, user_id: int, email: str, new_status: str) -> None:
        """Publica uma mudança de status em um canal configurado."""


class NullNotificationPublisher:
    """Implementação local intencionalmente silenciosa."""

    def account_status_changed(self, user_id: int, email: str, new_status: str) -> None:
        return None
