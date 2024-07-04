from sanic import Sanic
from sanic.response import json
from sanic_cors import CORS
import fastf1
import concurrent.futures
from cachetools import TTLCache, cached
import pandas as pd
from constants import *
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import fastf1.api

# Enable cache
fastf1.Cache.enable_cache('f1cache')

# Initialize Sanic app
app = Sanic("F1TelemetryAPI")
CORS(app)  # Enable CORS for all routes

# Create caches for different routes
years_cache = TTLCache(maxsize=100, ttl=86400)  # Cache for 1 day
drivers_cache = TTLCache(maxsize=100, ttl=86400)
laps_cache = TTLCache(maxsize=100, ttl=86400)
telemetry_cache = TTLCache(maxsize=100, ttl=86400)

# Check if a given year has Silverstone data
@cached(years_cache)
def check_year_for_silverstone(year):
    try:
        schedule = fastf1.get_event_schedule(year)
        # Find Silverstone in the schedule
        if 'Silverstone' in schedule['Location'].values:
            # Check if the race session has driver position data
            session = fastf1.get_session(year, 'Silverstone', 'Race')
            session.load()
            if not session.laps.empty:
                return year
    except Exception:
        pass
    return None

# Get available years dynamically using parallel processing
@cached(years_cache)
def get_available_years():
    current_year = 2024  # Set the current year or dynamically get the current year if needed
    available_years = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(check_year_for_silverstone, range(1950, current_year + 1)))
        available_years = [year for year in results if year is not None]
    return available_years

# Load race session data
@cached(drivers_cache)
def load_session(year, event_name, session_type):
    session = fastf1.get_session(year, event_name, session_type)
    session.load()
    return session

# Get all drivers in the race session
@cached(drivers_cache)
def get_drivers(session):
    first_lap = session.laps[session.laps['LapNumber'] == 1]
    return first_lap['Driver'].unique()

# Function to get X, Y coordinates and speed for a driver's specified lap
@cached(telemetry_cache)
def get_coordinates(session, driver_code, lap_number):
    laps = session.laps.pick_driver(driver_code)
    
    if lap_number < 1 or lap_number > len(laps):
        raise ValueError("Invalid lap number")
    
    lap = laps.iloc[lap_number - 1]  # Choose the specified lap
    
    car_data = lap.get_car_data()
    pos_data = lap.get_pos_data()
    
    x = pos_data['X'].values
    y = pos_data['Y'].values
    speed = car_data['Speed'].values
    brake = car_data['Brake'].values
    rpm = car_data['RPM'].values
    
    return x, y, speed, brake, rpm

# Define the scale factor based on the global coordinates
@cached(telemetry_cache)
def get_scale_factor(global_min_x, global_max_x, global_min_y, global_max_y):
    range_x = global_max_x - global_min_x
    range_y = global_max_y - global_min_y
    max_range = max(range_x, range_y)
    scale_factor = 177.5 / max_range
    return scale_factor

# Function to adjust coordinates with a common reference point and global scaling
def adjust_coordinates(x_coordinates, y_coordinates, ref_x, ref_y, scale_factor):
    adjusted_points = [
        [((x - ref_x) * scale_factor), 
         0, 
         ((y - ref_y) * scale_factor)]
        for x, y in zip(x_coordinates, y_coordinates)
    ]
    
    return adjusted_points

# Function that returns laps weather data as json array [1: data, 2: data, ...] Rainfall
def get_lap_weather(session, lap_start_time, lap_duration):
    weather_data = session.laps.get_weather_data()
    rain = False
    
    for index, weather in weather_data.iterrows():
        if lap_start_time <= weather['Time'] <= (lap_start_time + lap_duration):
            rain = rain or bool(weather['Rainfall']) if not pd.isnull(weather['Rainfall']) else False
    
    return rain

@app.route('/years', methods=['GET'])
async def get_years(request):
    years = get_available_years()
    return json(years)

@app.route('/drivers/<year:int>/<session_type>', methods=['GET'])
async def get_drivers_by_year(request, year, session_type):
    session = load_session(year, 'Silverstone', session_type)
    drivers = get_drivers(session)
    return json(drivers.tolist())

@app.route('/laps/<year:int>/<session_type>/<driver_code>', methods=['GET'])
async def get_laps_by_driver(request, year, session_type, driver_code):
    session = load_session(year, 'Silverstone', session_type)
    laps = session.laps.pick_driver(driver_code)
    lap_numbers = list(range(1, len(laps) + 1))
    return json(lap_numbers)


