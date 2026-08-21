$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not (Test-Path ".venv")) {
    Write-Host "Ambiente virtual não encontrado. Rodando uv sync..."
    uv sync
}

Write-Host "Iniciando o projeto..."
uv run uvicorn app.main:app --reload
