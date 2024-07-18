import fastf1
import pandas as pd
import json
import time

# Zaman ölçümleri için liste
timing_info = []

def log_time(start, description):
    end = time.time()
    duration = end - start
    timing_info.append((description, duration))
    return end

# FastF1'i initialize et ve cache directory'sini ayarla
start_time = time.time()
fastf1.Cache.enable_cache('f1cache')
end_time = log_time(start_time, 'Cache enable')

# Silverstone yarışını yükle (2021 sezonu, yarış kodu 10)
start_time = end_time
session = fastf1.get_session(2021, 'Silverstone', 'R')
end_time = log_time(start_time, 'Get session')

# Verileri yükle
start_time = end_time
session.load()
end_time = log_time(start_time, 'Load session data')

drivers = session.drivers

# Hamilton'ın turlarını seç
start_time = end_time
car_data = session.laps.pick_driver('HAM').get_car_data()
pos_data = session.laps.pick_driver('HAM').get_pos_data()
laps = session.laps.pick_driver('HAM')
driver_info = session.get_driver('HAM')
end_time = log_time(start_time, 'Select Hamilton\'s laps')

# Telemetri verilerini elde et ve total_seconds formatına çevir
start_time = end_time
car_data['SessionTime (s)'] = car_data['SessionTime'].dt.total_seconds()
pos_data['SessionTime (s)'] = pos_data['SessionTime'].dt.total_seconds()
end_time = log_time(start_time, 'Convert telemetry data to seconds')

# Her turun başlangıç ve bitiş zamanlarını hesapla
start_time = end_time
laps_info = []

previous_lap_end_time = None

for i, lap in laps.iterlaps():
    lap_number = lap['LapNumber']

    try:
        
        lap_duration = lap['LapTime'].total_seconds() if not pd.isnull(lap['LapTime']) else None
    except IndexError:
        lap_duration = None

    if lap_duration is None:
        # Use telemetry data to calculate lap duration if LapTime is missing
        telemetry_data = laps.pick_lap(lap_number).get_car_data()
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

    session_start_time = session.session_start_time.total_seconds()
    lap_time = lap['Time'].total_seconds()

    if lap_number == 1:
        lap_start_time = session_start_time
        lap_end_time = session_start_time + lap_duration
    else:
        lap_start_time = previous_lap_end_time
        lap_end_time = lap_start_time + lap_duration

    previous_lap_end_time = lap_end_time

    lap_info = {
        'LapNumber': lap_number,
        'LapStartTime': lap_start_time,
        'LapEndTime': lap_end_time,
        'LapDuration': lap_duration
    }
    laps_info.append(lap_info)

end_time = log_time(start_time, 'Calculate lap start and end times')

# Telemetri verilerini laplere böl
start_time = end_time
def get_telemetry_for_lap(lap_start_time, lap_end_time):
    lap_telemetry_car = car_data[(car_data['SessionTime (s)'] >= lap_start_time) & (car_data['SessionTime (s)'] < lap_end_time)]
    lap_telemetry_pos = pos_data[(pos_data['SessionTime (s)'] >= lap_start_time) & (pos_data['SessionTime (s)'] < lap_end_time)]
    return lap_telemetry_car, lap_telemetry_pos

for lap in laps_info:
    lap_telemetry_car, lap_telemetry_pos = get_telemetry_for_lap(lap['LapStartTime'], lap['LapEndTime'])
    lap['Telemetry'] = {
        'X': lap_telemetry_pos['X'].values.tolist(),
        'Y': lap_telemetry_pos['Y'].values.tolist(),
        'Speed': lap_telemetry_car['Speed'].values.tolist(),
        'Brake': lap_telemetry_car['Brake'].values.tolist(),
        'RPM': lap_telemetry_car['RPM'].values.tolist(),
        'SessionTime (s)': lap_telemetry_car['SessionTime (s)'].values.tolist()
    }

end_time = log_time(start_time, 'Divide telemetry data into laps')

result = {
    "HAM" : laps_info
}

# JSON dosyasına kaydetme
start_time = end_time
with open('all_telemetry.json', 'w') as json_file:
    json.dump(result, json_file, indent=4)
end_time = log_time(start_time, 'Save to JSON file')

# Zamanlama bilgilerini yazdırma
for description, duration in timing_info:
    print(f'{description}: {duration:.2f} seconds')
