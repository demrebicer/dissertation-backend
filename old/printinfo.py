import os
import fastf1
from fastf1 import plotting
from matplotlib import pyplot as plt
import numpy as np
import fastf1.api

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

weather = session.weather_data

print(weather)