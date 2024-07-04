import os
import fastf1
from fastf1 import plotting
from matplotlib import pyplot as plt
import numpy as np
from scipy.interpolate import splprep, splev

# Enable the cache
cache_dir = 'f1cache'
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)

fastf1.Cache.enable_cache(cache_dir)

# Load session data
session = fastf1.get_session(2021, 'Silverstone', 'R')
session.load()

# Get clean telemetry data from another driver to generate the track map
reference_lap = session.laps.pick_driver('HAM').iloc[0]
reference_telemetry = reference_lap.get_telemetry()
ref_x = reference_telemetry['X'].values
ref_y = reference_telemetry['Y'].values

# Remove NaNs from reference data and ensure valid ranges
valid_indices = ~np.isnan(ref_x) & ~np.isnan(ref_y) & (ref_x > -1e6) & (ref_x < 1e6) & (ref_y > -1e6) & (ref_y < 1e6)
ref_x = ref_x[valid_indices]
ref_y = ref_y[valid_indices]

# Ensure there are enough points for spline fitting
if len(ref_x) < 3 or len(ref_y) < 3:
    raise ValueError("Not enough valid points for spline fitting")

# Fit a spline to the reference track data for smoothing
try:
    tck, u = splprep([ref_x, ref_y], s=1000)  # Increased smoothing factor
    new_points = splev(u, tck)
except Exception as e:
    print(f"Error in spline fitting: {e}")
    new_points = [ref_x, ref_y]  # Fallback to original data

# Plot the reference track map
plt.plot(new_points[0], new_points[1], label='Track Map')
plt.xlabel('X Coordinate')
plt.ylabel('Y Coordinate')
plt.title('Silverstone Track Map')
plt.legend()
plt.show()

# Get Gasly's telemetry data
gasly_laps = session.laps.pick_driver('GAS')
gasly_lap = gasly_laps.iloc[0]
gasly_telemetry = gasly_lap.get_telemetry()
x_gasly = gasly_telemetry['X'].values
y_gasly = gasly_telemetry['Y'].values
speed_gasly = gasly_telemetry['Speed'].values

# Remove NaNs from Gasly's data and ensure valid ranges
valid_indices_gasly = ~np.isnan(x_gasly) & ~np.isnan(y_gasly) & ~np.isnan(speed_gasly) & (x_gasly > -1e6) & (x_gasly < 1e6) & (y_gasly > -1e6) & (y_gasly < 1e6)
x_gasly = x_gasly[valid_indices_gasly]
y_gasly = y_gasly[valid_indices_gasly]
speed_gasly = speed_gasly[valid_indices_gasly]

# Function to correct telemetry data in segments
def correct_telemetry_segments(x, y, ref_points, segment_length=50, threshold=100):
    corrected_x = np.copy(x)
    corrected_y = np.copy(y)
    num_segments = len(x) // segment_length
    for seg in range(num_segments):
        start = seg * segment_length
        end = start + segment_length
        if end > len(x):
            end = len(x)
        segment_x = x[start:end]
        segment_y = y[start:end]
        for i in range(len(segment_x)):
            min_dist = np.inf
            closest_point = (segment_x[i], segment_y[i])
            for j in range(len(ref_points[0])):
                dist = np.sqrt((segment_x[i] - ref_points[0][j])**2 + (segment_y[i] - ref_points[1][j])**2)
                if dist < min_dist:
                    min_dist = dist
                    closest_point = (ref_points[0][j], ref_points[1][j])
            if min_dist > threshold:
                corrected_x[start + i] = closest_point[0]
                corrected_y[start + i] = closest_point[1]
    return corrected_x, corrected_y

# Correct Gasly's telemetry data in segments
corrected_x_gasly, corrected_y_gasly = correct_telemetry_segments(x_gasly, y_gasly, new_points)

# Function to smooth corrected telemetry data locally with constraints
def local_smoothing_with_constraints(x, y, window_size=10, smoothing_factor=0.1):
    smoothed_x = np.copy(x)
    smoothed_y = np.copy(y)
    for i in range(window_size, len(x) - window_size):
        segment_x = x[i - window_size:i + window_size]
        segment_y = y[i - window_size:i + window_size]
        valid_indices = ~np.isnan(segment_x) & ~np.isnan(segment_y) & (segment_x > -1e6) & (segment_x < 1e6) & (segment_y > -1e6) & (segment_y < 1e6)
        segment_x = segment_x[valid_indices]
        segment_y = segment_y[valid_indices]
        if len(segment_x) < 3 or len(segment_y) < 3:
            continue
        try:
            tck, u = splprep([segment_x, segment_y], s=smoothing_factor)
            smoothed_segment = splev(u, tck)
            smoothed_x[i] = smoothed_segment[0][window_size]
            smoothed_y[i] = smoothed_segment[1][window_size]
        except Exception as e:
            print(f"Error in local smoothing at index {i}: {e}")
            continue
    return smoothed_x, smoothed_y

# Apply local smoothing with constraints to the corrected data
smoothed_x_gasly, smoothed_y_gasly = local_smoothing_with_constraints(corrected_x_gasly, corrected_y_gasly)

# Plot the corrected and smoothed telemetry data
plt.plot(new_points[0], new_points[1], label='Track Map', linestyle='--')
plt.plot(smoothed_x_gasly, smoothed_y_gasly, label='Gasly Corrected and Smoothed Lap')
plt.xlabel('X Coordinate')
plt.ylabel('Y Coordinate')
plt.title('Gasly\'s Corrected and Smoothed Lap at Silverstone')
plt.legend()
plt.show()
