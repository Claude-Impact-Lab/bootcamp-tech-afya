"""
Fábrica de `CFMClient` para injeção via `Depends` do FastAPI.

Controlada por `CFM_CLIENT` no ambiente/.env:
- "fake" (padrão): `FakeCFMClient`, sem rede — usar até o contrato oficial
  do CFM estar disponível, e sempre nos testes automatizados.
- "http": `CFMHttpClient`, o adapter real (ainda pendente da especificação
  oficial do CFM — ver app/cfm/http_client.py).
"""

import os

from app.cfm.client import CFMClient
from app.cfm.fake_client import FakeCFMClient
from app.cfm.http_client import CFMHttpClient


def get_cfm_client() -> CFMClient:
    """Resolve qual implementação de `CFMClient` usar, a partir do ambiente."""
    modo = os.getenv("CFM_CLIENT", "fake").strip().lower()
    if modo == "http":
        return CFMHttpClient(
            base_url=os.getenv("CFM_BASE_URL"),
            chave_acesso=os.getenv("CFM_CHAVE_ACESSO"),
        )
    return FakeCFMClient()
