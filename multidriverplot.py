import fastf1

# Enable the cache
fastf1.Cache.enable_cache('f1cache')

# Load a session to get access to the driver data
session = fastf1.get_session(2021, 'Silverstone', 'R')
session.load()

# Get the list of drivers who participated in the 2021 season for the session
drivers = session.laps['Driver'].unique()

# Print the three-letter abbreviations of the drivers
for driver in drivers:
    print(driver)
