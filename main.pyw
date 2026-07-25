"""
main.py — Ponto de entrada do Dashboard de Telemetria AMS2
===========================================================
Fluxo de inicialização:
  1. AMS2TelemetryProvider  — Abre socket UDP e escuta pacotes do AMS2
  2. TelemetryEngine        — Thread a 60 Hz que chama get_state() e emite sinais Qt
  3. DashboardMainWindow    — Interface gráfica que reage aos sinais da Engine
"""

import os
import sys
import subprocess
from PyQt5.QtWidgets import QApplication

from providers.automobilista2 import AMS2TelemetryProvider
from providers.mock import MockTelemetryProvider
from core.engine import TelemetryEngine
from ui.main_window import DashboardMainWindow

# --------------------------------------------------------------------------
# MOCK_MODE
# --------------------------------------------------------------------------
# True  -> usa o MockTelemetryProvider (simulador interno, sem UDP, sem jogo).
#          Ideal para testar a interface e a lógica de setores/deltas/gráficos
#          numa máquina onde o AMS2 não está instalado.
# False -> usa o AMS2TelemetryProvider real, escutando UDP na porta 5606.
#          Configure no jogo: Options → Gameplay → UDP Telemetry → 127.0.0.1:5606
MOCK_MODE = False


def free_udp_port(port: int):
    """Mata processos fantasmas que prenderam a porta UDP (evita falha de bind)."""
    try:
        output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
        current_pid = os.getpid()
        for line in output.splitlines():
            if f":{port}" in line and "UDP" in line:
                parts = line.strip().split()
                if not parts:
                    continue
                pid_str = parts[-1]
                if pid_str.isdigit():
                    pid = int(pid_str)
                    if pid != current_pid:
                        print(f"[*] Limpando porta {port} (matando processo zumbi PID {pid})")
                        subprocess.run(f"taskkill /PID {pid} /F", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def main():
    app = QApplication(sys.argv)

    if MOCK_MODE:
        print("[*] MOCK_MODE ativo — usando simulador interno de telemetria (sem AMS2, sem UDP).")
        provider = MockTelemetryProvider()
    else:
        free_udp_port(5606)
        # Configure no jogo: Options → Gameplay → UDP Telemetry → 127.0.0.1:5606
        provider = AMS2TelemetryProvider()

    # Injeta o provider na Engine central (60 Hz)
    engine = TelemetryEngine(provider=provider, hz=60)

    # 3. Passa a Engine para a Interface Gráfica
    window = DashboardMainWindow(engine)
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