@app.route('/telemetry/<year:int>/<session_type>/<driver_code>/<lap_number:int>', methods=['GET'])
async def get_telemetry(request, year, session_type, driver_code, lap_number):
    session = load_session(year, 'Silverstone', session_type)
    
    # Load necessary data
    session.load(laps=True, telemetry=True)
    
    # Get coordinates for the reference lap (using the first lap of the pole sitter)
    reference_x, reference_y, _, _, _ = get_coordinates(session, driver_code, 1)
    
    reference_x = REFERENCE_X
    reference_y = REFERENCE_Y

    global_min_x = PREDEFINED_GLOBAL_MIN_X
    global_max_x = PREDEFINED_GLOBAL_MAX_X
    global_min_y = PREDEFINED_GLOBAL_MIN_Y
    global_max_y = PREDEFINED_GLOBAL_MAX_Y
        
    scale_factor = get_scale_factor(global_min_x, global_max_x, global_min_y, global_max_y)
    
    # Get coordinates, speed, and brake data for the selected driver and lap
    x, y, speed, brake, rpm = get_coordinates(session, driver_code, lap_number)
    adjusted_points = adjust_coordinates(x, y, reference_x[0], reference_y[0], scale_factor)
    
    # Get the lap data
    laps = session.laps.pick_driver(driver_code)
    
    try:
        lap = laps.iloc[lap_number - 1]
        lap_duration = lap['LapTime'].total_seconds() if not pd.isnull(lap['LapTime']) else None
    except IndexError:
        lap_duration = None

    if lap_duration is None:
        # Use telemetry data to calculate lap duration if LapTime is missing
        telemetry_data = session.laps.pick_driver(driver_code).pick_lap(lap_number).get_telemetry()
        if not telemetry_data.empty:
            lap_start_time = telemetry_data.iloc[0]['Time']
            lap_end_time = telemetry_data.iloc[-1]['Time']
            lap_duration = (lap_end_time - lap_start_time).total_seconds()
        else:
            # Fallback: Estimate lap duration using the average of surrounding laps
            previous_laps = laps.iloc[max(0, lap_number - 5):lap_number - 1]
            next_laps = laps.iloc[lap_number:min(lap_number + 5, len(laps))]
            surrounding_laps = pd.concat([previous_laps, next_laps])
            estimated_duration = surrounding_laps['LapTime'].mean().total_seconds() if not surrounding_laps['LapTime'].isnull().all() else 30
            lap_duration = estimated_duration

    lap_duration = pd.Timedelta(seconds=lap_duration)  # Convert lap duration back to Timedelta

    # Retrieve flag data
    track_status = session.track_status
    flag_data = []
    
    for index, row in track_status.iterrows():
        if index < len(track_status) - 1:
            next_row = track_status.iloc[index + 1]

        if lap['LapStartTime'] <= row['Time'] <= (lap['LapStartTime'] + lap_duration):
            start_time = (row['Time'] - lap['LapStartTime']).total_seconds()
            end_time = (next_row['Time'] - lap['LapStartTime']).total_seconds() if next_row['Time'] <= (lap['LapStartTime'] + lap_duration) else lap_duration.total_seconds()
            flag_data.append({
                'start_time': start_time,
                'end_time': end_time,
                'flag': row['Status']
            })

    # Check if it was raining during the selected lap
    rain = get_lap_weather(session, lap['LapStartTime'], lap_duration)

    return json({
        'telemetry': adjusted_points,
        'lap_duration': lap_duration.total_seconds(),  # Convert to seconds for JSON response
        'speed': speed.tolist(),  # Include speed data as an array
        'brake': brake.tolist(),  # Include brake data as an array
        'rpm': rpm.tolist(),  # Include RPM data as an array
        'flags': flag_data,  # Include flag data with start and end times
        'is_rain': rain,  # Include rain information for the selected lap
    })

