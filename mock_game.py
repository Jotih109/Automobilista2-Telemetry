"""
mock_game.py — Simulador Completo de Telemetria UDP do Automobilista 2
=======================================================================
Simula os pacotes UDP no formato Project CARS 2 que o AMS2 envia,
fielmente mapeado para os offsets que o provider atual consome.

COMO USAR:
  1. Terminal A: python mock_game.py
  2. Terminal B: python main.py
"""

import socket
import struct
import time
import math
import random

TARGET_IP    = "127.0.0.1"
TARGET_PORT  = 5606
LOOP_HZ      = 20
LOOP_SLEEP   = 1.0 / LOOP_HZ
TRACK_LENGTH = 4309.0   # Interlagos GP em metros
TOTAL_LAPS   = 8        # 0 = infinito

BASE_S1_MS  = 31500
BASE_S2_MS  = 31500
BASE_S3_MS  = 26500
BASE_LAP_MS = BASE_S1_MS + BASE_S2_MS + BASE_S3_MS  # ~89.5s

FUEL_CAPACITY = 80.0
FUEL_INITIAL  = 60.0
FUEL_PER_LAP  = 1.45   # litros/volta medio

PKT_CAR_PHYSICS     = 0
PKT_RACE_DEFINITION = 1
PKT_TIMINGS         = 3
PKT_VEHICLE_NAMES   = 6

CAR_ABS = (1 << 3)
CAR_TC  = (1 << 5)


def _pack_header(seq, pkt_type):
    return struct.pack("<IIBBBB", seq, seq, 1, 1, pkt_type, 0)


def _ms_to_laptime_str(ms):
    if ms <= 0:
        return "--:--.---"
    mins   = ms // 60000
    secs   = (ms % 60000) // 1000
    millis = ms % 1000
    return "{0}:{1:02d}.{2:03d}".format(mins, secs, millis)


GEAR_RANGES = {
    2: (  0,  78),
    3: ( 68, 118),
    4: (105, 163),
    5: (148, 213),
    6: (198, 258),
    7: (243, 315),
}


def _gear_for_speed(speed_kmh, braking=False):
    chosen = 2
    items = sorted(GEAR_RANGES.items(), key=lambda x: x[0], reverse=braking)
    for g, (vmin, vmax) in items:
        if vmin <= speed_kmh <= vmax:
            chosen = g
            break
    else:
        if speed_kmh > 260:
            chosen = 7
    vmin, vmax = GEAR_RANGES.get(chosen, (240, 310))
    ratio = max(0.0, min(1.0, (speed_kmh - vmin) / max(1, vmax - vmin)))
    rpm = 4200 + ratio * 4100 + random.randint(-50, 50)
    return chosen, rpm


def _track_profile(p):
    """Perfil de pista Interlagos: 8 zonas."""
    noise  = random.gauss(0, 0.012)
    snoise = random.uniform(-1.2, 1.2)

    if p < 0.15:
        t = p / 0.15
        gas   = min(1.0, 0.9 + noise)
        brake = 0.0
        speed = 130 + t * 150 + snoise
        steer = random.uniform(-0.01, 0.01)
    elif p < 0.22:
        t = (p - 0.15) / 0.07
        gas   = 0.0
        brake = min(1.0, t * 3.5 + noise)
        speed = 280 - t * 180 + snoise
        steer = math.sin(t * math.pi) * 0.45 + noise
    elif p < 0.38:
        t = (p - 0.22) / 0.16
        gas   = max(0.05, 0.25 + t * 0.5 + noise)
        brake = max(0.0, 0.15 - t * 0.15 + noise)
        speed = 100 + t * 80 + snoise
        steer = math.sin(t * math.pi * 2) * 0.4 + noise
    elif p < 0.50:
        t = (p - 0.38) / 0.12
        gas   = min(1.0, 0.7 + t * 0.3 + noise)
        brake = 0.0
        speed = 180 + t * 80 + snoise
        steer = random.uniform(-0.02, 0.02)
    elif p < 0.60:
        t = (p - 0.50) / 0.10
        gas   = 0.0
        brake = min(1.0, t * 2.5 + noise)
        speed = 260 - t * 150 + snoise
        steer = math.sin(t * math.pi) * 0.35 + noise
    elif p < 0.75:
        t = (p - 0.60) / 0.15
        gas   = max(0.2, 0.4 + t * 0.6 + noise)
        brake = max(0.0, 0.1 - t * 0.1)
        speed = 110 + t * 130 + snoise
        steer = math.sin(t * math.pi * 1.5) * 0.3 + noise
    elif p < 0.88:
        t = (p - 0.75) / 0.13
        if t < 0.4:
            s     = t / 0.4
            gas   = max(0.0, 0.1 + noise)
            brake = max(0.0, 0.7 - s * 0.5 + noise)
            speed = 240 - s * 100 + snoise
        else:
            s     = (t - 0.4) / 0.6
            gas   = max(0.1, 0.2 + s * 0.7 + noise)
            brake = 0.0
            speed = 140 + s * 70 + snoise
        steer = math.sin(t * math.pi * 2) * 0.45 + noise
    else:
        t = (p - 0.88) / 0.12
        gas   = min(1.0, 0.6 + t * 0.4 + noise)
        brake = max(0.0, 0.05 - t * 0.05)
        speed = 160 + t * 100 + snoise
        steer = random.uniform(-0.03, 0.03)

    return (
        max(0.0, min(1.0, gas)),
        max(0.0, min(1.0, brake)),
        max(20.0, min(310.0, speed)),
        steer,
    )


