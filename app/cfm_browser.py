"""Abre a busca pública do CFM e preenche os campos para revisão humana.

O CAPTCHA e o clique em ENVIAR são sempre feitos pela pessoa no navegador.
"""

import sys

from playwright.sync_api import sync_playwright

from app.cfm_client import CFM_SEARCH_URL, crm_for_cfm


def open_cfm_form(uf: str, crm: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(CFM_SEARCH_URL, wait_until="domcontentloaded")
        page.locator("#uf").select_option(label=uf)
        page.locator("#crm").fill(crm_for_cfm(crm, uf))
        page.bring_to_front()
        # Mantém a janela aberta para a pessoa conferir os dados, resolver o
        # CAPTCHA se aparecer e clicar em ENVIAR.
        page.wait_for_event("close")
        browser.close()


if __name__ == "__main__":
    open_cfm_form(sys.argv[1], sys.argv[2])
