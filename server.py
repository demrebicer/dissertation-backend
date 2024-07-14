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
import asyncio

# Enable cache
fastf1.Cache.enable_cache('f1cache')

# Initialize Sanic app
app = Sanic("F1TelemetryAPI")
CORS(app)  # Enable CORS for all routes

# Create caches for different routes
telemetry_cache = TTLCache(maxsize=100, ttl=86400)

# Load race session data
@cached(telemetry_cache)
def load_session(year, event_name, session_type):
    session = fastf1.get_session(year, event_name, session_type)
    session.load()
    return session

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

def convert_timedelta_to_str(df):
    for column in df.select_dtypes(include=['timedelta']):
        df[column] = df[column].apply(lambda x: str(x.total_seconds()) if not pd.isnull(x) else None)
    return df

def convert_special_values_to_null(df):
    df = df.replace([pd.NaT, np.nan], None)
    return df

@app.get('/timing/<year:int>/<session_type>')
async def get_timing(request, year, session_type):
    session = load_session(year, 'Silverstone', session_type)

    session_drivers = session.drivers

    driver_enum = {}

    for driver in session.drivers:
        driver_enum[driver] = session.get_driver(driver).Abbreviation

    laps_data, stream_data = fastf1.api.timing_data(session.api_path)
    
    track_status = fastf1.api.track_status_data(session.api_path)
    track_status['Time'] = [x.total_seconds() for x in track_status['Time']]
    track_status_json = [
        {'Time': time, 'Status': status, 'Message': message}
        for time, status, message in zip(track_status['Time'], track_status['Status'], track_status['Message'])
    ]

    # Sürücü numaralarından oluşan set
    laps_drivers = set(laps_data['Driver'].unique())
    stream_drivers = set(stream_data['Driver'].unique())

    # Session sürücülerinin verisi olmayanları kontrol et
    laps_missing_drivers = set(session_drivers) - laps_drivers
    stream_missing_drivers = set(session_drivers) - stream_drivers

    # print("Laps data missing drivers:", laps_missing_drivers)
    # print("Stream data missing drivers:", stream_missing_drivers)

    missing_drivers = laps_missing_drivers.union(stream_missing_drivers)
    print("Total missing drivers:", missing_drivers)

    new_stream_data = []
    new_laps_data = []
    
    for driver in missing_drivers:

        driver_info = session.get_driver(driver)
        
        driver_short_name = driver_info.Abbreviation

        laps = session.laps.pick_driver(driver)

        lap = laps.iloc[0]  # İlk turu seç

        telemetry = lap.get_telemetry()

        telemetry_data = telemetry[['RPM', 'Speed', 'nGear', 'Throttle', 'Brake', 'DRS']]

        # Sabit veri kontrolü
        same_data_count = (telemetry_data.shift() == telemetry_data).all(axis=1).astype(int).groupby(telemetry_data.index // 40).sum()
        constant_data = same_data_count[same_data_count == 40]

        if not constant_data.empty:
            session_time_first = telemetry['SessionTime'].iloc[0]
            session_time_last = telemetry['SessionTime'].iloc[constant_data.index[0] * 40]
            print(f"Sürücü {driver_short_name} yarış dışı kaldı. SessionTime: {session_time_last}")

            new_stream_data.append({
                'Time': session_time_first,
                'Driver': driver,
                'Position': driver_info.GridPosition,
                'GapToLeader': None,
                'IntervalToPositionAhead': None
            })
            
            new_stream_data.append({
                'Time': session_time_last,
                'Driver': driver,
                'Position': driver_info.Position,
                'GapToLeader': None,
                'IntervalToPositionAhead': None
            })

            new_laps_data.append({
                'Time': laps.iloc[0].Time,
                'Driver': driver,
                'NumberOfLaps': 1,
                'NumberOfPitStops': 0,
                'PitOutTime': None,
                'PitInTime': None,
                'Sector1Time': None,
                'Sector2Time': None,
                'Sector3Time': None,
                'Sector1SessionTime': None,
                'Sector2SessionTime': None,
                'Sector3SessionTime': None,
                'SpeedI1': None,
                'SpeedI2': None,
                'SpeedFL': None,
                'SpeedST': None,
                'IsPersonalBest': "FALSE",
            })

    stream_data = pd.concat([stream_data, pd.DataFrame(new_stream_data)])
    laps_data = pd.concat([laps_data, pd.DataFrame(new_laps_data)])

    laps_data.insert(2, 'DriverName', laps_data['Driver'].map(driver_enum))
    laps_data.insert(3, 'TeamColor', laps_data['Driver'].map(lambda x: "#" + session.get_driver(x).TeamColor))

    stream_data.insert(2, 'DriverName', stream_data['Driver'].map(driver_enum))

    laps_data = convert_timedelta_to_str(laps_data)
    laps_data = convert_special_values_to_null(laps_data)

    stream_data = convert_timedelta_to_str(stream_data)
    stream_data = convert_special_values_to_null(stream_data)

    # Tamamlanan tur ve sürücü durumu verilerini ekleyin
    completed_laps_data = {}
    driver_status_data = {}

    for driver in session.drivers:
        laps = session.laps.pick_driver(driver)
        completed_laps_data[driver] = len(laps)
        driver_status_data[driver] = "Finished" if len(laps) == session.total_laps else "+1 Lap" if len(laps) == session.total_laps - 1 else "DNF"

    #Find session end time by checking last lap time last driver finished is end of session
    total_laps = session.total_laps
    last_lap_data = laps_data[laps_data['NumberOfLaps'] == total_laps]
    session_end_time = last_lap_data['Time'].max()

    weather_data = session.weather_data
    weather_data = convert_timedelta_to_str(weather_data)
    weather_data = convert_special_values_to_null(weather_data)

    weather_data_json = [
        {
            'Time': time,
            'Rainfall': rainfall,
        }
        for time, rainfall in zip(weather_data['Time'], weather_data['Rainfall'])
    ]

    return json({
        'total_laps': total_laps,
        'session_start_time': str(session.session_start_time.total_seconds()),
        'session_end_time': str(session_end_time),
        'completed_laps': completed_laps_data,
        'driver_status': driver_status_data,
        'laps_data': laps_data.to_dict(orient='records'),
        'stream_data': stream_data.to_dict(orient='records'),
        'track_status': track_status_json,
        'weather_data': weather_data_json
    })


@app.route('/telemetry/<year:int>/<session_type>', methods=['GET'])
async def telemetry(request, year, session_type):
    session = load_session(year, 'Silverstone', session_type)
    
    # Get unique driver codes
    driver_codes = session.laps['Driver'].unique()
    results = {}

    async def process_driver(driver_code):
        laps = session.laps.pick_driver(driver_code)
        car_data = laps.get_car_data()
        pos_data = laps.get_pos_data()

        # Convert SessionTime to total seconds
        car_data['SessionTime (s)'] = car_data['SessionTime'].dt.total_seconds()
        pos_data['SessionTime (s)'] = pos_data['SessionTime'].dt.total_seconds()
        
        # Calculate lap start and end times
        laps_info = []
        driver_info = session.get_driver(driver_code)

        for i in range(len(laps)):
            lap = laps.iloc[i]

            lap_number = lap['LapNumber']
            lap_start_time = session.session_start_time.total_seconds() if i == 0 else laps_info[-1]['LapEndTime']
            lap_end_time = lap['Time'].total_seconds()

            try:
                lap_duration = lap['LapTime'].total_seconds() if not pd.isnull(lap['LapTime']) else None
            except IndexError:
                lap_duration = None

            if lap_duration is None:
                # Use telemetry data to calculate lap duration if LapTime is missing
                telemetry_data = laps.pick_lap(lap_number).get_car_data()
                if not telemetry_data.empty:
                    lap_start_time = telemetry_data.iloc[0]['SessionTime'].total_seconds() if i == 0 else lap_start_time
                    lap_end_time = telemetry_data.iloc[-1]['SessionTime'].total_seconds()
                    lap_duration = lap_end_time - lap_start_time
                else:
                    # Fallback: Estimate lap duration using the average of surrounding laps
                    previous_laps = laps.iloc[max(0, lap_number - 5):lap_number - 1]
                    next_laps = laps.iloc[lap_number:min(lap_number + 5, len(laps))]
                    surrounding_laps = pd.concat([previous_laps, next_laps])
                    estimated_duration = surrounding_laps['LapTime'].mean().total_seconds() if not surrounding_laps['LapTime'].isnull().all() else 30
                    lap_duration = estimated_duration

            lap_info = {
                'LapNumber': lap_number,
                'LapStartTime': lap_start_time,
                'LapEndTime': lap_end_time,
                'LapDuration': lap_duration,
                'TeamColor': "#" + driver_info.TeamColor,
            }
            laps_info.append(lap_info)

        # Telemetry data for each lap
        def get_telemetry_for_lap(lap_start_time, lap_end_time):
            lap_telemetry_car = car_data[(car_data['SessionTime (s)'] >= lap_start_time) & (car_data['SessionTime (s)'] < lap_end_time)]
            lap_telemetry_pos = pos_data[(pos_data['SessionTime (s)'] >= lap_start_time) & (pos_data['SessionTime (s)'] < lap_end_time)]
            return lap_telemetry_car, lap_telemetry_pos

        for lap in laps_info:
            lap_telemetry_car, lap_telemetry_pos = get_telemetry_for_lap(lap['LapStartTime'], lap['LapEndTime'])

            adjusted_points = adjust_coordinates(
                lap_telemetry_pos['X'].values, 
                lap_telemetry_pos['Y'].values, 
                REFERENCE_X[0], 
                REFERENCE_Y[0], 
                get_scale_factor(PREDEFINED_GLOBAL_MIN_X, PREDEFINED_GLOBAL_MAX_X, PREDEFINED_GLOBAL_MIN_Y, PREDEFINED_GLOBAL_MAX_Y)
            )

            lap['Telemetry'] = {
                'GPS_Coordinates': adjusted_points,
                'Speed': lap_telemetry_car['Speed'].values.tolist(),
                'Brake': lap_telemetry_car['Brake'].values.tolist(),
                'RPM': lap_telemetry_car['RPM'].values.tolist(),
                'SessionTime': lap_telemetry_car['SessionTime (s)'].values.tolist()
            }

        results[driver_code] = laps_info

    tasks = [process_driver(driver_code) for driver_code in driver_codes]
    await asyncio.gather(*tasks)

    return json(results)

# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, access_log=True, auto_reload=True, fast=True)