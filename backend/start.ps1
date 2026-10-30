param(
    [ValidateSet("meal", "coach", "health", "event")]
    [string]$Service = "meal"
)

$servicePort = @{
    meal   = 8000
    coach  = 8001
    health = 8002
    event  = 8003
}[$Service]

$serviceFolder = Join-Path $PSScriptRoot "${Service}_service"
$requirementsPath = Join-Path $serviceFolder "requirements.txt"

Write-Host "Starting StressOFF $Service service..." -ForegroundColor Green

if (-Not (Test-Path "$PSScriptRoot/venv")) {
    Write-Host "Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv "$PSScriptRoot/venv"
    Write-Host "Virtual environment created." -ForegroundColor Green
}

Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& "$PSScriptRoot/venv/Scripts/Activate.ps1"

Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install --upgrade pip --quiet
pip install -r $requirementsPath --quiet

$modulePath = "backend.${Service}_service.main:app"
Write-Host "Launching uvicorn ($modulePath) on port $servicePort" -ForegroundColor Green
Write-Host "Docs: http://127.0.0.1:$servicePort/docs" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow

uvicorn $modulePath --host 0.0.0.0 --port $servicePort