def build_car_physics_packet(seq, lap_progress, fuel_level):
    """
    PKT_CAR_PHYSICS — 559 bytes total (header 12 + payload 547).
    Offsets (absolutos no pacote):
      [15] unfilteredThrottle uint8
      [16] unfilteredBrake    uint8
      [17] unfilteredSteering int8
      [18] unfilteredClutch   uint8
      [19] carFlags           uint8
      [30] fuelCapacity       uint8
      [32] fuelLevel          float (0..1)
      [36] speed              float (m/s)
      [40] engineRPM          uint16
      [42] maxRPM             uint16
      [44] steeringAngle      int8
      [45] gearNumGears       uint8 (hi nibble=numGears, lo nibble=gear)
      [200+i] tyreWear[4]     uint8
      [220+i*2] tyreTreadTemp[4] uint16 (Kelvin)
      [332+i*4] suspensionTravel[4] float (metros)
      [364+i*2] airPressure[4] uint16
    """
    HDR = 12
    PKT = 559
    header  = _pack_header(seq, PKT_CAR_PHYSICS)
    payload = bytearray(PKT - HDR)

    gas, brake, speed_kmh, steering = _track_profile(lap_progress)
    gear_raw, rpm = _gear_for_speed(speed_kmh, braking=(brake > 0.2))
    speed_ms = speed_kmh / 3.6

    car_flags = 0
    if brake > 0.85:               car_flags |= CAR_ABS
    if gas > 0.90 and gear_raw<=3: car_flags |= CAR_TC

    base_temp  = 78.0 + brake * 16.0 + gas * 5.0
    tyre_temps = [base_temp + 273.15 + i * 0.5 + random.uniform(-0.3, 0.3) for i in range(4)]
    tyre_psi   = [int((28.0 + brake * 0.9) * 100) for _ in range(4)]
    suspension = [0.05 + math.sin(seq * 0.3 + i) * 0.003 for i in range(4)]

    def su8(o, v):  payload[o-HDR] = max(0, min(255, int(v))) & 0xFF
    def si8(o, v):  payload[o-HDR] = struct.pack("<b", max(-128, min(127, int(v))))[0]
    def su16(o, v): payload[o-HDR:o-HDR+2] = struct.pack("<H", max(0, min(65535, int(v))))
    def sf32(o, v): payload[o-HDR:o-HDR+4] = struct.pack("<f", float(v))

    su8(15,  gas * 255)
    su8(16,  brake * 255)
    si8(17,  steering * 127)
    su8(18,  0)
    su8(19,  car_flags)
    su8(30,  int(FUEL_CAPACITY))
    sf32(32, max(0.0, min(1.0, fuel_level / FUEL_CAPACITY)))
    sf32(36, speed_ms)
    su16(40, int(rpm))
    su16(42, 8500)
    si8(44,  steering * 127)
    su8(45,  (6 << 4) | (gear_raw & 0x0F))

    for i in range(4):
        su8(200 + i, 255)
        su16(220 + i * 2, int(tyre_temps[i]))
        sf32(332 + i * 4, suspension[i])
        su16(364 + i * 2, tyre_psi[i])

    return header + bytes(payload)


