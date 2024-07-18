import fastf1
import pandas as pd

import fastf1.api

# FastF1'i initialize et ve cache directory'sini ayarla
fastf1.Cache.enable_cache('f1cache')

# Silverstone yarışını yükle (2021 sezonu, yarış kodu 10)
session = fastf1.get_session(2021, 'Silverstone', 'R')

# Verileri yükle
session.load()

session_drivers = session.drivers

# print(session.get_driver('44'))

# print(session.drivers)

print(session.get_driver('VET'))