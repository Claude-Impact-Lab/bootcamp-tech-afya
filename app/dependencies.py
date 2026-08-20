"""Dependências substituíveis usadas pelas rotas FastAPI."""

import os

from fastapi import Depends

from app.integrations.cfm_browser import CFMBrowserService
from app.integrations.cfm_soap import CFMSoapService
from app.services.cfm import CFMService
from app.services.doctor_verification import DoctorVerificationService
from app.services.notifications import (
    ConsoleNotificationPublisher,
    NotificationPublisher,
    SMTPNotificationPublisher,
)


def get_cfm_service() -> CFMService:
    if os.getenv("CFM_VALIDATION_METHOD", "browser").lower() == "browser":
        return CFMBrowserService(
            timeout_seconds=os.getenv("CFM_BROWSER_TIMEOUT_SECONDS", "120"),
            headless=os.getenv("CFM_BROWSER_HEADLESS", "false").lower() == "true",
            channel=os.getenv("CFM_BROWSER_CHANNEL", "chrome"),
        )
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
    """Usa SMTP quando configurado e o terminal no ambiente local."""

    host = os.getenv("SMTP_HOST", "").strip()
    if not host:
        return ConsoleNotificationPublisher()
    return SMTPNotificationPublisher(
        host=host,
        port=int(os.getenv("SMTP_PORT", "587")),
        sender=os.getenv("SMTP_FROM", "portal@localhost"),
        username=os.getenv("SMTP_USERNAME") or None,
        password=os.getenv("SMTP_PASSWORD") or None,
        use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
    )
