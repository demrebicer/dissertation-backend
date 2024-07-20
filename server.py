import gzip
from sanic import Sanic, response
from sanic.response import json
from sanic_cors import CORS
import fastf1
from cachetools import TTLCache, cached
import pandas as pd
import numpy as np
import fastf1.api
import asyncio
from sanic_gzip import Compress
from constants import *
from sanic.exceptions import ServiceUnavailable
import httpx
import sqlite3
import ujson
import os

# Enable cache
fastf1.Cache.enable_cache('f1cache')

# Initialize Sanic app
app = Sanic("F1TelemetryAPI")
CORS(app)  # Enable CORS for all routes
compress = Compress()

# Create caches for different routes
telemetry_cache = TTLCache(maxsize=100, ttl=86400)

# Initialize SQLite connection
conn = sqlite3.connect('f1data.sqlite')
cursor = conn.cursor()

# Create table for storing API responses
cursor.execute('''
CREATE TABLE IF NOT EXISTS api_responses (
    route TEXT PRIMARY KEY,
    response TEXT
)
''')
conn.commit()

@app.on_request
# @compress.compress()
async def check_ergast_api_status(request):
    route = request.path
    async with httpx.AsyncClient(timeout=5) as client:
        print("Ergast API Status is checking...")
        try:
            response = await client.get('https://ergast.com/api/f1/2021/10/results.json')
            if response.status_code != 200:
                raise ServiceUnavailable("Ergast API is not available")
        except httpx.RequestError:
            cached_response = get_response_from_db(route)

            if cached_response:
                cached_response = ujson.loads(cached_response)
                return json(cached_response)
            else:
                raise ServiceUnavailable(
                    "Ergast API is not available and no cached response found")

def save_response_to_db(route, response):
    cursor.execute(
        'REPLACE INTO api_responses (route, response) VALUES (?, ?)', (route, response))
    conn.commit()

def get_response_from_db(route):
    cursor.execute(
        'SELECT response FROM api_responses WHERE route = ?', (route,))
    row = cursor.fetchone()
    return row[0] if row else None

@app.middleware('response')
async def save_response(request, response):
    if response.status == 200 and response.content_type == 'application/json':
        try:
            # Yanıtın gzip sıkıştırılmış olup olmadığını kontrol edin
            if response.headers.get('Content-Encoding') == 'gzip':
                response_body = gzip.decompress(response.body)
                response_body = response_body.decode('utf-8')
            else:
                response_body = response.body.decode('utf-8')
            
            save_response_to_db(request.path, response_body)
        except (UnicodeDecodeError, OSError) as e:
            # Hata ayıklama için yanıt gövdesinin ilk 100 baytını yazdırın
            print(f"Failed to decode response body for route {request.path}. Error: {e}. Response body (first 100 bytes): {response.body[:100]}")
        except Exception as e:
            # Diğer olası hataları yakalayın ve bildirin
            print(f"An unexpected error occurred for route {request.path}. Error: {e}")

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
        [((x - ref_x) * scale_factor), 0, ((y - ref_y) * scale_factor)]
        for x, y in zip(x_coordinates, y_coordinates)
    ]
    return adjusted_points

def convert_timedelta_to_str(df):
    for column in df.select_dtypes(include=['timedelta']):
        df[column] = df[column].apply(lambda x: str(
            x.total_seconds()) if not pd.isnull(x) else None)
    return df

def convert_special_values_to_null(df):
    df = df.replace([pd.NaT, np.nan], None)
    return df

