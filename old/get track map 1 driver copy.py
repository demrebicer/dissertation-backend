import os
import fastf1
from fastf1 import plotting
from matplotlib import pyplot as plt

# Önbellek dizinini kontrol edin ve gerekirse oluşturun
cache_dir = 'f1cache'
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)

# FastF1'nin cache mekanizmasını etkinleştir
fastf1.Cache.enable_cache(cache_dir)

# Yarış verilerini yükleyin ve işleyin
# Örneğin: 2021 Silverstone Grand Prix için
session = fastf1.get_session(2021, 'Silverstone', 'R')
session.load()

# Lewis Hamilton'un turlarını seçin
laps = session.laps.pick_driver('GAS')

# Hamilton'un tur telemetrisini alın
# Örnek olarak ilk turu kullanalım
lap = laps.iloc[0]  # İlk turu seç
telemetry = lap.get_telemetry()

# Telemetriden zaman ve mesafe verilerini çek
time = telemetry['Time']
distance = telemetry['Distance']

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
scale_factor = 1 / max_range

# Koordinatları ölçeklendirip, ilk koordinatı (0,0,0) olacak şekilde ayarlayalım
scaled_normalized_points = [
    [((x - min_x) * scale_factor) - ((first_x - min_x) * scale_factor), 0, ((y - min_y) * scale_factor) - ((first_y - min_y) * scale_factor)]
    for x, y in zip(x_coordinates, y_coordinates)
]

# İlk 15 noktayı örnek olarak gösterelim
print(scaled_normalized_points)

