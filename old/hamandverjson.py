import fastf1
import pandas as pd
import json
import time
from constants import *

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

def get_scale_factor(global_min_x, global_max_x, global_min_y, global_max_y):
    range_x = global_max_x - global_min_x
    range_y = global_max_y - global_min_y
    max_range = max(range_x, range_y)
    scale_factor = 177.5 / max_range
    return scale_factor

# Function to adjust coordinates with a common reference point and global scaling
def adjust_coordinates(x_coordinates, y_coordinates, ref_x, ref_y, scale_factor):
    adjusted_points = [
        [((x - ref_x) * scale_factor), 
         0, 
         ((y - ref_y) * scale_factor)]
        for x, y in zip(x_coordinates, y_coordinates)
    ]
    
    return adjusted_points

scale_factor = get_scale_factor(PREDEFINED_GLOBAL_MIN_X, PREDEFINED_GLOBAL_MAX_X, PREDEFINED_GLOBAL_MIN_Y, PREDEFINED_GLOBAL_MAX_Y)
ref_x, ref_y = REFERENCE_X[0], REFERENCE_Y[0]

def process_driver_data(driver_code): 
    start_time = time.time()
    laps = session.laps.pick_driver(driver_code)
    # telemetry = laps.get_telemetry()

    car_data = laps.get_car_data()
    pos_data = laps.get_pos_data()

    # Her iki veri çerçevesinin de SessionTime sütunlarının sıralı olduğundan emin olun
    pos_data = pos_data.sort_values(by='SessionTime')
    car_data = car_data.sort_values(by='SessionTime')

    # merge_asof kullanarak en yakın eşleşmeyi bul ve birleştir
    telemetry = pd.merge_asof(pos_data, car_data, on='SessionTime', direction='nearest')

    end_time = log_time(start_time, f'Process {driver_code} telemetry data')

    # Convert SessionTime to total seconds
    start_time = end_time
    telemetry['SessionTime (s)'] = telemetry['SessionTime'].dt.total_seconds()
    end_time = log_time(start_time, 'Convert telemetry data to seconds')

    # Koordinatları ayarla
    start_time = end_time
    x_values = telemetry['X'].values
    y_values = telemetry['Y'].values

    adjusted_points = adjust_coordinates(
        x_values, 
        y_values, 
        ref_x, 
        ref_y, 
        scale_factor
    )
    telemetry['AdjustedCoordinates'] = list(adjusted_points)

    end_time = log_time(start_time, 'Adjust coordinates')

    # Her bir zaman damgası için koordinatları içeren listeyi oluştur
    start_time = end_time
    telemetry.rename(columns={
        'SessionTime (s)': 'timestamp',
        'AdjustedCoordinates': 'coordinates'
    }, inplace=True)

    # Sadece gerekli kolonları seçip listeye dönüştürme
    formatted_telemetry_list = telemetry[['timestamp', 'coordinates', 'Brake', 'RPM']].to_dict('records')


    end_time = log_time(start_time, 'Create telemetry data list')
    
    return formatted_telemetry_list

# Hamilton ve Verstappen için verileri işle
start_time = time.time()
hamilton_data = process_driver_data('HAM')
# verstappen_data = process_driver_data('VER')
end_time = log_time(start_time, 'Process data for Hamilton')

result = {
    "cars": [
        {
            "id": "HAM",
            "path": hamilton_data
        },
        # {
        #     "id": "VER",
        #     "path": verstappen_data
        # }
    ]
}

# JSON dosyasına kaydetme
start_time = end_time
with open('hamilton_verstappen_telemetry.json', 'w') as json_file:
    json.dump(result, json_file, indent=4)
end_time = log_time(start_time, 'Save to JSON file')

# Zamanlama bilgilerini yazdırma
for description, duration in timing_info:
    print(f'{description}: {duration:.2f} seconds')
