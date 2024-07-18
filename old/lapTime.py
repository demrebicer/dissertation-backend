import fastf1
import pandas as pd
import json

# FastF1'i initialize et ve cache directory'sini ayarla
fastf1.Cache.enable_cache('f1cache')

# Silverstone yarışını yükle (2021 sezonu, yarış kodu 10)
session = fastf1.get_session(2021, 'Silverstone', 'R')

# Verileri yükle
session.load(laps=True, telemetry=True)

# Hamilton'ın turlarını seç
laps = session.laps.pick_driver('HAM')

# Her turun başlangıç ve bitiş zamanlarını hesapla
laps_info = []

for i in range(len(laps) - 1):
    lap = laps.iloc[i]
    next_lap = laps.iloc[i + 1]
    
    lap_number = lap['LapNumber']
    
    try:
        lap_duration = lap['LapTime'].total_seconds() if not pd.isnull(lap['LapTime']) else None
    except IndexError:
        lap_duration = None

    if lap_duration is None:
        # Use telemetry data to calculate lap duration if LapTime is missing
        telemetry_data = laps.pick_lap(lap_number).get_telemetry()
        if not telemetry_data.empty:
            lap_start_time = telemetry_data.iloc[0]['Time']
            lap_end_time = telemetry_data.iloc[-1]['Time']
            lap_duration = (lap_end_time - lap_start_time).total_seconds()
        else:
            # Fallback: Estimate lap duration using the average of surrounding laps
            previous_laps = laps.iloc[max(0, lap_number - 5):lap_number - 1]
            next_laps = laps.iloc[lap_number:min(lap_number + 5, len(laps))]
            surrounding_laps = pd.concat([previous_laps, next_laps])
            estimated_duration = surrounding_laps['LapTime'].mean().total_seconds() if not surrounding_laps['LapTime'].isnull().all() else 30
            lap_duration = estimated_duration

    lap_start_time = lap['Time'].total_seconds()
    next_lap_start_time = next_lap['Time'].total_seconds()
    lap_end_time = next_lap_start_time

    lap_info = {
        'LapNumber': lap_number,
        'LapStartTime': lap_start_time,
        'LapEndTime': lap_end_time,
        'LapDuration': lap_duration
    }
    laps_info.append(lap_info)

# Last lap
last_lap = laps.iloc[-1]
lap_number = last_lap['LapNumber']
lap_start_time = last_lap['Time'].total_seconds()

try:
    lap_duration = last_lap['LapTime'].total_seconds() if not pd.isnull(last_lap['LapTime']) else None
except IndexError:
    lap_duration = None

if lap_duration is None:
    telemetry_data = laps.pick_lap(lap_number).get_telemetry()
    if not telemetry_data.empty:
        lap_start_time = telemetry_data.iloc[0]['Time']
        lap_end_time = telemetry_data.iloc[-1]['Time']
        lap_duration = (lap_end_time - lap_start_time).total_seconds()
    else:
        previous_laps = laps.iloc[max(0, lap_number - 5):lap_number - 1]
        surrounding_laps = previous_laps
        estimated_duration = surrounding_laps['LapTime'].mean().total_seconds() if not surrounding_laps['LapTime'].isnull().all() else 30
        lap_duration = estimated_duration

lap_end_time = lap_start_time + lap_duration

lap_info = {
    'LapNumber': lap_number,
    'LapStartTime': lap_start_time,
    'LapEndTime': lap_end_time,
    'LapDuration': lap_duration
}
laps_info.append(lap_info)

# JSON formatına çevir
laps_json = json.dumps(laps_info, indent=4)

print(laps_json)
