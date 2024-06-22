import fastf1
from fastf1 import plotting
import matplotlib.pyplot as plt
import pandas as pd

# Önbelleği ve logging'i ayarlayın
fastf1.Cache.enable_cache('f1cache')

# Yarış verilerini yükleyin
session = fastf1.get_session(2021, 'Silverstone', 'R')
session.load()

#export the session laps data to a csv file
session.laps.to_csv('lapsham.csv')

# Lewis Hamilton'un turlarını seçin
laps = session.laps.pick_driver('HAM')

# Tüm sürücülerin turlarını alın
lap = laps.iloc[0]  # İlk turu seç
telemetry = lap.get_telemetry()

lap_time_ms = lap.LapTime.total_seconds() * 1000
print(lap_time_ms)

# Hamilton'un tur telemetrisinden X ve Y koordinatlarını alın
x = telemetry['X']
y = telemetry['Y']

x_coordinates = x.values
y_coordinates = y.values

min_x, max_x = min(x_coordinates), max(x_coordinates)
min_y, max_y = min(y_coordinates), max(y_coordinates)

first_x = x_coordinates[0]
first_y = y_coordinates[0]

# Koordinat aralığını bulalım
range_x = max_x - min_x
range_y = max_y - min_y

# En büyük aralığı bulup, her iki eksen için de aynı ölçekleme faktörünü kullanalım
max_range = max(range_x, range_y)

# Ölçekleme faktörü olarak en büyük aralığın tersini alalım
scale_factor = 177.5 / max_range  # Örnekte belirlenen ölçekleme faktörü

# İlk pozisyon olarak ayarlanacak yeni değerler
new_start_x = 25
new_start_y = 0
new_start_z = 210

# Scaled ve normalized koordinatları yeni başlangıç noktası ile ayarlayalım
adjusted_points = [
    [((x - min_x) * scale_factor) - ((first_x - min_x) * scale_factor) + new_start_x, 
     new_start_y, 
     ((y - min_y) * scale_factor) - ((first_y - min_y) * scale_factor) + new_start_z]
    for x, y in zip(x_coordinates, y_coordinates)
]

# İlk 15 noktayı örnek olarak gösterelim
# adjusted_points[:15]

# İlk 15 noktayı örnek olarak gösterelim
# print(adjusted_points)

time = telemetry['Time'].dt.total_seconds().values  # Zamanı saniye cinsinden alalım
# time_seconds = np.array(time) 
#format times as 00:00.000
formatted_time = [f"{int(t // 60):02d}:{t % 60:06.3f}" for t in time]



print(len(adjusted_points))