def build_timings_packet(seq, lap_ms, lap_dist_m, delta_s, sector_idx, lap_number):
    """
    PKT_TIMINGS — Header (12) + Prefix (33) + Participant[0] (32).

    Offsets absolutos:
      Prefix:
        [29] mSplitTime (float) = delta em segundos   → prefix[17]
      Participant (base = 33):
        [b+12] sCurrentLapDistance  uint16 metros
        [b+15] sSector              uint8  (bits 0-2: 1=S1, 2=S2, 3=S3)
        [b+21] sCurrentLap          uint8
        [b+22] sCurrentTime         float  segundos
    """
    header = _pack_header(seq, PKT_TIMINGS)
    prefix = bytearray(33)
    struct.pack_into("<f", prefix, 17, float(delta_s))   # offset 29 no pacote

    part = bytearray(32)
    dist16 = max(0, min(65535, int(lap_dist_m)))
    struct.pack_into("<H", part, 12, dist16)
    part[15] = int(sector_idx) & 0x07
    part[21] = max(0, lap_number - 1) & 0x7F
    struct.pack_into("<f", part, 22, lap_ms / 1000.0)

    return header + bytes(prefix) + bytes(part)


def build_time_stats_packet(seq, best_ms, last_ms, last_sector_s):
    """
    PKT_TIME_STATS (7)
    Header (12) + mParticipantsChangedTimestamp (4) + ParticipantStats (30)
    [b+0] mFastestLapTime (float)
    [b+4] mLastLapTime (float)
    [b+8] mLastSectorTime (float)
    """
    header = _pack_header(seq, 7)
    prefix = struct.pack("<I", 0) # mParticipantsChangedTimestamp
    
    part = bytearray(30)
    struct.pack_into("<f", part, 0, best_ms / 1000.0 if best_ms > 0 else -1.0)
    struct.pack_into("<f", part, 4, last_ms / 1000.0 if last_ms > 0 else -1.0)
    struct.pack_into("<f", part, 8, float(last_sector_s))
    
    return header + prefix + bytes(part)


def build_race_definition_packet(seq):
    header = _pack_header(seq, PKT_RACE_DEFINITION)
    tl = b"Autodromo Jose Carlos Pace\x00"
    tv = b"Grand Prix\x00"
    payload = struct.pack(
        "<I I fff H H B B B f f f f f f f 128s 64s 64s h b",
        seq, 0, 0.0, 0.0, 0.0, 0, 0, 5, 1, 1,
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        tl.ljust(128, b"\x00"),
        tv.ljust(64, b"\x00"),
        tv.ljust(64, b"\x00"),
        10, -1,
    )
    return header + payload


def build_vehicle_names_packet(seq):
    header = _pack_header(seq, PKT_VEHICLE_NAMES)
    return header + struct.pack("B", 1) + b"Porsche 992 GT3 Cup\x00".ljust(64, b"\x00")


