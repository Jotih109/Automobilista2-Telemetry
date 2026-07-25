import dataclasses
from typing import List

@dataclasses.dataclass
class TelemetryState:
    """
    Representação padronizada do estado atual do carro e da sessão.

    O AMS2TelemetryProvider lê os pacotes UDP do Automobilista 2
    (protocolo pCars2) e mapeia todos os valores para este dataclass.
    A Interface Gráfica e a Engine de análises consomem apenas este
    formato, sendo completamente independentes do protocolo de rede.
    """

    # --- Status da Conexão ---
    is_connected: bool = False
    car_name: str = "Unknown Car"
    track_name: str = "Unknown Track"

    # --- Entradas do Piloto (0.0 a 1.0) ---
    gas: float = 0.0
    brake: float = 0.0
    clutch: float = 0.0
    steer_angle: float = 0.0  # Graus

    # --- Motor e Transmissão ---
    speed_kmh: float = 0.0
    rpm: int = 0
    max_rpm: float = 8500.0  # RPM Máximo (ex: 8500 no Porsche Cup)
    gear: int = 0            # 0=Ré, 1=Neutro, 2=1ª, 3=2ª ...
    turbo_boost: float = 0.0 # bar

    # --- Tempos e Posição ---
    current_time: str = ""   # Tempo da volta atual (m:ss.mmm)
    last_time: str = ""      # Tempo da última volta
    best_time: str = ""      # Melhor volta pessoal na sessão
    sector_index: int = 0    # Setor atual (0, 1 ou 2)
    last_sector_time: int = 0  # Tempo do último setor (ms)
    s1_time: str = "--:--"    # Tempo formatado do Setor 1
    s2_time: str = "--:--"    # Tempo formatado do Setor 2
    s3_time: str = "--:--"    # Tempo formatado do Setor 3

    # Personal Best sectors (real)
    pb_s1: str = "--:--"
    pb_s2: str = "--:--"
    pb_s3: str = "--:--"

    s1_delta: float = 0.0    # Delta S1 vs referência
    s2_delta: float = 0.0    # Delta S2 vs referência
    s3_delta: float = 0.0    # Delta S3 vs referência
    lap_number: int = 0      # Número da volta atual
    delta_time: float = 0.0  # Segundos vs referência (+pior / -melhor)
    track_position: float = 0.0  # Progresso na pista (0.0 a 1.0)
    distance_traveled: float = 0.0  # Metros percorridos
    track_length: float = 4309.0  # Comprimento da pista em metros

    # --- Eletrônica e Sistemas ---
    abs_active: bool = False
    tc_active: bool = False
    pit_limiter: bool = False

    # --- Condições Climáticas (AMS2 tem clima dinâmico) ---
    ambient_temp: float = 25.0
    track_temp: float = 30.0
    rain_density: float = 0.0    # 0.0 (seco) a 1.0 (tempestade)
    track_wetness: float = 0.0   # 0.0 (seco) a 1.0 (molhado)

    # --- Danos ---
    car_damage: float = 0.0  # 0 a 100% (média geral dos danos)

    # --- Combustível e Pneus Gerais ---
    fuel: float = 0.0               # Litros restantes
    fuel_avg_consumption: float = 0.0  # Litros por volta (calculado pela engine)
    fuel_laps_remaining: float = 0.0   # Voltas estimadas com o combustível atual
    tyre_compound: str = ""

    # --- Dinâmica 4 Rodas [FL, FR, RL, RR] ---
    tyre_temp: List[float] = dataclasses.field(default_factory=lambda: [80.0] * 4)
    tyre_pressure: List[float] = dataclasses.field(default_factory=lambda: [25.0] * 4)
    tyre_wear: List[float] = dataclasses.field(default_factory=lambda: [100.0] * 4)
    tyre_slip: List[float] = dataclasses.field(default_factory=lambda: [0.0] * 4)
    suspension_travel: List[float] = dataclasses.field(default_factory=lambda: [0.0] * 4)
