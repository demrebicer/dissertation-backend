import fastf1
from fastf1 import plotting
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation

# Enable the cache
fastf1.Cache.enable_cache('f1cache') 

# Load the session
session = fastf1.get_session(2021, 'Silverstone', 'R')
session.load()

# Get the lap data for Hamilton and Perez for lap 1
hamilton = session.laps.pick_driver('HAM').pick_lap(1)
perez = session.laps.pick_driver('PER').pick_lap(1)

# Extract telemetry data
hamilton_tel = hamilton.get_telemetry()
perez_tel = perez.get_telemetry()

# Predefined reference and global min/max values
REFERENCE_X = [2.0]  # Example reference point, please adjust accordingly
REFERENCE_Y = [3.0]  # Example reference point, please adjust accordingly
PREDEFINED_GLOBAL_MIN_X = -3000
PREDEFINED_GLOBAL_MAX_X = 3000
PREDEFINED_GLOBAL_MIN_Y = -3000
PREDEFINED_GLOBAL_MAX_Y = 3000

# Define the scale factor based on the global coordinates
def get_scale_factor(global_min_x, global_max_x, global_min_y, global_max_y):
    range_x = global_max_x - global_min_x
    range_y = global_max_y - global_min_y
    max_range = max(range_x, range_y)
    scale_factor = 177.5 / max_range
    return scale_factor

# Function to adjust coordinates with a common reference point and global scaling
def adjust_coordinates(x_coordinates, y_coordinates, ref_x, ref_y, scale_factor):
    adjusted_points = [
        ((x - ref_x) * scale_factor, (y - ref_y) * scale_factor)
        for x, y in zip(x_coordinates, y_coordinates)
    ]
    return adjusted_points

# Calculate the scale factor
scale_factor = get_scale_factor(PREDEFINED_GLOBAL_MIN_X, PREDEFINED_GLOBAL_MAX_X, PREDEFINED_GLOBAL_MIN_Y, PREDEFINED_GLOBAL_MAX_Y)

# Adjust the coordinates for Hamilton and Perez
hamilton_adjusted = adjust_coordinates(hamilton_tel['X'], hamilton_tel['Y'], REFERENCE_X[0], REFERENCE_Y[0], scale_factor)
perez_adjusted = adjust_coordinates(perez_tel['X'], perez_tel['Y'], REFERENCE_X[0], REFERENCE_Y[0], scale_factor)

# Convert the adjusted coordinates to separate lists
hamilton_x_adj, hamilton_y_adj = zip(*hamilton_adjusted)
perez_x_adj, perez_y_adj = zip(*perez_adjusted)

# Set up the plot
fig, ax = plt.subplots()
line_ham, = ax.plot([], [], label='Hamilton', color='blue')
line_per, = ax.plot([], [], label='Perez', color='red')
ax.set_xlim(min(min(hamilton_x_adj), min(perez_x_adj)), max(max(hamilton_x_adj), max(perez_x_adj)))
ax.set_ylim(min(min(hamilton_y_adj), min(perez_y_adj)), max(max(hamilton_y_adj), max(perez_y_adj)))
plt.legend()

def update(frame):
    line_ham.set_data(hamilton_x_adj[:frame], hamilton_y_adj[:frame])
    line_per.set_data(perez_x_adj[:frame], perez_y_adj[:frame])
    return line_ham, line_per

ani = FuncAnimation(fig, update, frames=min(len(hamilton_x_adj), len(perez_x_adj)), blit=True)

plt.xlabel('X Coordinate')
plt.ylabel('Y Coordinate')
plt.title('Hamilton vs Perez - Lap 1 Silverstone 2021')

plt.show()