def run_mock_ams2():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = (TARGET_IP, TARGET_PORT)

    sep = "=" * 62
    print(sep)
    print("  AMS2 Mock Telemetry v3 | Interlagos | Porsche 992 GT3 Cup")
    print(sep)
    print("  S1={0:.1f}s | S2={1:.1f}s | S3={2:.1f}s | Volta~{3:.1f}s".format(
        BASE_S1_MS/1000, BASE_S2_MS/1000, BASE_S3_MS/1000, BASE_LAP_MS/1000))
    print("  Combustivel inicial: {0:.1f}L | Consumo: ~{1:.2f}L/volta".format(
        FUEL_INITIAL, FUEL_PER_LAP))
    print("  Voltas: {0}".format(TOTAL_LAPS if TOTAL_LAPS > 0 else "infinitas"))
    print(sep)
    print("  >> Terminal A: python mock_game.py")
    print("  >> Terminal B: python main.py")
    print(sep + "\n")

    seq         = 0
    lap_ms      = 0
    last_ms     = 0
    best_ms     = 0
    lap_number  = 1

    s1_locked    = 0
    s2_locked    = 0
    s3_locked    = 0
    sector_proto = 0    # 0=S1, 1=S2, 2=S3 (protocolo AMS2)
    last_sector_s = 0.0

    fuel = FUEL_INITIAL

    lap_var      = random.randint(-300, 400)
    lap_target   = BASE_LAP_MS + lap_var
    s1_end       = BASE_S1_MS + random.randint(-200, 200)
    s2_end       = BASE_S1_MS + BASE_S2_MS + random.randint(-200, 200)
    ref_best     = BASE_LAP_MS

    meta = 0

    try:
        while True:
            tick  = int(LOOP_SLEEP * 1000)
            lap_ms += tick
            prog  = min(1.0, lap_ms / lap_target)
            dist  = prog * TRACK_LENGTH

            # ── Setores ─────────────────────────────────────────────────────
            if s1_locked == 0 and lap_ms >= s1_end:
                s1_locked     = lap_ms
                last_sector_s = s1_locked / 1000.0
                sector_proto  = 1
                print("  [V{0}] S1 fechado: {1}".format(lap_number, _ms_to_laptime_str(s1_locked)))

            elif s2_locked == 0 and s1_locked > 0 and lap_ms >= s2_end:
                s2_locked     = lap_ms - s1_locked
                last_sector_s = s2_locked / 1000.0
                sector_proto  = 2
                print("  [V{0}] S2 fechado: {1}".format(lap_number, _ms_to_laptime_str(s2_locked)))

            # ── Delta ────────────────────────────────────────────────────────
            ref_t = (prog * ref_best) / 1000.0
            curr  = lap_ms / 1000.0
            delta = curr - ref_t + math.sin(prog * math.pi * 6) * 0.05 + random.uniform(-0.03, 0.03)

            # ── Fim de Volta ─────────────────────────────────────────────────
            if lap_ms >= lap_target:
                last_ms   = lap_ms
                s3_locked = last_ms - (s1_locked + s2_locked) if s2_locked > 0 else 0
                last_sector_s = s3_locked / 1000.0
                sector_proto  = 0

                if best_ms == 0 or last_ms < best_ms:
                    best_ms  = last_ms
                    ref_best = best_ms
                    print("  [V{0}] BEST: {1}".format(lap_number, _ms_to_laptime_str(best_ms)))
                else:
                    print("  [V{0}] Fim: {1}  (best {2})".format(
                        lap_number, _ms_to_laptime_str(last_ms), _ms_to_laptime_str(best_ms)))

                fuel = max(0.0, fuel - FUEL_PER_LAP + random.uniform(-0.05, 0.05))
                print("  [V{0}] Combustivel: {1:.2f}L".format(lap_number, fuel))

                lap_number += 1
                lap_ms = 0
                s1_locked = s2_locked = s3_locked = 0
                lap_var    = random.randint(-300, 400)
                lap_target = BASE_LAP_MS + lap_var
                s1_end     = BASE_S1_MS + random.randint(-150, 150)
                s2_end     = BASE_S1_MS + BASE_S2_MS + random.randint(-150, 150)

                if TOTAL_LAPS > 0 and lap_number > TOTAL_LAPS:
                    print("\n  Simulacao concluida ({0} voltas).".format(TOTAL_LAPS))
                    break

            # ── Envio ────────────────────────────────────────────────────────
            sock.sendto(build_car_physics_packet(seq, prog, fuel), dest)
            sock.sendto(build_timings_packet(
                seq           = seq,
                lap_ms        = lap_ms,
                lap_dist_m    = dist,
                delta_s       = delta,
                sector_idx    = sector_proto,
                lap_number    = lap_number
            ), dest)
            
            sock.sendto(build_time_stats_packet(
                seq           = seq,
                best_ms       = best_ms,
                last_ms       = last_ms,
                last_sector_s = last_sector_s
            ), dest)

            if meta % LOOP_HZ == 0:
                sock.sendto(build_race_definition_packet(seq), dest)
                sock.sendto(build_vehicle_names_packet(seq), dest)

            seq  += 1
            meta += 1
            time.sleep(LOOP_SLEEP)

    except KeyboardInterrupt:
        print("\n  Simulador encerrado.")
    finally:
        sock.close()


if __name__ == "__main__":
    run_mock_ams2()
