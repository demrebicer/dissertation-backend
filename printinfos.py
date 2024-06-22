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
session = fastf1.get_session(2022, 'Silverstone', 'Q')
session.load()

# Hamiton'nun turlarını seçin
laps = session.laps.pick_driver('HAM').get_telemetry()

laps.to_csv('telemetry.csv')
