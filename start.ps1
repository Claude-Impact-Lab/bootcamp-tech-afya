<#
.SYNOPSIS
Script para iniciar o projeto no Windows PowerShell.

.DESCRIPTION
Verifica se o ambiente do uv já existe, executa `uv sync` se necessário,
e em seguida inicia o servidor FastAPI com uvicorn.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
Set-Location $scriptDir

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host 'uv não foi encontrado. Instale o uv antes de usar este script.' -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path '.venv')) {
    Write-Host 'Ambiente .venv não encontrado. Executando uv sync...' -ForegroundColor Cyan
    uv sync
} else {
    Write-Host 'Ambiente .venv encontrado. Pulando uv sync.' -ForegroundColor Green
}

Write-Host 'Iniciando o servidor...' -ForegroundColor Cyan
uv run uvicorn app.main:app --reload
