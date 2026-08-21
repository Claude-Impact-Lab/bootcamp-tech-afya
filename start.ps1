<#
.SYNOPSIS
Script para iniciar o projeto no Windows PowerShell.

.DESCRIPTION
Inicia o servidor FastAPI usando SQLite local como banco de dados.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
Set-Location $scriptDir

Write-Host 'Iniciando User Manager' -ForegroundColor Cyan
Write-Host 'Banco de dados: SQLite (usermanager.db)' -ForegroundColor Green
Write-Host ''

# Verificar se uv está instalado
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host 'uv não foi encontrado. Instale o uv antes de usar este script.' -ForegroundColor Yellow
    Write-Host 'https://docs.astral.sh/uv/getting-started/installation/' -ForegroundColor Yellow
    exit 1
}

# Sincronizar dependências
if (-not (Test-Path '.venv')) {
    Write-Host 'Ambiente .venv não encontrado. Executando uv sync...' -ForegroundColor Cyan
    uv sync
    Write-Host 'Dependências instaladas! ✅' -ForegroundColor Green
} else {
    Write-Host 'Ambiente .venv encontrado. ✅' -ForegroundColor Green
}

Write-Host '' -ForegroundColor Gray
Write-Host 'Iniciando o servidor...' -ForegroundColor Cyan
Write-Host 'Acesse http://localhost:8000 no seu navegador.' -ForegroundColor Green
Write-Host '' -ForegroundColor Gray
Write-Host 'Para parar o servidor: Ctrl+C' -ForegroundColor Gray
Write-Host 'Para sair: Ctrl+C depois Enter' -ForegroundColor Gray
Write-Host '' -ForegroundColor Gray

uv run uvicorn app.main:app --reload
