<#
.SYNOPSIS
Script para iniciar o projeto no Windows PowerShell.

.DESCRIPTION
Tenta subir PostgreSQL via Docker se disponível.
Se Docker não estiver instalado, usa SQLite local (sem Docker).
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
Set-Location $scriptDir

# Verificar se Docker está instalado
$dockerInstalled = $false
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $dockerInstalled = $true
    Write-Host 'Docker encontrado! ✅' -ForegroundColor Green
    
    # Verificar se Docker daemon está rodando
    try {
        docker info > $null 2>&1
        Write-Host 'Docker daemon está rodando! ✅' -ForegroundColor Green
        
        # Subir PostgreSQL
        $containerName = 'usermanager-postgres'
        $running = docker ps --filter "name=$containerName" --format '{{.Names}}' 2>$null
        
        if ($running -ne $containerName) {
            Write-Host "Iniciando PostgreSQL em Docker..." -ForegroundColor Cyan
            docker-compose up -d
            Write-Host 'Aguardando PostgreSQL ficar pronto...' -ForegroundColor Cyan
            Start-Sleep -Seconds 5
            Write-Host 'PostgreSQL iniciado! ✅' -ForegroundColor Green
        } else {
            Write-Host 'PostgreSQL já está rodando! ✅' -ForegroundColor Green
        }
    } catch {
        Write-Host 'Docker daemon não está rodando. Usando SQLite local.' -ForegroundColor Yellow
        Write-Host 'Dica: Abra Docker Desktop para usar PostgreSQL em Docker.' -ForegroundColor Yellow
    }
} else {
    Write-Host 'Docker não instalado. Usando SQLite local.' -ForegroundColor Yellow
    Write-Host 'Banco será armazenado em: usermanager.db' -ForegroundColor Cyan
    Write-Host '' -ForegroundColor Gray
    Write-Host 'Se quiser usar PostgreSQL em Docker depois:' -ForegroundColor Gray
    Write-Host '  1. Instale Docker Desktop: https://www.docker.com/products/docker-desktop' -ForegroundColor Gray
    Write-Host '  2. Execute este script novamente' -ForegroundColor Gray
    Write-Host '' -ForegroundColor Gray
}

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
