"""
Integração com o CFM (Missão 07) — Port & Adapter.

O domínio depende apenas do contrato `CFMClient` (find_doctor). A implementação
real (`CFMHttpClient`) e a de desenvolvimento/teste (`FakeCFMClient`) ficam
isoladas aqui, sem vazar detalhes do CFM para o resto da aplicação.
"""
