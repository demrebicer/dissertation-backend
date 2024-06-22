import fastf1
from fastf1 import plotting

# Önbelleği ve logging'i ayarlayın
fastf1.Cache.enable_cache('f1cache') # Bu adımı tekrar çalıştırmaya gerek yok, çünkü zaten ayarlandı.

# Yarış verilerini yükleyin
session = fastf1.get_session(2021, 'Silverstone', 'R')
session.load()

# Lewis Hamilton ve Charles Leclerc'in turlarını seçin
laps_hamilton = session.laps.pick_driver('HAM')
laps_leclerc = session.laps.pick_driver('LEC')

# Her iki sürücünün de ilk turlarının telemetrisini alın
lap_hamilton = laps_hamilton.iloc[0]  # Hamilton'un ilk turu
telemetry_hamilton = lap_hamilton.get_telemetry()

lap_leclerc = laps_leclerc.iloc[0]  # Leclerc'in ilk turu
telemetry_leclerc = lap_leclerc.get_telemetry()

lap_time_ms = lap_hamilton.LapTime.total_seconds() * 1000
print(lap_time_ms)

lap_time_ms_2 = lap_leclerc.LapTime.total_seconds() * 1000
print(lap_time_ms_2)

# Hamilton ve Leclerc için X ve Y koordinatlarını alın
x_hamilton, y_hamilton = telemetry_hamilton['X'], telemetry_hamilton['Y']
x_leclerc, y_leclerc = telemetry_leclerc['X'], telemetry_leclerc['Y']

# Hamilton için koordinatları ölçeklendirip, ilk koordinatı (0,0) olacak şekilde ayarlayın
min_x_hamilton, max_x_hamilton = x_hamilton.min(), x_hamilton.max()
min_y_hamilton, max_y_hamilton = y_hamilton.min(), y_hamilton.max()
range_x_hamilton = max_x_hamilton - min_x_hamilton
range_y_hamilton = max_y_hamilton - min_y_hamilton
max_range_hamilton = max(range_x_hamilton, range_y_hamilton)
scale_factor_hamilton = 100 / max_range_hamilton
scaled_normalized_hamilton = [
    [(x - min_x_hamilton) * scale_factor_hamilton, 0, (y - min_y_hamilton) * scale_factor_hamilton]
    for x, y in zip(x_hamilton, y_hamilton)
]

# Leclerc için koordinatları ölçeklendirip, ilk koordinatı (0,0) olacak şekilde ayarlayın
min_x_leclerc, max_x_leclerc = x_leclerc.min(), x_leclerc.max()
min_y_leclerc, max_y_leclerc = y_leclerc.min(), y_leclerc.max()
range_x_leclerc = max_x_leclerc - min_x_leclerc
range_y_leclerc = max_y_leclerc - min_y_leclerc
max_range_leclerc = max(range_x_leclerc, range_y_leclerc)
scale_factor_leclerc = 100 / max_range_leclerc
scaled_normalized_leclerc = [
    [(x - min_x_leclerc) * scale_factor_leclerc, 0, (y - min_y_leclerc) * scale_factor_leclerc]
    for x, y in zip(x_leclerc, y_leclerc)
]

# Hamilton ve Leclerc için ölçeklendirilmiş ve normalleştirilmiş ilk 5 koordinatı yazdırın
print("Hamilton: ")
print(scaled_normalized_hamilton)
# print("Leclerc: ")
# print(scaled_normalized_leclerc)

