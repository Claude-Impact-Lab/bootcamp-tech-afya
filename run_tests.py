#!/usr/bin/env python
"""Script para rodar os testes e mostrar resultados."""

import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
    cwd=r"c:\Users\GABRIEL\Documents\Projeto-afya\bootcamp-tech-afya",
)

sys.exit(result.returncode)
