"""Normalização segura do CRM sem inferir informações pela numeração."""

import re


def crm_digits(value: str) -> str:
    return "".join(re.findall(r"\d", value or ""))