@app.get('/timing/<year:int>/<session_type>')
@compress.compress()
async def get_timing(request, year, session_type):
    session = load_session(year, 'Silverstone', session_type)
    session_drivers = session.drivers

    driver_enum = {driver: session.get_driver(
        driver).Abbreviation for driver in session.drivers}

    laps_data, stream_data = fastf1.api.timing_data(session.api_path)
    track_status = fastf1.api.track_status_data(session.api_path)
    track_status['Time'] = [x.total_seconds() for x in track_status['Time']]
    track_status_json = [{'Time': time, 'Status': status, 'Message': message} for time, status, message in zip(
        track_status['Time'], track_status['Status'], track_status['Message'])]

    laps_drivers = set(laps_data['Driver'].unique())
    stream_drivers = set(stream_data['Driver'].unique())

    laps_missing_drivers = set(session_drivers) - laps_drivers
    stream_missing_drivers = set(session_drivers) - stream_drivers
    missing_drivers = laps_missing_drivers.union(stream_missing_drivers)

    new_stream_data = []
    new_laps_data = []

    for driver in missing_drivers:
        driver_info = session.get_driver(driver)
        driver_short_name = driver_info.Abbreviation
        laps = session.laps.pick_driver(driver)
        lap = laps.iloc[0]
        telemetry = lap.get_telemetry()
        telemetry_data = telemetry[['RPM', 'Speed',
                                    'nGear', 'Throttle', 'Brake', 'DRS']]
        same_data_count = (telemetry_data.shift() == telemetry_data).all(
            axis=1).astype(int).groupby(telemetry_data.index // 40).sum()
        constant_data = same_data_count[same_data_count == 40]

        if not constant_data.empty:
            session_time_first = telemetry['SessionTime'].iloc[0]
            session_time_last = telemetry['SessionTime'].iloc[constant_data.index[0] * 40]

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
    laps_data.insert(3, 'TeamColor', laps_data['Driver'].map(
        lambda x: "#" + session.get_driver(x).TeamColor))
    stream_data.insert(2, 'DriverName', stream_data['Driver'].map(driver_enum))

    laps_data = convert_timedelta_to_str(laps_data)
    laps_data = convert_special_values_to_null(laps_data)

    stream_data = convert_timedelta_to_str(stream_data)
    stream_data = convert_special_values_to_null(stream_data)

    completed_laps_data = {driver: len(
        session.laps.pick_driver(driver)) for driver in session.drivers}
    driver_status_data = {
        driver: "Finished" if len(session.laps.pick_driver(driver)) == session.total_laps else "+1 Lap" if len(
            session.laps.pick_driver(driver)) == session.total_laps - 1 else "DNF"
        for driver in session.drivers
    }

    total_laps = session.total_laps
    last_lap_data = laps_data[laps_data['NumberOfLaps'] == total_laps]
    session_end_time = last_lap_data['Time'].max()

    weather_data = session.weather_data
    weather_data = convert_timedelta_to_str(weather_data)
    weather_data = convert_special_values_to_null(weather_data)

    weather_data_json = [{'Time': time, 'Rainfall': rainfall} for time, rainfall in zip(
        weather_data['Time'], weather_data['Rainfall'])]

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
@compress.compress()
async def telemetry(request, year, session_type):
    session = load_session(year, 'Silverstone', session_type)
    drivers = session.drivers

    def process_driver_data(driver_code):
        laps = session.laps.pick_driver(driver_code)
        car_data = laps.get_car_data()
        pos_data = laps.get_pos_data()

        pos_data = pos_data.sort_values(by='SessionTime')
        car_data = car_data.sort_values(by='SessionTime')

        telemetry = pd.merge_asof(
            pos_data, car_data, on='SessionTime', direction='nearest')
        telemetry['SessionTime (s)'] = telemetry['SessionTime'].dt.total_seconds(
        )
        adjusted_points = adjust_coordinates(
            telemetry['X'].values,
            telemetry['Y'].values,
            REFERENCE_X[0],
            REFERENCE_Y[0],
            get_scale_factor(PREDEFINED_GLOBAL_MIN_X, PREDEFINED_GLOBAL_MAX_X,
                             PREDEFINED_GLOBAL_MIN_Y, PREDEFINED_GLOBAL_MAX_Y)
        )
        telemetry['AdjustedCoordinates'] = list(adjusted_points)
        telemetry.rename(columns={'SessionTime (s)': 'timestamp',
                         'AdjustedCoordinates': 'coordinates'}, inplace=True)
        formatted_telemetry_list = telemetry[[
            'timestamp', 'coordinates', 'Brake', 'RPM']].to_dict('records')
        return formatted_telemetry_list

    async def process_driver(driver):
        driver_info = session.get_driver(driver)
        driver_code = driver_info.Abbreviation
        driver_data = await asyncio.to_thread(process_driver_data, driver_code)
        return {
            "id": driver_code,
            "teamColor": "#" + driver_info.TeamColor,
            "path": driver_data
        }

    results = {
        "cars": await asyncio.gather(*(process_driver(driver) for driver in drivers))
    }

    return json(results)

# Run the app
if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, access_log=True, auto_reload=True, fast=True)
