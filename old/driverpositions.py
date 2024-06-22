import fastf1
from fastf1 import plotting
import os

# Enable cache and logging
fastf1.Cache.enable_cache('f1cache')

# Load race session data
session = fastf1.get_session(2015, 'Silverstone', 'R')
session.load()

# Get the pole sitter's driver number from the qualifying session
qualifying_session = fastf1.get_session(2015, 'Silverstone', 'Q')
qualifying_session.load()
pole_sitter_driver = qualifying_session.laps.pick_fastest().Driver

# Get all drivers in the race session
drivers = session.laps['Driver'].unique()

# Function to get X, Y coordinates for a driver's first lap
def get_coordinates(driver_code):
    laps = session.laps.pick_driver(driver_code)
    lap = laps.iloc[0]  # Choose the first lap
    telemetry = lap.get_telemetry()
    
    x = telemetry['X'].values
    y = telemetry['Y'].values
    
    return x, y

# Get the global min and max coordinates for scaling
global_min_x, global_max_x = float('inf'), float('-inf')
global_min_y, global_max_y = float('inf'), float('-inf')

for driver in drivers:
    x, y = get_coordinates(driver)
    global_min_x = min(global_min_x, min(x))
    global_max_x = max(global_max_x, max(x))
    global_min_y = min(global_min_y, min(y))
    global_max_y = max(global_max_y, max(y))

# Define the scale factor based on the global coordinates
range_x = global_max_x - global_min_x
range_y = global_max_y - global_min_y
max_range = max(range_x, range_y)
scale_factor = 177.5 / max_range

# Function to adjust coordinates with a common reference point and global scaling
def adjust_coordinates(x_coordinates, y_coordinates, ref_x, ref_y):
    adjusted_points = [
        [((x - ref_x) * scale_factor), 
         0, 
         ((y - ref_y) * scale_factor)]
        for x, y in zip(x_coordinates, y_coordinates)
    ]
    
    return adjusted_points

# Get coordinates for the pole sitter to use as reference
reference_x, reference_y = get_coordinates(pole_sitter_driver)

# Prepare output file
output_file = 'driver_positions.js'
if os.path.exists(output_file):
    os.remove(output_file)

# Initialize an empty list to store constant names
constant_names = []

# Process telemetry data for each driver
with open(output_file, 'a') as f:
    for driver in drivers:
        x, y = get_coordinates(driver)
        adjusted_points = adjust_coordinates(x, y, reference_x[0], reference_y[0])
        
        # Create a constant name based on the driver's code
        const_name = f"{driver.lower()}_positions"
        constant_names.append(const_name)
        
        # Write the constant to the file
        f.write(f"export const {const_name} = {adjusted_points};\n")

# Print the constant names
print("Created constants:")
for name in constant_names:
    print(name)
