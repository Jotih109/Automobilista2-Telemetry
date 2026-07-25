from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, 
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
import pyqtgraph as pg

# --- Pure Functions for Semantic Colors ---

def get_delta_color_bg(delta_val: float) -> str:
    if delta_val < 0:
        return "#003300" # verde escuro fundo
    elif delta_val > 0:
        return "#330000" # vermelho escuro fundo
    return "#151515"

def get_delta_color_text(delta_val: float) -> str:
    if delta_val < 0:
        return "#00ff00"
    elif delta_val > 0:
        return "#ff4444"
    return "#888888"

def get_sector_color(sector_time_str: str, personal_best_str: str, session_record_str: str) -> str:
    """Retorna roxo (recorde), verde (melhor pessoal) ou vermelho (lento)."""
    if sector_time_str == "--:--" or not sector_time_str:
        return "#888888"
        
    if session_record_str and sector_time_str <= session_record_str:
        return "#b266ff" # Roxo
    elif personal_best_str and sector_time_str <= personal_best_str:
        return "#00ff00" # Verde
    
    return "#ff4444" # Vermelho / Mais lento

# --- Base UI Components ---

class BaseCard(QFrame):
    def __init__(self, title=None, margins=(12, 12, 12, 12), spacing=8):
        super(BaseCard, self).__init__()
        self.setStyleSheet("background-color: #151515; border-radius: 8px;")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(*margins)
        self.main_layout.setSpacing(spacing)
        
        if title:
            self.lbl_title = QLabel(title)
            self.lbl_title.setFont(QFont("Consolas", 10))
            self.lbl_title.setStyleSheet("color: #888888; background: transparent;")
            self.main_layout.addWidget(self.lbl_title)

# --- Sidebar Components ---

class GearCard(BaseCard):
    """Marcha em destaque, centralizada no topo do bloco (fundida com o SpeedCard abaixo)."""
    def __init__(self):
        super(GearCard, self).__init__(margins=(6, 6, 6, 6))
        self.num_box = QFrame()
        self.num_box.setFixedHeight(84)
        self.num_box.setMinimumWidth(84)
        self.num_box.setStyleSheet("background-color: #1a1a2e; border-radius: 10px;")
        num_layout = QVBoxLayout(self.num_box)
        num_layout.setContentsMargins(0, 0, 0, 0)
        num_layout.setAlignment(Qt.AlignCenter)
        self.lbl_gear = QLabel("N")
        self.lbl_gear.setFont(QFont("Consolas", 42, QFont.Bold))
        self.lbl_gear.setAlignment(Qt.AlignCenter)
        self.lbl_gear.setStyleSheet("color: #ffffff; background: transparent; margin: 0; padding: 0;")
        num_layout.addWidget(self.lbl_gear)

        # Centraliza o box da marcha horizontalmente dentro do card
        center_row = QHBoxLayout()
        center_row.setContentsMargins(0, 0, 0, 0)
        center_row.addStretch()
        center_row.addWidget(self.num_box)
        center_row.addStretch()
        self.main_layout.addLayout(center_row)

        self._current_rpm = 0.0
        self._max_rpm = 8500.0
        
    def update_gear(self, gear: int, rpm: float = 0.0, max_rpm: float = 8500.0):
        self._current_rpm = rpm
        self._max_rpm = max_rpm
        gear_str = "R" if gear == 0 else ("N" if gear == 1 else str(gear - 1))
        self.lbl_gear.setText(gear_str)
        at_redline = rpm >= max_rpm * 0.97
        if gear_str == "R" or at_redline:
            # Red: Reverse or redline
            self.num_box.setStyleSheet("background-color: #cc0000; border-radius: 10px;")
            self.lbl_gear.setStyleSheet("color: #ffffff; background: transparent; margin: 0; padding: 0;")
        elif gear_str == "N":
            # Green: Neutral
            self.num_box.setStyleSheet("background-color: #005500; border-radius: 10px;")
            self.lbl_gear.setStyleSheet("color: #00ff88; background: transparent; margin: 0; padding: 0;")
        else:
            # Dark blue-grey: Normal gears
            self.num_box.setStyleSheet("background-color: #1a1a2e; border-radius: 10px;")
            self.lbl_gear.setStyleSheet("color: #ffffff; background: transparent; margin: 0; padding: 0;")

