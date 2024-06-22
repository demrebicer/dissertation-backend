import matplotlib.pyplot as plt
import numpy as np
import fastf1
from fastf1 import plotting

# Enable the cache for fastf1
fastf1.Cache.enable_cache('f1cache')

# Load the session data
session = fastf1.get_session(2021, 'Silverstone', 'Q')
session.load()

# Pick the fastest lap from the session
lap = session.laps.pick_fastest()
pos = lap.get_pos_data()

# Define a helper function for rotating points
def rotate(xy, angle):
    rad = np.radians(angle)
    rot_mat = np.array([[np.cos(rad), -np.sin(rad)], [np.sin(rad), np.cos(rad)]])
    return np.dot(xy, rot_mat)

# Extract the track map coordinates
track_coords = pos[['X', 'Y']].to_numpy()

# Get the rotation angle from the circuit information
circuit_info = session.get_circuit_info()
rotation_angle = circuit_info.rotation

# Rotate the track map coordinates
rotated_track = rotate(track_coords, rotation_angle)

print(session.event.keys())


# Plotting the rotated track map
plt.figure(figsize=(10, 8))
plt.plot(rotated_track[:, 0], rotated_track[:, 1], label='Track Map')
plt.title(f"{session.event.EventName} {session.event.EventDate} - Fastest Lap Track Map")
plt.axis('equal')  # Keep the aspect ratio of the track
plt.xticks([])
plt.yticks([])
plt.legend()
plt.show()
