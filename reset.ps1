Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  AMS2 Telemetria - Reset e Limpeza da porta 5606" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Mata todos os processos na porta 5606
$pids = (netstat -ano | Select-String "UDP.*:5606" | ForEach-Object {
    ($_.Line -split '\s+') | Select-Object -Last 1
} | Sort-Object -Unique)

if ($pids) {
    foreach ($p in $pids) {
        if ($p -match '^\d+$') {
            Write-Host "  Matando processo PID: $p" -ForegroundColor Yellow
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "  Porta 5606 liberada!" -ForegroundColor Green
} else {
    Write-Host "  Porta 5606 ja esta livre." -ForegroundColor Green
}

Start-Sleep -Milliseconds 500

# Inicia o mock em janela separada
Write-Host "`n  Iniciando mock_game.py..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit -Command `"cd '$PWD'; python mock_game.py`"" -WindowStyle Normal

Start-Sleep -Milliseconds 800

# Inicia o dashboard
Write-Host "  Iniciando main.py..." -ForegroundColor Cyan
py .\main.py
