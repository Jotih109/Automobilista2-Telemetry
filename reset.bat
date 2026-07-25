@echo off
echo ============================================================
echo  AMS2 Telemetria - Limpeza da porta UDP 5606
echo ============================================================
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5606 ^| findstr UDP') do (
    echo Matando processo PID: %%a
    taskkill /PID %%a /F ^>nul 2^>^&1
)
echo Porta 5606 liberada!
echo.
echo Iniciando Telemetry Pro...
cd /d "%~dp0"
start python mock_game.py
timeout /t 1 /nobreak ^>nul
py main.py