class SpeedCard(QFrame):
    """
    Bloco de velocidade — fica logo abaixo do GearCard (empilhados verticalmente),
    com padding generoso e alinhamento central para não estourar com valores de 3 dígitos.
    """
    def __init__(self):
        super(SpeedCard, self).__init__()
        self.setStyleSheet("background-color: #111111; border-radius: 8px;")
        self.setMinimumHeight(76)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignCenter)

        self.lbl_speed = QLabel("0")
        self.lbl_speed.setFont(QFont("Consolas", 28, QFont.Bold))
        self.lbl_speed.setAlignment(Qt.AlignCenter)
        self.lbl_speed.setStyleSheet("color: #ffffff; background: transparent; margin: 0; padding: 0;")

        lbl_unit = QLabel("km/h")
        lbl_unit.setFont(QFont("Consolas", 10))
        lbl_unit.setAlignment(Qt.AlignCenter)
        lbl_unit.setStyleSheet("color: #888888; background: transparent; margin: 0; padding: 0;")

        layout.addWidget(self.lbl_speed, alignment=Qt.AlignCenter)
        layout.addWidget(lbl_unit, alignment=Qt.AlignCenter)

    def update_speed(self, speed_kmh: int):
        self.lbl_speed.setText(str(speed_kmh))

class PedalsBarCard(BaseCard):
    def __init__(self):
        super(PedalsBarCard, self).__init__(title=None, margins=(8, 8, 8, 8))
        box = QHBoxLayout()
        box.setSpacing(10)
        
        # Acelerador (Verde)
        gas_box = QVBoxLayout()
        self.bar_gas = QProgressBar()
        self.bar_gas.setOrientation(Qt.Vertical)
        self.bar_gas.setTextVisible(False)
        self.bar_gas.setRange(0, 100)
        self.bar_gas.setStyleSheet("""
            QProgressBar { background-color: #1a1a1a; border: none; border-radius: 4px; width: 30px; }
            QProgressBar::chunk { background-color: #33ff33; border-radius: 4px; }
        """)
        lbl_gas = QLabel("GAS")
        lbl_gas.setFont(QFont("Consolas", 9, QFont.Bold))
        lbl_gas.setStyleSheet("color: #33ff33;")
        lbl_gas.setAlignment(Qt.AlignCenter)
        gas_box.addWidget(self.bar_gas)
        gas_box.addWidget(lbl_gas)
        
        # Freio (Vermelho)
        brake_box = QVBoxLayout()
        self.bar_brake = QProgressBar()
        self.bar_brake.setOrientation(Qt.Vertical)
        self.bar_brake.setTextVisible(False)
        self.bar_brake.setRange(0, 100)
        self.bar_brake.setStyleSheet("""
            QProgressBar { background-color: #1a1a1a; border: none; border-radius: 4px; width: 30px; }
            QProgressBar::chunk { background-color: #ff3333; border-radius: 4px; }
        """)
        lbl_brake = QLabel("BRK")
        lbl_brake.setFont(QFont("Consolas", 9, QFont.Bold))
        lbl_brake.setStyleSheet("color: #ff3333;")
        lbl_brake.setAlignment(Qt.AlignCenter)
        brake_box.addWidget(self.bar_brake)
        brake_box.addWidget(lbl_brake)
        
        box.addLayout(gas_box)
        box.addLayout(brake_box)
        self.main_layout.addLayout(box)
        
    def update_pedals(self, gas: float, brake: float):
        self.bar_gas.setValue(int(gas * 100))
        self.bar_brake.setValue(int(brake * 100))

