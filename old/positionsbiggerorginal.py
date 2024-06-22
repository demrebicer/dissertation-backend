import fastf1
from fastf1 import plotting
import matplotlib.pyplot as plt
import pandas as pd

# Önbelleği ve logging'i ayarlayın
fastf1.Cache.enable_cache('f1cache')

# Yarış verilerini yükleyin
session = fastf1.get_session(2021, 'Silverstone', 'R')
session.load()

# Lewis Hamilton'un turlarını seçin
laps = session.laps.pick_driver('HAM')

# Tüm sürücülerin turlarını alın
lap = laps.iloc[0]  # İlk turu seç
telemetry = lap.get_telemetry()

# Sadece X ve Y koordinatlarını alıyoruz
x_coordinates = telemetry['X'].values
y_coordinates = telemetry['Y'].values

# Three.js formatına uygun olarak [x, 0, y] şeklinde bir dizi oluşturalım
threejs_points = [[x, 0, y] for x, y in zip(x_coordinates, y_coordinates)]

print(threejs_points)