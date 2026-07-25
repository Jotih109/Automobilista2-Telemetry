from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from core.models import TelemetryState
from ui.components import GearCard, SpeedCard, RpmCard, CarDataCard, TireCard, AssistsCard, GhostSelectorCard, WeatherCard

class SidebarPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(240)
        self.setStyleSheet("background-color: #0a0a0a; border: none;")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # --- Status de Conexão ---
        conn_row = QHBoxLayout()
        conn_row.setSpacing(6)
        self._conn_dot = QLabel("●")
        self._conn_dot.setFont(QFont("Consolas", 12, QFont.Bold))
        self._conn_dot.setStyleSheet("color: #ff4444; background: transparent;")
        self._conn_label = QLabel("Desconectado")
        self._conn_label.setFont(QFont("Consolas", 9))
        self._conn_label.setStyleSheet("color: #666666; background: transparent;")
        conn_row.addWidget(self._conn_dot)
        conn_row.addWidget(self._conn_label)
        conn_row.addStretch()
        main_layout.addLayout(conn_row)

        # --- Pista / Carro ---
        self._lbl_track = QLabel("Pista: --")
        self._lbl_track.setFont(QFont("Consolas", 8))
        self._lbl_track.setStyleSheet("color: #888888; background: transparent;")
        self._lbl_track.setWordWrap(True)
        self._lbl_car = QLabel("Carro: --")
        self._lbl_car.setFont(QFont("Consolas", 8))
        self._lbl_car.setStyleSheet("color: #888888; background: transparent;")
        self._lbl_car.setWordWrap(True)
        main_layout.addWidget(self._lbl_track)
        main_layout.addWidget(self._lbl_car)

        # Instantiate Components
        from ui.components import PedalsBarCard
        self.pedals_bar_card = PedalsBarCard()
        self.gear_card = GearCard()
        self.speed_card = SpeedCard()
        self.rpm_card = RpmCard()
        self.car_data_card = CarDataCard()
        self.tire_card = TireCard()
        self.assists_card = AssistsCard()
        self.ghost_selector = GhostSelectorCard()
        self.weather_card = WeatherCard()
        
        # RPM first (top of sidebar)
        main_layout.addWidget(self.rpm_card)

        # Marcha + Velocidade empilhados, pedais ao lado
        gear_speed_col = QVBoxLayout()
        gear_speed_col.setSpacing(8)
        gear_speed_col.addWidget(self.gear_card)
        gear_speed_col.addWidget(self.speed_card)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        top_row.addWidget(self.pedals_bar_card)
        top_row.addLayout(gear_speed_col, stretch=1)
        main_layout.addLayout(top_row)
        
        main_layout.addWidget(self.car_data_card)
        main_layout.addWidget(self.tire_card)
        main_layout.addWidget(self.weather_card)
        main_layout.addWidget(self.assists_card)
        main_layout.addWidget(self.ghost_selector)
        
        main_layout.addStretch()

    def update_panel(self, state: TelemetryState):
        if not state.is_connected:
            self._conn_dot.setStyleSheet("color: #ff4444; background: transparent;")
            self._conn_label.setText("Desconectado")
            return

        # Status conexão
        self._conn_dot.setStyleSheet("color: #00ff88; background: transparent;")
        self._conn_label.setText("Conectado")

        # Pista / Carro
        self._lbl_track.setText(f"Pista: {state.track_name}")
        self._lbl_car.setText(f"Carro: {state.car_name}")

        # Update Gear and Speed Cards (pass rpm for dynamic color)
        max_rpm = getattr(state, 'max_rpm', 8500.0)
        self.pedals_bar_card.update_pedals(state.gas, state.brake)
        self.gear_card.update_gear(state.gear, state.rpm, max_rpm)
        self.speed_card.update_speed(int(state.speed_kmh))
        
        # Update RPM Card
        self.rpm_card.update_rpm(state.rpm, max_rpm)
        
        # Update Car Data
        self.car_data_card.update_data(
            fuel=state.fuel,
            laps=state.fuel_laps_remaining,
            turbo=state.turbo_boost,
            steer=state.steer_angle,
            fuel_avg=getattr(state, '_fuel_avg', 0.0)
        )
        
        # Update Tires (with wear)
        self.tire_card.update_tire(self.tire_card.t_fl, state.tyre_temp[0], state.tyre_pressure[0], state.tyre_wear[0])
        self.tire_card.update_tire(self.tire_card.t_fr, state.tyre_temp[1], state.tyre_pressure[1], state.tyre_wear[1])
        self.tire_card.update_tire(self.tire_card.t_rl, state.tyre_temp[2], state.tyre_pressure[2], state.tyre_wear[2])
        self.tire_card.update_tire(self.tire_card.t_rr, state.tyre_temp[3], state.tyre_pressure[3], state.tyre_wear[3])
        
        # Update Weather
        self.weather_card.update_weather(
            ambient=state.ambient_temp,
            track=state.track_temp,
            rain=state.rain_density,
            wet=state.track_wetness
        )

        # Update Assists — using real state values
        self.assists_card.led_abs.set_active(state.abs_active)
        self.assists_card.led_tc.set_active(state.tc_active)
        self.assists_card.led_pit.set_active(state.pit_limiter)

