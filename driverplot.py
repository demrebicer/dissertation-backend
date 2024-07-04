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

laps = session.laps.pick_driver('GAS')

# Örnek olarak ilk turu kullanalım
lap = laps.iloc[0]  # İlk turu seç
telemetry = lap.get_telemetry()

# Telemetriden X ve Y koordinatlarını alın
x = telemetry['X'].values
y = telemetry['Y'].values
speed = telemetry['Speed'].values

# Hatalı noktaları filtrelemek için farkları hesapla
dx = np.diff(x)
dy = np.diff(y)
distance = np.sqrt(dx**2 + dy**2)

# Hatalı noktaları filtrelemek için eşik değeri belirle
threshold = np.mean(distance) + 2 * np.std(distance)
valid_points = np.hstack([[True], distance < threshold])

# Hızdaki ani değişiklikleri hesapla
dspeed = np.diff(speed)
speed_threshold = np.mean(dspeed) + 2 * np.std(dspeed)
speed_anomalies = np.abs(dspeed) > speed_threshold

# Hızdaki ani değişikliklerin olduğu noktaları işaretle
anomaly_indices = np.where(speed_anomalies)[0]

# Geçersiz noktaları interpolasyon ile düzeltme
for i in range(1, len(valid_points) - 1):
    if not valid_points[i]:
        x[i] = (x[i - 1] + x[i + 1]) / 2
        y[i] = (y[i - 1] + y[i + 1]) / 2

# Hatalı noktaları kaldırarak temizleme
x_cleaned = np.delete(x, anomaly_indices)
y_cleaned = np.delete(y, anomaly_indices)

# Yeniden interpolasyon yaparak hatalı noktaları düzelt
for i in anomaly_indices:
    if i > 0 and i < len(x) - 1:
        x_cleaned = np.insert(x_cleaned, i, (x[i - 1] + x[i + 1]) / 2)
        y_cleaned = np.insert(y_cleaned, i, (y[i - 1] + y[i + 1]) / 2)

# Plot the filtered X and Y coordinates
plt.plot(x_cleaned, y_cleaned)
plt.xlabel('X Coordinate')
plt.ylabel('Y Coordinate')
plt.title('Hamilton\'s Lap at Silverstone')
plt.show()

