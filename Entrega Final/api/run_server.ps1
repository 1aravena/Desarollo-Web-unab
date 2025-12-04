# Script para iniciar el servidor de desarrollo
Write-Host "Iniciando servidor de Pizzería La Fornace..."
# Intentar usar el entorno virtual si existe
if (Test-Path "venv/Scripts/Activate.ps1") {
    & "venv/Scripts/Activate.ps1"
}
uvicorn main:app --reload --host 0.0.0.0 --port 8000