@app.route('/all-telemetry/<year:int>/<session_type>/<lap_number:int>', methods=['GET'])
async def get_all_telemetry(request, year, session_type, lap_number):
    session = load_session(year, 'Silverstone', session_type)
    
    # Load necessary data
    session.load(laps=True, telemetry=True)

    # Get all drivers in the session
    drivers = get_drivers(session)
    
    # Function to process telemetry data for a driver
    def process_driver_telemetry(driver_code):
        try:
            # Get coordinates, speed, and brake data for the selected driver and lap
            x, y, speed, brake, rpm = get_coordinates(session, driver_code, lap_number)
            adjusted_points = adjust_coordinates(x, y, REFERENCE_X[0], REFERENCE_Y[0], get_scale_factor(
                PREDEFINED_GLOBAL_MIN_X, PREDEFINED_GLOBAL_MAX_X, PREDEFINED_GLOBAL_MIN_Y, PREDEFINED_GLOBAL_MAX_Y
            ))

            # Get the lap duration
            laps = session.laps.pick_driver(driver_code)
            try:
                lap = laps.iloc[lap_number - 1]
                lap_duration = lap['LapTime'].total_seconds() if not pd.isnull(lap['LapTime']) else None
            except IndexError:
                lap_duration = None

            if lap_duration is None:
                # Use telemetry data to calculate lap duration if LapTime is missing
                telemetry_data = session.laps.pick_driver(driver_code).pick_lap(lap_number).get_telemetry()
                if not telemetry_data.empty:
                    lap_start_time = telemetry_data.iloc[0]['Time']
                    lap_end_time = telemetry_data.iloc[-1]['Time']
                    lap_duration = (lap_end_time - lap_start_time).total_seconds()
                else:
                    # Fallback: Estimate lap duration using the average of surrounding laps
                    previous_laps = laps.iloc[max(0, lap_number - 5):lap_number - 1]
                    next_laps = laps.iloc[lap_number:min(lap_number + 5, len(laps))]
                    surrounding_laps = pd.concat([previous_laps, next_laps])
                    estimated_duration = surrounding_laps['LapTime'].mean().total_seconds() if not surrounding_laps['LapTime'].isnull().all() else 30
                    lap_duration = estimated_duration

            lap_duration = pd.Timedelta(seconds=lap_duration)  # Convert lap duration back to Timedelta

            # Retrieve flag data
            track_status = session.track_status
            flag_data = []

            for index, row in track_status.iterrows():
                if index < len(track_status) - 1:
                    next_row = track_status.iloc[index + 1]

                if lap['LapStartTime'] <= row['Time'] <= (lap['LapStartTime'] + lap_duration):
                    start_time = (row['Time'] - lap['LapStartTime']).total_seconds()
                    end_time = (next_row['Time'] - lap['LapStartTime']).total_seconds() if next_row['Time'] <= (lap['LapStartTime'] + lap_duration) else lap_duration.total_seconds()
                    flag_data.append({
                        'start_time': start_time,
                        'end_time': end_time,
                        'flag': row['Status']
                    })

            # Check if it was raining during the selected lap
            rain = get_lap_weather(session, lap['LapStartTime'], lap_duration)

            return {
                driver_code: {
                    'telemetry': adjusted_points,
                    'lap_duration': lap_duration.total_seconds(),  # Convert to seconds for JSON response
                    'speed': speed.tolist(),  # Include speed data as an array
                    'brake': brake.tolist(),  # Include brake data as an array
                    'rpm': rpm.tolist(),  # Include RPM data as an array
                    'flags': flag_data,  # Include flag data with start and end times
                    'is_rain': rain,  # Include rain information for the selected lap
                }
            }
        except Exception as e:
            print(f"Error processing telemetry for driver {driver_code}: {e}")
            return {}

    # Use a ThreadPoolExecutor to process drivers in parallel
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(process_driver_telemetry, drivers))
    
    # Merge results into a single dictionary
    all_telemetry_data = {}
    for result in results:
        all_telemetry_data.update(result)

    return json(all_telemetry_data)

def convert_timedelta_to_str(df):
    for column in df.select_dtypes(include=['timedelta']):
        df[column] = df[column].apply(lambda x: str(x.total_seconds()) if not pd.isnull(x) else None)
    return df

def convert_special_values_to_null(df):
    df = df.replace([pd.NaT, np.nan], None)
    return df

@app.get('/timing/<year:int>/<session_type>')
async def get_timing(request, year, session_type):
    session = fastf1.get_session(year, 'Silverstone', session_type)
    
    # Load necessary data
    session.load(laps=True, telemetry=True)

    print(session.drivers)

    laps_data, stream_data = fastf1.api.timing_data(session.api_path)
    
    laps_data = convert_timedelta_to_str(laps_data)
    laps_data = convert_special_values_to_null(laps_data)

    stream_data = convert_timedelta_to_str(stream_data)
    stream_data = convert_special_values_to_null(stream_data)

    return json({
        'laps_data': laps_data.to_dict(orient='records'),
        'stream_data': stream_data.to_dict(orient='records')
    })


# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, access_log=True, auto_reload=True, fast=True)