import os
import fastf1
import pandas as pd

# Ensure the cache directory exists
cache_dir = 'f1cache'
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)

# Enable the cache
fastf1.Cache.enable_cache(cache_dir)

# Load the session data (Example: 2021 Silverstone Grand Prix)
session = fastf1.get_session(2021, 'Silverstone', 'R')
session.load()

# Get all laps data
laps = session.laps

# Create a list to store position changes
position_changes_list = []

# Sort laps by time to track positions over the race duration
laps = laps.sort_values(by='Time')

# Initialize a dictionary to keep track of the last known positions
last_positions = {}

# Iterate through each row to find position changes
for index, row in laps.iterrows():
    driver = row['Driver']
    time = row['Time']
    position = row['Position']

    if driver in last_positions:
        previous_position = last_positions[driver]
        if position != previous_position:
            position_changes_list.append({
                'Time': time,
                'Driver': driver,
                'Previous_Position': previous_position,
                'New_Position': position
            })

    # Update the last known position
    last_positions[driver] = position

# Convert the list to a DataFrame
position_changes = pd.DataFrame(position_changes_list)

# print(position_changes)

# Print position changes
for index, row in position_changes.iterrows():
    print(f"Zaman: {row['Time']}, Sürücü: {row['Driver']}, Önceki Pozisyon: {row['Previous_Position']}, Yeni Pozisyon: {row['New_Position']}")


#Create a json for the position changes
position_changes_json = position_changes.to_json(orient='records')

# print(position_changes_json)

# Save the position changes to a JSON file
position_changes.to_json('position_changes.json', orient='records')