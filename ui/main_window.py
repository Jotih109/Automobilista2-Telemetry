import collections
import os
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QPushButton, QSizePolicy, QSplitter, QProgressBar
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
import pyqtgraph as pg

from core.models import TelemetryState
from core.engine import TelemetryEngine
from core.session_manager import SessionManager

from ui.sidebar_panel import SidebarPanel
from ui.components import TopMetricCard, SectorsCard, LegendsRow, CustomPlot, LapHistoryTable

# Auto-exporta uma imagem PNG da análise sempre que uma nova Melhor Volta (Best Lap)
# for concluída. Desligue se preferir só exportar manualmente pelo botão da UI.
AUTO_EXPORT_ON_BEST_LAP = True
EXPORT_DIR = "exportacoes"


class DashboardMainWindow(QMainWindow):
    def __init__(self, engine: TelemetryEngine):
        super().__init__()
        self.engine = engine
        
        self.setWindowTitle("Telemetry Pro - Analysis Tool")
        self.setGeometry(50, 50, 1400, 850)
        
        self.setStyleSheet("""
            QMainWindow { background-color: #0a0a0a; }
            QWidget { background-color: #0a0a0a; color: #ffffff; font-family: Consolas; }
        """)
        
        self.session_manager = SessionManager()
        self.last_track_car_signature = ""
        self._last_time_seen = ""
        self._graph_x_max = 120.0
        self._last_exported_best = ""
        self._last_state = None
        
        self.init_ui()
        
        # Conecta o seletor da Sidebar
        self.sidebar_panel.ghost_selector.combo.currentIndexChanged.connect(self.on_ghost_mode_changed)
        
        # Conecta o sinal da Thread (Engine) para atualizar a UI
        self.engine.on_update.connect(self.on_telemetry_update)
        
        # Inicia a Thread
        self.engine.start()

    def init_ui(self):
        pg.setConfigOption('background', '#151515')
        pg.setConfigOption('foreground', '#888888')
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)
        
        # --- Top Split: Sidebar (Esq) + Main Area (Dir) ---
        top_split = QHBoxLayout()
        top_split.setSpacing(12)
        
        # Sidebar
        self.sidebar_panel = SidebarPanel()
        top_split.addWidget(self.sidebar_panel)
        
        # Main Area (Direita)
        right_area = QVBoxLayout()
        right_area.setSpacing(6)
        
        # Metrics Row
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(12)
        
        self.card_current = TopMetricCard("Volta atual", "--:--.---")
        self.card_best = TopMetricCard("Melhor volta", "--:--.---")
        self.card_delta = TopMetricCard("Delta geral", "+0.00s", is_delta=True)
        self.card_sectors = SectorsCard()
        
        metrics_row.addWidget(self.card_current)
        metrics_row.addWidget(self.card_best)
        metrics_row.addWidget(self.card_delta)
        metrics_row.addWidget(self.card_sectors, stretch=1)
        
        right_area.addLayout(metrics_row)
        
        # Cabeçalho dos gráficos: Legenda à esquerda | Ref/Est + Botão Exportar à direita
        self.lbl_graph_legend = QLabel("— Sólida: Volta Atual    |    --- Tracejada: Volta Referência")
        self.lbl_graph_legend.setFont(QFont("Consolas", 10))
        self.lbl_graph_legend.setStyleSheet("color: #888888;")

        self.lbl_ref_est_laps = QLabel("Ref: --:--.---   |   Est: --:--.---")
        self.lbl_ref_est_laps.setFont(QFont("Consolas", 14, QFont.Bold))
        self.lbl_ref_est_laps.setStyleSheet("color: #aaaaaa;")

        self.btn_export = QPushButton("Exportar Análise (Imagem)")
        self.btn_export.setFont(QFont("Consolas", 9, QFont.Bold))
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #1e1e1e;
                color: #eedd82;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 5px 12px;
            }
            QPushButton:hover { background-color: #2a2a2a; border: 1px solid #eedd82; }
            QPushButton:pressed { background-color: #151515; }
        """)
        self.btn_export.clicked.connect(self.on_export_clicked)

        graph_header_row = QHBoxLayout()
        graph_header_row.setContentsMargins(0, 0, 0, 0)
        graph_header_row.addWidget(self.lbl_graph_legend, alignment=Qt.AlignVCenter)
        graph_header_row.addStretch()
        graph_header_row.addWidget(self.lbl_ref_est_laps, alignment=Qt.AlignVCenter)
        graph_header_row.addSpacing(15)
        graph_header_row.addWidget(self.btn_export, alignment=Qt.AlignVCenter)
        right_area.addLayout(graph_header_row)

        # Gráficos
        self._speed_y_max = 300.0  # escala Y dinâmica de velocidade

        self.plot_speed = CustomPlot("Velocidade (Km/h)")
        self.plot_speed.setYRange(0, 300)
        self.plot_speed.setXRange(0, 120)
        self.plot_speed.setLimits(xMin=0, xMax=120, yMin=0, yMax=500, minXRange=5, maxXRange=120)
        self.cursor_speed = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen(color='#ff0000', width=1.0))
        self.plot_speed.addItem(self.cursor_speed)
        
        self.sector1_line_speed = pg.InfiniteLine(pos=31.6, angle=90, pen=pg.mkPen(color='#444444', style=Qt.DashLine))
        self.sector2_line_speed = pg.InfiniteLine(pos=63.3, angle=90, pen=pg.mkPen(color='#444444', style=Qt.DashLine))
        self.plot_speed.addItem(self.sector1_line_speed)
        self.plot_speed.addItem(self.sector2_line_speed)
        
        # Labels S1 / S2 Speed — stored as attrs so we can reposition them later
        self.s1_text_speed = pg.TextItem("S1", color='#888888')
        self.s1_text_speed.setPos(31.6, 280)
        self.plot_speed.addItem(self.s1_text_speed)
        
        self.s2_text_speed = pg.TextItem("S2", color='#888888')
        self.s2_text_speed.setPos(63.3, 280)
        self.plot_speed.addItem(self.s2_text_speed)

        pen_ghost_speed = pg.mkPen(color=(200, 150, 255, 180), width=4.0, style=Qt.SolidLine)
        self.curve_ghost_speed = self.plot_speed.plot(pen=pen_ghost_speed)
        self.curve_speed = self.plot_speed.plot(pen=pg.mkPen(color='#66b2ff', width=3.0))
        
        self.plot_gas = CustomPlot("Acelerador (%)")
        self.plot_gas.setYRange(0, 105)
        self.plot_gas.setXRange(0, 120)
        self.plot_gas.setLimits(xMin=0, xMax=120, yMin=-5, yMax=110, minXRange=5, maxXRange=120)
        self.cursor_gas = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen(color='#ff0000', width=1.0))
        self.plot_gas.addItem(self.cursor_gas)

        self.sector1_line_gas = pg.InfiniteLine(pos=31.6, angle=90, pen=pg.mkPen(color='#444444', style=Qt.DashLine))
        self.sector2_line_gas = pg.InfiniteLine(pos=63.3, angle=90, pen=pg.mkPen(color='#444444', style=Qt.DashLine))
        self.plot_gas.addItem(self.sector1_line_gas)
        self.plot_gas.addItem(self.sector2_line_gas)

        self.plot_brake = CustomPlot("Freio (%)")
        self.plot_brake.setYRange(0, 105)
        self.plot_brake.setXRange(0, 120)
        self.plot_brake.setLimits(xMin=0, xMax=120, yMin=-5, yMax=110, minXRange=5, maxXRange=120)
        self.cursor_brake = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen(color='#ff0000', width=1.0))
        self.plot_brake.addItem(self.cursor_brake)

        self.sector1_line_brake = pg.InfiniteLine(pos=31.6, angle=90, pen=pg.mkPen(color='#444444', style=Qt.DashLine))
        self.sector2_line_brake = pg.InfiniteLine(pos=63.3, angle=90, pen=pg.mkPen(color='#444444', style=Qt.DashLine))
        self.plot_brake.addItem(self.sector1_line_brake)
        self.plot_brake.addItem(self.sector2_line_brake)


        # Gráfico de RPM
        self.plot_rpm = CustomPlot("RPM")
        self.plot_rpm.setYRange(0, 9000)
        self.plot_rpm.setXRange(0, 120)
        self.plot_rpm.setLimits(xMin=0, xMax=120, yMin=0, yMax=20000, minXRange=5, maxXRange=120)
        self.cursor_rpm = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen(color='#ff0000', width=1.0))
        self.plot_rpm.addItem(self.cursor_rpm)
        self.sector1_line_rpm = pg.InfiniteLine(pos=31.6, angle=90, pen=pg.mkPen(color='#444444', style=Qt.DashLine))
        self.sector2_line_rpm = pg.InfiniteLine(pos=63.3, angle=90, pen=pg.mkPen(color='#444444', style=Qt.DashLine))
        self.plot_rpm.addItem(self.sector1_line_rpm)
        self.plot_rpm.addItem(self.sector2_line_rpm)

        pen_ghost_gas = pg.mkPen(color=(0, 255, 0, 150), width=4.0, style=Qt.SolidLine)
        pen_ghost_brake = pg.mkPen(color=(255, 100, 100, 150), width=4.0, style=Qt.SolidLine)
        pen_ghost_rpm = pg.mkPen(color=(150, 100, 255, 150), width=3.0, style=Qt.SolidLine)
        
        self.curve_ghost_gas = self.plot_gas.plot(pen=pen_ghost_gas)
        self.curve_ghost_brake = self.plot_brake.plot(pen=pen_ghost_brake)
        self.curve_ghost_rpm = self.plot_rpm.plot(pen=pen_ghost_rpm)
        
        self.curve_gas = self.plot_gas.plot(pen=pg.mkPen(color='#00ff00', width=2.0))
        self.curve_brake = self.plot_brake.plot(pen=pg.mkPen(color='#ff4444', width=2.0))
        self.curve_rpm = self.plot_rpm.plot(pen=pg.mkPen(color='#aa66ff', width=2.0))
        
        self.plot_splitter = QSplitter(Qt.Vertical)
        self.plot_splitter.setStyleSheet("QSplitter::handle { background-color: #333333; margin: 2px 0px; }")
        self.plot_splitter.addWidget(self.plot_speed)
        self.plot_splitter.addWidget(self.plot_gas)
        self.plot_splitter.addWidget(self.plot_brake)
        self.plot_splitter.addWidget(self.plot_rpm)
        # Todos com o mesmo tamanho
        for i in range(4):
            self.plot_splitter.setStretchFactor(i, 1)
        self.plot_splitter.setSizes([220, 220, 220, 220])
        
        right_area.addWidget(self.plot_splitter, stretch=1)

        # Barra de progresso da posição na pista
        track_pos_row = QHBoxLayout()
        track_pos_row.setContentsMargins(0, 4, 0, 0)
        lbl_pos = QLabel("Pista:")
        lbl_pos.setFont(QFont("Consolas", 9))
        lbl_pos.setStyleSheet("color: #555555;")
        lbl_pos.setFixedWidth(42)
        self.track_pos_bar = QProgressBar()
        self.track_pos_bar.setRange(0, 1000)
        self.track_pos_bar.setValue(0)
        self.track_pos_bar.setTextVisible(False)
        self.track_pos_bar.setFixedHeight(10)
        self.track_pos_bar.setStyleSheet("""
            QProgressBar { background-color: #1a1a1a; border: none; border-radius: 5px; }
            QProgressBar::chunk { background-color: #66b2ff; border-radius: 5px; }
        """)
        self.lbl_track_pos_pct = QLabel("0.0%")
        self.lbl_track_pos_pct.setFont(QFont("Consolas", 9))
        self.lbl_track_pos_pct.setStyleSheet("color: #555555;")
        self.lbl_track_pos_pct.setFixedWidth(48)
        track_pos_row.addWidget(lbl_pos)
        track_pos_row.addWidget(self.track_pos_bar)
        track_pos_row.addWidget(self.lbl_track_pos_pct)
        right_area.addLayout(track_pos_row)
        
        top_split.addLayout(right_area)
        
        # --- Bottom Split: Lap History ---
        self.lap_history_table = LapHistoryTable()
        self.lap_history_table.setMinimumHeight(100)
        self.lap_history_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        main_layout.addLayout(top_split, stretch=4)
        
        lbl_history_title = QLabel("Histórico de voltas")
        lbl_history_title.setFont(QFont("Consolas", 10))
        lbl_history_title.setStyleSheet("color: #ffffff; margin-top: 2px; margin-bottom: 2px;")
        main_layout.addWidget(lbl_history_title)
        
        main_layout.addWidget(self.lap_history_table, stretch=2)
 
    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _parse_time_ms(t_str: str) -> int:
        """Parse '1:29.650' or '--:--.---' to milliseconds."""
        try:
            if not t_str or '-' in t_str:
                return 0
            if '.' in t_str:
                min_sec, millis = t_str.rsplit('.', 1)
                parts = min_sec.split(':')
                minutes = int(parts[0]) if len(parts) >= 2 else 0
                seconds = int(parts[-1])
                return (minutes * 60 * 1000) + (seconds * 1000) + int(millis.ljust(3, '0')[:3])
        except Exception:
            pass
        return 0

    @staticmethod
    def _format_ms(ms: int) -> str:
        """Format milliseconds back to 'M:SS.mmm'."""
        if ms <= 0:
            return "--:--.---"
        minutes = ms // 60000
        seconds = (ms % 60000) // 1000
        millis = ms % 1000
        return f"{minutes}:{seconds:02d}.{millis:03d}"

    def _calc_sector_delta(self, current_str: str, ref_str: str) -> str:
        """Returns '+0.123s' / '-0.123s' or '' if data not available."""
        curr_ms = self._parse_time_ms(current_str)
        ref_ms  = self._parse_time_ms(ref_str)
        if curr_ms <= 0 or ref_ms <= 0:
            return ""
        delta_s = (curr_ms - ref_ms) / 1000.0
        return f"{delta_s:+.3f}s"

    def _projected_lap(self, best_time_str: str, delta_s: float) -> str:
        """Best time ± delta → projected finish time string."""
        best_ms = self._parse_time_ms(best_time_str)
        if best_ms <= 0:
            return "--:--.---"
        projected_ms = int(best_ms + delta_s * 1000)
        return self._format_ms(max(0, projected_ms))

    def _update_graph_scale(self, state: TelemetryState, best_time_str: str):
        """
        Ajusta o eixo X (tempo) dos gráficos:
        - Se já existe uma melhor volta, usa BestLapTime * 1.05.
        - Caso contrário, usa um padrão de 2 minutos (120s) conforme solicitado pelo usuário.
        """
        best_ms = self._parse_time_ms(best_time_str)
        if best_ms > 0:
            target = (best_ms / 1000.0) * 1.05
        else:
            target = 120.0  # Padrão inicial de 2 minutos

        target = max(10.0, target)

        # Só reaplica os limites quando a mudança é relevante (evita "tremer" o gráfico)
        if abs(target - self._graph_x_max) > 1.0:
            self._graph_x_max = target
            for plot in (self.plot_speed, self.plot_gas, self.plot_brake, self.plot_rpm):
                plot.setXRange(0, target, padding=0)
                plot.setLimits(xMin=0, xMax=target, minXRange=5, maxXRange=target)

    # -----------------------------------------------------------------------
    # Exportação de imagem (PNG)
    # -----------------------------------------------------------------------

    def export_analysis_image(self, auto: bool = False, lap_number: int = None, lap_time_str: str = None) -> str:
        """
        Salva um snapshot (PNG) do dashboard completo em EXPORT_DIR.
        Chamado manualmente pelo botão "Exportar Análise (Imagem)" ou
        automaticamente quando AUTO_EXPORT_ON_BEST_LAP=True e uma nova
        Melhor Volta é concluída.
        """
        os.makedirs(EXPORT_DIR, exist_ok=True)

        if lap_number is None:
            lap_number = getattr(self._last_state, "lap_number", 0) if self._last_state else 0
        if lap_time_str is None:
            lap_time_str = self.card_best.lbl_val.text()

        safe_time = lap_time_str.replace(":", "-").replace(".", "-")
        prefix = "BestLap" if auto else "Analise"
        filename = f"{prefix}_Volta{lap_number}_{safe_time}.png"
        path = os.path.join(EXPORT_DIR, filename)

        pixmap = self.centralWidget().grab()
        if pixmap.save(path, "PNG"):
            print(f"[Export] Imagem da análise salva em: {path}")
        else:
            print(f"[Export] Falha ao salvar imagem em: {path}")
        return path

    def on_export_clicked(self):
        self.export_analysis_image(auto=False)

    def _update_sector_lines(self):
        """Reposition S1/S2 vertical lines using actual sector boundaries from the selected reference ghost."""
        idx = self.sidebar_panel.ghost_selector.combo.currentIndex()
        ghost = self._reference_ghost_for_index(idx).get("telemetry", {})
        times = ghost.get("times", [])
        sectors = ghost.get("sector", [])
        if len(times) < 2 or len(sectors) < 2:
            return
        s1_end = s2_end = None
        for i in range(1, len(sectors)):
            if s1_end is None and sectors[i] == 1 and sectors[i - 1] == 0:
                s1_end = times[i]
            if s2_end is None and sectors[i] == 2 and sectors[i - 1] == 1:
                s2_end = times[i]
            if s1_end and s2_end:
                break
        if s1_end:
            self.sector1_line_speed.setValue(s1_end)
            self.sector1_line_gas.setValue(s1_end)
            self.sector1_line_brake.setValue(s1_end)
            self.sector1_line_rpm.setValue(s1_end)
            self.s1_text_speed.setPos(s1_end, self.plot_speed.viewRange()[1][1] * 0.9)
        if s2_end:
            self.sector2_line_speed.setValue(s2_end)
            self.sector2_line_gas.setValue(s2_end)
            self.sector2_line_brake.setValue(s2_end)
            self.sector2_line_rpm.setValue(s2_end)
            self.s2_text_speed.setPos(s2_end, self.plot_speed.viewRange()[1][1] * 0.9)

    # -----------------------------------------------------------------------
    # Main telemetry update slot
    # -----------------------------------------------------------------------

    def _reference_ghost_for_index(self, idx: int) -> dict:
        """Maps the Ghost Selector combo index to the corresponding stored ghost."""
        if idx == 1:   # Personal Best
            return self.session_manager.best_lap_ghost
        elif idx == 2 or idx == 0:  # Session Record or Desativado (calculates deltas based on session best)
            return self.session_manager.session_best_lap_ghost
        elif idx == 3:  # Ideal Lap
            return self.session_manager.ideal_lap_ghost
        return self.session_manager._empty_ghost()

    def on_telemetry_update(self, state: TelemetryState):
        if not state.is_connected:
            return

        self._last_state = state

        # 1. PROCESS STATE FIRST! This calculates Live Delta and Sectors,
        #    using whichever reference lap is currently selected in the sidebar.
        idx = self.sidebar_panel.ghost_selector.combo.currentIndex()
        reference_ghost = self._reference_ghost_for_index(idx)
        self.session_manager.process_state(state, reference_ghost=reference_ghost)
        self._update_sector_lines()
        
        # Inject calculated fuel avg into state for sidebar to display
        state._fuel_avg = self.session_manager.avg_fuel_per_lap
        
        # Recalculate fuel_laps_remaining using our computed avg
        if self.session_manager.avg_fuel_per_lap > 0 and state.fuel > 0:
            state.fuel_laps_remaining = state.fuel / self.session_manager.avg_fuel_per_lap
        
        self.sidebar_panel.update_panel(state)

        # --- Lap time cards ---
        curr_time_str = state.current_time if state.current_time else "--:--.---"
        best_time_str = state.best_time if state.best_time else "--:--.---"
        # Validate best_time: reject if < 30s (pit exit glitch)
        if self._parse_time_ms(best_time_str) < 30000:
            best_time_str = self.session_manager.session_best_lap_ghost["metadata"].get("lap_time_str", "--:--.---") or "--:--.---"
        self.card_current.set_value(curr_time_str)
        self.card_best.set_value(best_time_str)

        # Auto-exporta uma imagem sempre que uma NOVA melhor volta é registrada
        if AUTO_EXPORT_ON_BEST_LAP and best_time_str != "--:--.---" and best_time_str != self._last_exported_best:
            self._last_exported_best = best_time_str
            completed_lap_number = max(1, state.lap_number - 1)
            self.export_analysis_image(auto=True, lap_number=completed_lap_number, lap_time_str=best_time_str)

        # Escala dinâmica do eixo X dos gráficos, baseada na melhor volta / comprimento da pista
        self._update_graph_scale(state, best_time_str)

        # Determine Reference Time based on Ghost Selector (idx already read above)
        # Always pull the time from the ghost's own metadata to stay consistent with
        # the telemetry data used for delta calculation.
        has_valid_reference = False
        ref_lap_str = "--:--.---"
        
        if idx == 1: # Personal Best
            ref_lap_str = (
                self.session_manager.best_lap_ghost["metadata"].get("lap_time_str", "")
                or best_time_str
            )
        elif idx == 2 or idx == 0: # Session Record ou Desativado
            ref_lap_str = self.session_manager.session_best_lap_ghost["metadata"].get("lap_time_str", "--:--.---") or "--:--.---"
        elif idx == 3: # Ideal Lap
            ref_lap_str = self.session_manager.ideal_lap_ghost["metadata"].get("lap_time_str", "--:--.---") or "--:--.---"
            
        if self._parse_time_ms(ref_lap_str) > 0:
            has_valid_reference = True

        # Delta card + projected/reference lap
        delta_val = state.delta_time if has_valid_reference else 0.0
        if has_valid_reference:
            self.card_delta.set_value(f"{delta_val:+.2f}s", delta_val)
        else:
            self.card_delta.set_value("+0.00s", 0.0)
            self.card_delta.lbl_val.setStyleSheet("color: #888888; font-weight: bold;")
        
        # Reference & Estimated lap
        best_ms = self._parse_time_ms(ref_lap_str)
        if has_valid_reference and best_ms > 0:
            est_ms = best_ms + int(delta_val * 1000)
            ref_str = f"Ref: {ref_lap_str}"
            est_str = f"Est: {self._format_ms(max(0, est_ms))}"
            self.lbl_ref_est_laps.setText(f"<div style='text-align: right;'>"
                                          f"<span style='color: #eedd82;'>{ref_str}</span>&nbsp;&nbsp;&nbsp;&nbsp;"
                                          f"<span style='color: #aaaaaa;'>{est_str}</span>"
                                          f"</div>")
        else:
            self.lbl_ref_est_laps.setText("<div style='text-align: right;'>"
                                          "<span style='color: #888888;'>Ref: --:--.---</span>&nbsp;&nbsp;&nbsp;&nbsp;"
                                          "<span style='color: #888888;'>Est: --:--.---</span>"
                                          "</div>")
        
        # --- Sectors ---
        # Garantindo gatilho seguro usando os tempos salvos pelo session_manager
        def format_ms(ms):
            if ms <= 0: return "--:--.---"
            m = ms // 60000
            s = (ms % 60000) // 1000
            mls = ms % 1000
            if m > 0: return f"{m}:{s:02d}.{mls:03d}"
            return f"{s}.{mls:03d}"

        s1_ms = self.session_manager.current_sector_times[0]
        s2_ms = self.session_manager.current_sector_times[1]
        s3_ms = self.session_manager.current_sector_times[2]
        
        s1_val = format_ms(s1_ms)
        s2_val = format_ms(s2_ms)
        s3_val = format_ms(s3_ms)
        
        # Enquanto o setor atual ainda está rolando, podemos deixar o superior como o tempo de volta correndo ou vazio
        if state.sector_index == 0 and s1_ms == 0:
            s1_val = state.current_time  # fallback rolling time
        elif state.sector_index == 1 and s2_ms == 0:
            # We are in sector 2, s1_val is locked. We can show rolling time in S2
            pass
            
        # Deltas de setor seguem a mesma referência selecionada no Ghost Selector
        pb_times = self.session_manager.current_reference_sector_ms
        pb1, pb2, pb3 = format_ms(pb_times[0]), format_ms(pb_times[1]), format_ms(pb_times[2])
        d1, d2, d3 = "", "", ""
        
        if has_valid_reference:
            d1 = self._calc_sector_delta(s1_val, pb1) if s1_ms > 0 else ""
            d2 = self._calc_sector_delta(s2_val, pb2) if s2_ms > 0 else ""
            d3 = self._calc_sector_delta(s3_val, pb3) if s3_ms > 0 else ""
        
        self.card_sectors.update_sectors(
            s1_val, s2_val, s3_val,
            pb1, pb2, pb3,
            d1, d2, d3
        )
        
        # --- Ghost / sector lines ---
        signature = f"{state.track_name}_{state.car_name}"
        if signature != self.last_track_car_signature and signature != "Unknown Track_Unknown Car":
            self.last_track_car_signature = signature
            # Atualiza título da janela com pista e carro
            self.setWindowTitle(f"Telemetry Pro — {state.track_name} | {state.car_name}")
            if self.session_manager.auto_load_ghosts(state):
                self.on_ghost_mode_changed()
  
        # --- Track position progress bar ---
        track_pos = getattr(state, 'track_position', 0.0)
        self.track_pos_bar.setValue(int(track_pos * 1000))
        self.lbl_track_pos_pct.setText(f"{track_pos * 100:.1f}%")

        # --- Cursor update ---
        curr = self.session_manager.current_lap_data
        if len(curr["times"]) > 0:
            current_time_sec = curr["times"][-1]
            self.cursor_speed.setValue(current_time_sec)
            self.cursor_gas.setValue(current_time_sec)
            self.cursor_brake.setValue(current_time_sec)
            self.cursor_rpm.setValue(current_time_sec)
            
            # --- Graph data ---
            gas_100 = [g * 100.0 for g in curr["gas"]]
            brake_100 = [b * 100.0 for b in curr["brake"]]
            self.curve_speed.setData(curr["times"], curr["speed"])
            self.curve_gas.setData(curr["times"], gas_100)
            self.curve_brake.setData(curr["times"], brake_100)
            self.curve_rpm.setData(curr["times"], curr["rpm"])

            # Escala Y dinâmica para velocidade
            if curr["speed"]:
                max_speed = max(curr["speed"])
                # Adiciona 20 km/h de margem e arredonda para o próximo múltiplo de 20
                # (se o valor já for múltiplo exato de 50, usa 50; caso contrário, 20)
                target_y = max_speed + 20
                if target_y <= 100:
                    step = 20
                elif target_y <= 250:
                    step = 20
                else:
                    step = 50
                import math
                rounded_y = math.ceil(target_y / step) * step
                if rounded_y != self._speed_y_max:
                    self._speed_y_max = rounded_y
                    self.plot_speed.setYRange(0, self._speed_y_max, padding=0)
                    self.plot_speed.setLimits(yMin=0, yMax=max(self._speed_y_max + 50, 350))

            # Escala Y dinâmica para RPM
            max_rpm_val = getattr(state, 'max_rpm', 9000.0)
            self.plot_rpm.setYRange(0, max_rpm_val * 1.05, padding=0)
            
        # --- Update Lap History dynamically by Lap ID ---
        self._update_live_lap_history(state)
        
    def _update_live_lap_history(self, state: TelemetryState):
        from PyQt5.QtWidgets import QTableWidgetItem
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QColor
        
        def format_ms(ms):
            if ms <= 0: return "--:--.---"
            m = ms // 60000
            s = (ms % 60000) // 1000
            mls = ms % 1000
            if m > 0: return f"{m}:{s:02d}.{mls:03d}"
            return f"{s}.{mls:03d}"

        def set_cell(row, col, text):
            item = self.lap_history_table.item(row, col)
            if item is None:
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                self.lap_history_table.setItem(row, col, item)
            else:
                item.setText(text)

        def ensure_row(lap_num):
            """Return (row_idx, is_new) for the given lap number."""
            for i in range(self.lap_history_table.rowCount()):
                item = self.lap_history_table.item(i, 0)
                if item and item.text() == str(lap_num):
                    return i, False
            row_idx = self.lap_history_table.rowCount()
            self.lap_history_table.insertRow(row_idx)
            num_item = QTableWidgetItem(str(lap_num))
            num_item.setTextAlignment(Qt.AlignCenter)
            self.lap_history_table.setItem(row_idx, 0, num_item)
            for col in range(1, 6):
                ph = QTableWidgetItem("--:--.---" if col < 5 else "")
                ph.setTextAlignment(Qt.AlignCenter)
                self.lap_history_table.setItem(row_idx, col, ph)
            return row_idx, True

        # Calcular o melhor tempo de volta para highlight
        best_time_ms = 0
        best_row_idx = -1

        # --- 1. Sync all COMPLETED laps from historic_laps (frozen data) ---
        for lap_data in self.session_manager.historic_laps:
            lap_num = lap_data.get("lap_number", 0)
            if lap_num <= 0:
                continue
            row_idx, _ = ensure_row(lap_num)
            set_cell(row_idx, 1, lap_data.get("s1", "--:--.---"))
            set_cell(row_idx, 2, lap_data.get("s2", "--:--.---"))
            set_cell(row_idx, 3, lap_data.get("s3", "--:--.---"))
            total_str = lap_data.get("total_time", "--:--.---")
            set_cell(row_idx, 4, total_str)
            # Calcular delta vs best
            lap_ms = self._parse_time_ms(total_str)
            if lap_ms > 0:
                if best_time_ms == 0 or lap_ms < best_time_ms:
                    best_time_ms = lap_ms
                    best_row_idx = row_idx

        # Preencher coluna de delta para todas as voltas completadas
        if best_time_ms > 0:
            for lap_data in self.session_manager.historic_laps:
                lap_num = lap_data.get("lap_number", 0)
                if lap_num <= 0:
                    continue
                row_idx, _ = ensure_row(lap_num)
                total_str = lap_data.get("total_time", "--:--.---")
                lap_ms = self._parse_time_ms(total_str)
                if lap_ms > 0:
                    delta_ms = lap_ms - best_time_ms
                    if delta_ms == 0:
                        delta_str = "BEST"
                    else:
                        delta_s = delta_ms / 1000.0
                        delta_str = f"+{delta_s:.3f}s"
                    set_cell(row_idx, 5, delta_str)

        # Highlight best row
        prev_best = self.lap_history_table._best_row
        if best_row_idx != prev_best:
            self.lap_history_table.highlight_best_lap(best_row_idx, prev_best)
            self.lap_history_table._best_row = best_row_idx

        # --- 2. Active lap row: show live sectors ---
        lap_number = state.lap_number
        if lap_number > 0:
            row_idx, _ = ensure_row(lap_number)
            sm = self.session_manager
            s1 = format_ms(sm.current_sector_times[0])
            s2 = format_ms(sm.current_sector_times[1])
            s3 = format_ms(sm.current_sector_times[2])
            # Only update cells that are still blank (don't overwrite completed data)
            if sm.current_sector_times[0] > 0:
                set_cell(row_idx, 1, s1)
            if sm.current_sector_times[1] > 0:
                set_cell(row_idx, 2, s2)
            if sm.current_sector_times[2] > 0:
                set_cell(row_idx, 3, s3)

        self.lap_history_table.scrollToBottom()

    def add_lap_to_history(self, lap_data: dict):
        # Historic data is managed by _update_live_lap_history via session_manager.historic_laps
        pass

    def on_ghost_mode_changed(self):
        idx = self.sidebar_panel.ghost_selector.combo.currentIndex()
        ghost = None
        
        if idx == 0:
            self.curve_ghost_speed.setData([], [])
            self.curve_ghost_gas.setData([], [])
            self.curve_ghost_brake.setData([], [])
            self.curve_ghost_rpm.setData([], [])
            return
        elif idx == 1:
            ghost = self.session_manager.best_lap_ghost.get("telemetry", {})
        elif idx == 2:
            ghost = self.session_manager.session_best_lap_ghost.get("telemetry", {})
        elif idx == 3:
            ghost = self.session_manager.ideal_lap_ghost.get("telemetry", {})
            
        if ghost and len(ghost.get("times", [])) > 0:
            x_data = ghost.get("times", [])
            ghost_gas_100 = [g * 100.0 for g in ghost.get("gas", [])]
            ghost_brake_100 = [b * 100.0 for b in ghost.get("brake", [])]
            ghost_rpm = ghost.get("rpm", [0] * len(x_data))
            self.curve_ghost_speed.setData(x_data, ghost["speed"])
            self.curve_ghost_gas.setData(x_data, ghost_gas_100)
            self.curve_ghost_brake.setData(x_data, ghost_brake_100)
            self.curve_ghost_rpm.setData(x_data, ghost_rpm)
        else:
            self.curve_ghost_speed.setData([], [])
            self.curve_ghost_gas.setData([], [])
            self.curve_ghost_brake.setData([], [])
            self.curve_ghost_rpm.setData([], [])

    def closeEvent(self, event):
        print("Parando Thread de Telemetria...")
        self.engine.stop() 
        event.accept()
