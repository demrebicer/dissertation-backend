import fastf1
import pandas as pd

import fastf1.api

# FastF1'i initialize et ve cache directory'sini ayarla
fastf1.Cache.enable_cache('f1cache')

# Silverstone yarışını yükle (2021 sezonu, yarış kodu 10)
session = fastf1.get_session(2021, 'Silverstone', 'R')

# Verileri yükle
session.load()

session_drivers = session.drivers

print(session.session_start_time)

# print(session.drivers)

# print(session.get_driver('33'))

#Create json like enum for driver numbers and Abbreviation
#{'44': 'HAM', '16': 'LEC', '77': 'BOT', '4': 'NOR', '3': 'RIC', '55': 'SAI', '14': 'ALO', '18': 'STR', '31': 'OCO', '22': 'TSU', '10': 'GAS', '63': 'RUS', '99': 'GIO', '6': 'LAT', '7': 'RAI', '11': 'PER', '9': 'MAZ', '47': 'MSC', '5': 'VET', '33': 'VER'}
driver_enum = {}

for driver in session.drivers:
    driver_enum[driver] = session.get_driver(driver).Abbreviation


# Timing data'yı al
laps_data, stream_data = fastf1.api.timing_data(session.api_path)

# Sürücü numaralarından oluşan set
laps_drivers = set(laps_data['Driver'].unique())
stream_drivers = set(stream_data['Driver'].unique())

# Session sürücülerinin verisi olmayanları kontrol et
laps_missing_drivers = set(session_drivers) - laps_drivers
stream_missing_drivers = set(session_drivers) - stream_drivers

# print("Laps data missing drivers:", laps_missing_drivers)
# print("Stream data missing drivers:", stream_missing_drivers)

missing_drivers = laps_missing_drivers.union(stream_missing_drivers)
print("Total missing drivers:", missing_drivers)

for driver in missing_drivers:

    driver_short_name = session.get_driver(driver).Abbreviation

    laps = session.laps.pick_driver(driver)

    lap = laps.iloc[0]  # İlk turu seç

    telemetry = lap.get_telemetry()

    telemetry_data = telemetry[['RPM', 'Speed', 'nGear', 'Throttle', 'Brake', 'DRS']]

    # Sabit veri kontrolü
    same_data_count = (telemetry_data.shift() == telemetry_data).all(axis=1).astype(int).groupby(telemetry_data.index // 40).sum()
    constant_data = same_data_count[same_data_count == 40]

    if not constant_data.empty:
        session_time = telemetry['SessionTime'].iloc[constant_data.index[0] * 40]
        print(f"Sürücü {driver_short_name} yarış dışı kaldı. SessionTime: {session_time}")


#DriverName diye bir sütun ekle 3. sütun olacka bu
# laps_data['DriverName'] = laps_data['Driver'].map(driver_enum)
laps_data.insert(2, 'DriverName', laps_data['Driver'].map(driver_enum))
# DataFrame'leri CSV olarak kaydet
laps_data.to_csv('2021_silverstone_laps_data.csv', index=False)
stream_data.to_csv('2021_silverstone_stream_data.csv', index=False)

print("Veriler CSV olarak kaydedildi.")