class RpmCard(BaseCard):
    def __init__(self):
        super(RpmCard, self).__init__(title=None, margins=(10, 10, 10, 10))
        # Progress bar AT THE TOP (most prominent)
        self.progress = QProgressBar()
        self.progress.setFixedHeight(8)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { background-color: #1a1a1a; border: none; border-radius: 4px; }
            QProgressBar::chunk { background-color: #007acc; border-radius: 4px; }
        """)
        self.main_layout.addWidget(self.progress)
        
        # RPM value + label below
        box = QHBoxLayout()
        box.setContentsMargins(0, 4, 0, 0)
        self.lbl_rpm = QLabel("0")
        self.lbl_rpm.setFont(QFont("Consolas", 22, QFont.Bold))
        self.lbl_rpm.setStyleSheet("color: #ffffff; background: transparent;")
        lbl_unit = QLabel("RPM")
        lbl_unit.setFont(QFont("Consolas", 10))
        lbl_unit.setStyleSheet("color: #888888; background: transparent;")
        lbl_unit.setAlignment(Qt.AlignBottom)
        box.addWidget(self.lbl_rpm)
        box.addWidget(lbl_unit)
        box.addStretch()
        self.main_layout.addLayout(box)
        
    def update_rpm(self, rpm: float, max_rpm: float):
        try:
            safe_rpm = int(rpm)
            safe_max = int(max_rpm)
        except (ValueError, OverflowError):
            safe_rpm, safe_max = 0, 1
            
        safe_rpm = max(0, min(safe_rpm, 100000))
        safe_max = max(1, min(safe_max, 100000))
        
        self.lbl_rpm.setText(str(safe_rpm))
        self.progress.setRange(0, safe_max)
        self.progress.setValue(safe_rpm)
        ratio = safe_rpm / safe_max if safe_max > 0 else 0
        if ratio >= 0.97:
            color = "#cc0000"  # Red at redline
        elif ratio >= 0.85:
            color = "#ff8800"  # Orange: near limit
        elif ratio >= 0.65:
            color = "#ffdd00"  # Yellow: high
        else:
            color = "#007acc"  # Blue: normal
        self.progress.setStyleSheet(
            f"QProgressBar {{ background-color: #1a1a1a; border: none; border-radius: 4px; }}"
            f"QProgressBar::chunk {{ background-color: {color}; border-radius: 4px; }}"
        )

class CarDataCard(BaseCard):
    def __init__(self):
        super(CarDataCard, self).__init__()
        grid = QGridLayout()
        grid.setSpacing(10)
        self.lbl_fuel = self._create_value_box("Combustível", "0.0", "L")
        self.lbl_laps = self._create_value_box("Voltas est.", "0.0", "")
        self.lbl_turbo = self._create_value_box("Turbo", "0.00", "bar")
        self.lbl_steer = self._create_value_box("Volante", "0", "°")
        grid.addLayout(self.lbl_fuel, 0, 0)
        grid.addLayout(self.lbl_laps, 0, 1)
        grid.addLayout(self.lbl_turbo, 1, 0)
        grid.addLayout(self.lbl_steer, 1, 1)
        self.main_layout.addLayout(grid)

        # Fuel avg consumption row
        self.lbl_fuel_avg = QLabel("Média: -- L/volta")
        self.lbl_fuel_avg.setFont(QFont("Consolas", 9))
        self.lbl_fuel_avg.setStyleSheet("color: #aaaaaa; background: transparent;")
        self.main_layout.addWidget(self.lbl_fuel_avg)

    def _create_value_box(self, title, val, unit):
        vbox = QVBoxLayout()
        vbox.setSpacing(2)
        t = QLabel(title)
        t.setFont(QFont("Consolas", 9))
        t.setStyleSheet("color: #888888; background: transparent;")
        val_lbl = QLabel(f"{val} {unit}")
        val_lbl.setFont(QFont("Consolas", 12, QFont.Bold))
        val_lbl.setStyleSheet("color: #ffffff; background: transparent;")
        vbox.addWidget(t)
        vbox.addWidget(val_lbl)
        vbox.val_lbl = val_lbl
        vbox.unit = unit
        return vbox

    def update_data(self, fuel: float, laps: float, turbo: float, steer: float, fuel_avg: float = 0.0):
        self.lbl_fuel.val_lbl.setText(f"{fuel:.1f} {self.lbl_fuel.unit}")
        self.lbl_laps.val_lbl.setText(f"{laps:.1f} {self.lbl_laps.unit}")
        self.lbl_turbo.val_lbl.setText(f"{turbo:.2f} {self.lbl_turbo.unit}")
        self.lbl_steer.val_lbl.setText(f"{int(steer)}{self.lbl_steer.unit}")
        if fuel_avg > 0:
            self.lbl_fuel_avg.setText(f"Média: {fuel_avg:.2f} L/volta")
        else:
            self.lbl_fuel_avg.setText("Média: -- L/volta")

class TireCard(BaseCard):
    def __init__(self):
        super(TireCard, self).__init__(title="Pneus e suspensão")
        grid = QGridLayout()
        grid.setSpacing(10)
        self.t_fl = self._create_tire_box("FL")
        self.t_fr = self._create_tire_box("FR")
        self.t_rl = self._create_tire_box("RL")
        self.t_rr = self._create_tire_box("RR")
        grid.addWidget(self.t_fl, 0, 0)
        grid.addWidget(self.t_fr, 0, 1)
        grid.addWidget(self.t_rl, 1, 0)
        grid.addWidget(self.t_rr, 1, 1)
        self.main_layout.addLayout(grid)
        
    def _create_tire_box(self, label):
        frame = QFrame()
        frame.setStyleSheet("background-color: #002200; border-radius: 6px;")
        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(8, 6, 8, 6)
        vbox.setSpacing(1)
        lbl_title = QLabel(label)
        lbl_title.setFont(QFont("Consolas", 9, QFont.Bold))
        lbl_title.setStyleSheet("color: #00ff00; background: transparent;")
        lbl_temp = QLabel("80.0°C")
        lbl_temp.setFont(QFont("Consolas", 13, QFont.Bold))
        lbl_temp.setStyleSheet("color: #33ff33; background: transparent;")
        lbl_psi = QLabel("25.0 psi")
        lbl_psi.setFont(QFont("Consolas", 10))
        lbl_psi.setStyleSheet("color: #00ff33; background: transparent;")
        lbl_wear = QLabel("100%")
        lbl_wear.setFont(QFont("Consolas", 10))
        lbl_wear.setStyleSheet("color: #aaaaaa; background: transparent;")
        vbox.addWidget(lbl_title)
        vbox.addWidget(lbl_temp)
        vbox.addWidget(lbl_psi)
        vbox.addWidget(lbl_wear)
        frame.lbl_title = lbl_title
        frame.lbl_val = lbl_temp   # kept for compatibility
        frame.lbl_psi = lbl_psi
        frame.lbl_wear = lbl_wear
        return frame
        
    def update_tire(self, frame: QFrame, temp: float, pressure: float = 0.0, wear: float = 100.0):
        frame.lbl_val.setText(f"{temp:.1f}°C")
        frame.lbl_psi.setText(f"{pressure:.1f} psi")
        frame.lbl_wear.setText(f"{wear:.1f}%")
        # Wear color: green > 70%, yellow 40-70%, red < 40%
        if wear < 40:
            wear_color = "#ff4444"
        elif wear < 70:
            wear_color = "#ffaa00"
        else:
            wear_color = "#aaaaaa"
        frame.lbl_wear.setStyleSheet(f"color: {wear_color}; background: transparent;")
        if temp < 70:
            bg, fg, fg2 = "#111133", "#4444ff", "#3333cc"
        elif temp > 110:
            bg, fg, fg2 = "#331111", "#ff4444", "#cc3333"
        else:
            bg, fg, fg2 = "#003300", "#33ff33", "#00ff33"
        frame.setStyleSheet(f"background-color: {bg}; border-radius: 6px;")
        frame.lbl_title.setStyleSheet(f"color: {fg}; background: transparent;")
        frame.lbl_val.setStyleSheet(f"color: {fg}; background: transparent;")
        frame.lbl_psi.setStyleSheet(f"color: {fg2}; background: transparent;")

class AssistLED(QWidget):
    """Modern pill-style indicator badge."""
    COLORS = {
        "ABS":  {"on": "#e6b800", "text_on": "#000000"},  # Yellow
        "TC":   {"on": "#007acc", "text_on": "#ffffff"},  # Blue
        "PIT":  {"on": "#cc0000", "text_on": "#ffffff"},  # Red
    }
    
    def __init__(self, label: str):
        super().__init__()
        self._label = label
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(0)
        self.pill = QLabel(label)
        self.pill.setFont(QFont("Consolas", 10, QFont.Bold))
        self.pill.setAlignment(Qt.AlignCenter)
        self.pill.setFixedHeight(28)
        self.pill.setMinimumWidth(54)
        self._set_inactive()
        layout.addWidget(self.pill)
        layout.addStretch()

    def _set_inactive(self):
        self.pill.setStyleSheet(
            "color: #555555; background-color: #1e1e1e;"
            "border: 1px solid #333333; border-radius: 6px; padding: 0 10px;"
        )

    def set_active(self, active: bool, color: str = ""):
        if active:
            cfg = self.COLORS.get(self._label, {"on": "#00ff00", "text_on": "#000000"})
            bg  = cfg["on"]
            fg  = cfg["text_on"]
            self.pill.setStyleSheet(
                f"color: {fg}; background-color: {bg};"
                f"border: 1px solid {bg}; border-radius: 6px; padding: 0 10px;"
            )
        else:
            self._set_inactive()

class AssistsCard(BaseCard):
    def __init__(self):
        super(AssistsCard, self).__init__(title="Assistências")
        row = QHBoxLayout()
        row.setSpacing(6)
        self.led_abs = AssistLED("ABS")
        self.led_tc  = AssistLED("TC")
        self.led_pit = AssistLED("PIT")
        row.addWidget(self.led_abs)
        row.addWidget(self.led_tc)
        row.addWidget(self.led_pit)
        row.addStretch()
        self.main_layout.addLayout(row)

class GhostSelectorCard(BaseCard):
    def __init__(self):
        super(GhostSelectorCard, self).__init__(title="Referência")
        self.lbl_title.setFont(QFont("Consolas", 14, QFont.Bold))
        self.combo = QComboBox()
        self.combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.combo.setStyleSheet("""
            QComboBox {
                background-color: #222222;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 6px 10px;
                font-family: Consolas;
                font-size: 14px;
            }
            QComboBox:hover {
                border: 1px solid #666666;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #222222;
                color: #ffffff;
                border: 1px solid #444444;
                selection-background-color: #333333;
                font-family: Consolas;
                font-size: 14px;
                outline: none;
            }
        """)
        self.combo.addItems(["Desativado", "Personal Best", "Sessão Atual", "Volta Ideal"])
        self.main_layout.addWidget(self.combo)

# --- Main Area Components ---

class TopMetricCard(BaseCard):
    def __init__(self, title, initial_val, is_delta=False):
        super(TopMetricCard, self).__init__(title=title, margins=(15,10,15,10))
        self.is_delta = is_delta
        self.lbl_val = QLabel(initial_val)
        if self.is_delta:
            self.lbl_val.setFont(QFont("Consolas", 28, QFont.Bold))
        else:
            self.lbl_val.setFont(QFont("Consolas", 16, QFont.Bold))
        self.lbl_val.setStyleSheet("color: #ffffff; background: transparent;")
        self.main_layout.addWidget(self.lbl_val)
        
    def set_value(self, val_str: str, delta_val: float = 0.0):
        self.lbl_val.setText(val_str)
        if self.is_delta:
            bg = get_delta_color_bg(delta_val)
            fg = get_delta_color_text(delta_val)
            self.setStyleSheet(f"background-color: {bg}; border-radius: 8px;")
            self.lbl_val.setStyleSheet(f"color: {fg}; background: transparent;")
            self.lbl_title.setStyleSheet(f"color: {fg}; background: transparent;")

class SectorCardInner(QFrame):
    def __init__(self, title):
        super(SectorCardInner, self).__init__()
        self.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(QFont("Consolas", 10))
        self.lbl_title.setStyleSheet("color: #888888;")
        self.lbl_time = QLabel("--:--.---")
        self.lbl_time.setFont(QFont("Consolas", 18, QFont.Bold))
        self.lbl_time.setStyleSheet("color: #ffffff;")
        # Row: ref + delta side by side
        ref_row = QHBoxLayout()
        ref_row.setContentsMargins(0, 0, 0, 0)
        ref_row.setSpacing(6)
        self.lbl_ref = QLabel("Ref: --:--.---")
        self.lbl_ref.setFont(QFont("Consolas", 9))
        self.lbl_ref.setStyleSheet("color: #aaaaaa;")  # lighter for readability
        self.lbl_delta = QLabel("")
        self.lbl_delta.setFont(QFont("Consolas", 9, QFont.Bold))
        self.lbl_delta.setStyleSheet("color: #888888;")
        ref_row.addWidget(self.lbl_ref)
        ref_row.addWidget(self.lbl_delta)
        ref_row.addStretch()
        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_time)
        layout.addLayout(ref_row)
        
    def set_values(self, current_time, ref_time, color="#ffffff", delta_str=""):
        self.lbl_time.setText(current_time)
        self.lbl_time.setStyleSheet(f"color: {color};")
        if ref_time:
            self.lbl_ref.setText(f"Ref: {ref_time}")
            self.lbl_ref.show()
        else:
            self.lbl_ref.setText("")
            self.lbl_ref.hide()
        if delta_str:
            self.lbl_delta.setText(delta_str)
            # color delta green if negative (faster), red if positive (slower)
            d_color = "#00ff00" if delta_str.startswith("-") else "#ff4444"
            self.lbl_delta.setStyleSheet(f"color: {d_color};")
        else:
            self.lbl_delta.setText("")

class SectorsCard(BaseCard):
    def __init__(self):
        super(SectorsCard, self).__init__(title="Setores", margins=(15,10,15,10))
        layout = QHBoxLayout()
        self.s1 = SectorCardInner("S1")
        self.s2 = SectorCardInner("S2")
        self.s3 = SectorCardInner("S3")
        layout.addWidget(self.s1)
        layout.addWidget(self.s2)
        layout.addWidget(self.s3)
        self.main_layout.addLayout(layout)
        
    def update_sectors(self, s1: str, s2: str, s3: str, pb1: str, pb2: str, pb3: str,
                       d1: str = "", d2: str = "", d3: str = ""):
        c1 = "#ffffff" if not d1 else get_sector_color(s1, pb1, None)
        c2 = "#ffffff" if not d2 else get_sector_color(s2, pb2, None)
        c3 = "#ffffff" if not d3 else get_sector_color(s3, pb3, None)
        
        self.s1.set_values(s1, pb1, c1, d1)
        self.s2.set_values(s2, pb2, c2, d2)
        self.s3.set_values(s3, pb3, c3, d3)

class WeatherCard(QFrame):
    """Card de condições climáticas: temp. ambiente, temp. pista e chuva."""
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #151515; border-radius: 8px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        lbl_title = QLabel("Condições")
        lbl_title.setFont(QFont("Consolas", 9))
        lbl_title.setStyleSheet("color: #888888; background: transparent;")
        layout.addWidget(lbl_title)

        grid = QGridLayout()
        grid.setSpacing(4)
        grid.setContentsMargins(0, 0, 0, 0)

        self.lbl_ambient = self._make_val("Amb", "25°C")
        self.lbl_track = self._make_val("Pista", "30°C")
        self.lbl_rain = self._make_val("Chuva", "0%")
        self.lbl_wet = self._make_val("Molhado", "0%")

        grid.addWidget(self.lbl_ambient[0], 0, 0)
        grid.addWidget(self.lbl_ambient[1], 0, 1)
        grid.addWidget(self.lbl_track[0], 1, 0)
        grid.addWidget(self.lbl_track[1], 1, 1)
        grid.addWidget(self.lbl_rain[0], 2, 0)
        grid.addWidget(self.lbl_rain[1], 2, 1)
        grid.addWidget(self.lbl_wet[0], 3, 0)
        grid.addWidget(self.lbl_wet[1], 3, 1)
        layout.addLayout(grid)

    def _make_val(self, label, init):
        lbl_t = QLabel(label + ":")
        lbl_t.setFont(QFont("Consolas", 8))
        lbl_t.setStyleSheet("color: #666666; background: transparent;")
        lbl_v = QLabel(init)
        lbl_v.setFont(QFont("Consolas", 9, QFont.Bold))
        lbl_v.setStyleSheet("color: #cccccc; background: transparent;")
        lbl_v.setAlignment(Qt.AlignRight)
        return lbl_t, lbl_v

    def update_weather(self, ambient: float, track: float, rain: float, wet: float):
        self.lbl_ambient[1].setText(f"{ambient:.1f}°C")
        self.lbl_track[1].setText(f"{track:.1f}°C")
        rain_pct = rain * 100
        wet_pct = wet * 100
        self.lbl_rain[1].setText(f"{rain_pct:.0f}%")
        self.lbl_wet[1].setText(f"{wet_pct:.0f}%")
        # Color rain indicator
        if rain > 0.1:
            self.lbl_rain[1].setStyleSheet("color: #66aaff; background: transparent;")
        else:
            self.lbl_rain[1].setStyleSheet("color: #cccccc; background: transparent;")
        if wet > 0.1:
            self.lbl_wet[1].setStyleSheet("color: #44aaff; background: transparent;")
        else:
            self.lbl_wet[1].setStyleSheet("color: #cccccc; background: transparent;")


class LegendsRow(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._add_legend(layout, "#b266ff", "recorde da sessão")
        self._add_legend(layout, "#00ff00", "mais rápido que sua melhor volta")
        self._add_legend(layout, "#ff4444", "mais lento")
        layout.addStretch()
        
    def _add_legend(self, layout, color, text):
        box = QFrame()
        box.setFixedSize(8, 8)
        box.setStyleSheet(f"background-color: {color};")
        lbl = QLabel(text)
        lbl.setFont(QFont("Consolas", 9))
        lbl.setStyleSheet("color: #888888;")
        layout.addWidget(box)
        layout.addWidget(lbl)
        layout.addSpacing(15)

class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        strings = []
        for val in values:
            if val < 0:
                strings.append("")
                continue
            minutes = int(val // 60)
            seconds = int(val % 60)
            if minutes > 0:
                strings.append(f"{minutes}:{seconds:02d}")
            else:
                strings.append(f"{seconds}")
        return strings

class CustomPlot(pg.PlotWidget):
    def __init__(self, title):
        super(CustomPlot, self).__init__(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.setBackground('#151515')
        self.setTitle(title, color='#888888', size='10pt')
        self.showGrid(x=True, y=True, alpha=0.15)
        self.getAxis('left').setPen('#333333')
        self.getAxis('bottom').setPen('#333333')
        self.getAxis('left').setTextPen('#555555')
        self.getAxis('bottom').setTextPen('#888888')
        self.setMouseEnabled(x=False, y=False)
        self.hideButtons()
        self.setMenuEnabled(False)
        self.setStyleSheet("border-radius: 8px; border: none;")

class LapHistoryTable(QTableWidget):
    def __init__(self):
        super(LapHistoryTable, self).__init__(0, 6)
        self.setHorizontalHeaderLabels(["Volta", "S1", "S2", "S3", "Tempo total", "Δ Best"])
        self._best_row = -1
        self.setStyleSheet("""
            QTableWidget {
                background-color: #151515;
                color: #ffffff;
                gridline-color: #222222;
                border: none;
                border-radius: 8px;
                font-family: Consolas;
                font-size: 10pt;
            }
            QTableWidget::item {
                padding: 3px 6px;
            }
            QHeaderView::section {
                background-color: #151515;
                color: #888888;
                padding: 4px;
                border: none;
                border-bottom: 1px solid #333333;
                font-family: Consolas;
                font-size: 9pt;
                font-weight: bold;
            }
        """)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(26)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionMode(QTableWidget.NoSelection)
        self.setShowGrid(True)

    def highlight_best_lap(self, best_row: int, prev_best_row: int = -1):
        """Highlight the best lap row in green and clear the previous best."""
        # Clear previous best highlight
        if prev_best_row >= 0 and prev_best_row != best_row:
            for col in range(self.columnCount()):
                item = self.item(prev_best_row, col)
                if item:
                    item.setBackground(QColor("#151515"))
                    item.setForeground(QColor("#ffffff"))
        # Highlight new best
        if best_row >= 0:
            for col in range(self.columnCount()):
                item = self.item(best_row, col)
                if item:
                    item.setBackground(QColor("#003300"))
                    item.setForeground(QColor("#00ff88"))
