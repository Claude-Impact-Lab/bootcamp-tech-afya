"""Dependências substituíveis usadas pelas rotas FastAPI."""

import os

from fastapi import Depends

from app.integrations.cfm_soap import CFMSoapService
from app.services.cfm import CFMService
from app.services.doctor_verification import DoctorVerificationService
from app.services.notifications import NotificationPublisher, NullNotificationPublisher


def get_cfm_service() -> CFMService:
    return CFMSoapService(
        access_key=os.getenv("CFM_ACCESS_KEY"),
        url=os.getenv("CFM_WS_URL"),
        timeout_seconds=os.getenv("CFM_TIMEOUT_SECONDS", "10"),
    )


def get_doctor_verification_service(
    cfm_service: CFMService = Depends(get_cfm_service),
) -> DoctorVerificationService:
    return DoctorVerificationService(cfm_service)


def get_notification_publisher() -> NotificationPublisher:
    """Pode ser trocado futuramente por e-mail, notificação interna ou outro canal."""

    return NullNotificationPublisher()
