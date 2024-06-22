import fastf1 as ff1
import matplotlib.pyplot as plt

# FastF1'i yapılandırın ve gerekli verileri indirin
ff1.Cache.enable_cache('f1cache')  # Cache klasörünü belirleyin

# 2021 Silverstone yarışını yükleyin
race = ff1.get_session(2021, 'Silverstone', 'R')
race.load()

# Grid pozisyonlarını alalım
results = race.results
grid_positions = results[['GridPosition', 'Abbreviation']].sort_values(by='GridPosition')

# Her sürücünün start pozisyonu koordinatlarını almak için bir fonksiyon yazalım
def get_start_coordinates(driver_abbr):
    laps = race.laps.pick_driver(driver_abbr)
    telemetry = laps.iloc[0].get_telemetry()
    start_telemetry = telemetry[telemetry['Speed'] == 0]
    if not start_telemetry.empty:
        x = start_telemetry['X'].values[0]
        y = start_telemetry['Y'].values[0]
        return x, y
    else:
        return None, None

# Tüm sürücülerin start koordinatlarını alalım
driver_coordinates = {row.Abbreviation: get_start_coordinates(row.Abbreviation) for index, row in grid_positions.iterrows()}

# Plot oluşturma
plt.figure(figsize=(10, 10))

for driver, (x, y) in driver_coordinates.items():
    if x is not None and y is not None:
        plt.scatter(x, y, label=driver)

plt.title('2021 Silverstone Yarışındaki Grid Pozisyonları')
plt.xlabel('X Koordinatı')
plt.ylabel('Y Koordinatı')
plt.legend()
plt.show()