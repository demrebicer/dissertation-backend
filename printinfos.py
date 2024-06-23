import os
import fastf1
from fastf1 import plotting
from matplotlib import pyplot as plt
import numpy as np

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

# Belirli bir turun verilerini seçin
lap_number = 19  # Burada görmek istediğiniz tur numarasını belirleyin
selected_lap = session.laps.pick_driver('HAM').pick_lap(lap_number)

# # Seçilen tur için araç verilerini ve pozisyon verilerini alın
car_data = selected_lap.get_car_data()
pos_data = selected_lap.get_pos_data()

print(car_data)
print(pos_data)

# Pozisyon verilerini CSV dosyasına kaydedin
pos_data.to_csv('pos_data.csv')
car_data.to_csv('car_data.csv')