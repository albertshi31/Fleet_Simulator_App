import json
from Dispatcher import Dispatcher
from Passenger import Passenger
from Kiosk import Kiosk
from helper_functions import create_pixel_grid, latlng_to_xypixel, xypixel_to_latlng, get_locations_precalculated_kiosks
import pandas as pd
import time
from random import random

with open("InitSimTestData_Trenton.json", "r") as f:
    received_data = json.load(f)

center_coordinates = received_data['center_coordinates']
kiosks_dict = received_data['kiosks_dict']
routes_dict = received_data['routes_dict']
fleetsize = int(received_data['fleetsize'])
modesplit = .05
pax_waittime_threshold = int(received_data['pax_waittime_threshold'])
max_circuity = float(received_data['max_circuity']) / 100
MAX_CAPACITY = 2
polylinesGeoJSON = received_data['polylinesGeoJSON']
TIME_STEP = 10

lst_vehicle = []
lst_kiosk_pixels = []
lst_kiosk = []
lst_kiosk_dict_animation = []
kiosk_id = 1
for key, value in kiosks_dict.items():
    name, category, lat, lng = value['name'], value['category'], value['lat'], value['lng']
    xpixel, ypixel = latlng_to_xypixel(lat, lng)
    lst_kiosk_pixels.append((xpixel, ypixel))
    new_kiosk = Kiosk(kiosk_id, name, lat, lng, xpixel, ypixel)
    lst_kiosk.append(new_kiosk)
    lst_kiosk_dict_animation.append({'coordinates': [lng, lat], 'msg': str(new_kiosk)})
    kiosk_id += 1

lst_all_passengers_within_ODD = []
for filename in ['34_NewJersey/2020_OriginPixel34021_1.csv', '34_NewJersey/2020_OriginPixel34021_2.csv']:
    df = pd.read_csv("local_static/" + filename)
    curr_lst_pax = [Passenger(personID, lat, lng, dest_lat, dest_lng, oxcoord, oycoord, dxcoord, dycoord, odeparturetime, max_circuity) for personID, lat, lng, dest_lat, dest_lng, oxcoord, oycoord, dxcoord, dycoord, odeparturetime in \
    zip(df['Person ID'], df['OLat'], df['OLon'], df['DLon'], df['DLon'], df['OXCoord'], df['OYCoord'], df['DXCoord'], df['DYCoord'], df['ODepartureTime']) if (oxcoord, oycoord) in lst_kiosk_pixels and (dxcoord, dycoord) in lst_kiosk_pixels and (oxcoord, oycoord) != (dxcoord, dycoord)]
    lst_all_passengers_within_ODD.extend(curr_lst_pax)

df_departure_times = pd.DataFrame([pax.getDepartureTime() for pax in lst_all_passengers_within_ODD], columns=["DepartureTime"])
print("Num Pax", len(lst_all_passengers_within_ODD))

bins = range(0, max(df_departure_times['DepartureTime'])+TIME_STEP, TIME_STEP)
times = pd.Series(df_departure_times['DepartureTime'])
groups = pd.cut(times, bins=bins)
timestep_departure_counts = groups.value_counts(sort=False).to_list()
max_timestep_count = max(timestep_departure_counts)
modesplits_by_timestep = []
for count in timestep_departure_counts:
    if count == 0:
        modesplits_by_timestep.append(0)
    else:
        modesplits_by_timestep.append(min(1, (modesplit * max_timestep_count) / count))

print(modesplits_by_timestep)

lst_all_passengers = []
for pax in lst_all_passengers_within_ODD:
    modesplit = modesplits_by_timestep[pax.getDepartureTime()//TIME_STEP]
    if random() <= modesplit:
        lst_all_passengers.append(pax)

lst_all_passengers.sort(key=lambda pax:pax.odeparturetime)

# get the start datetime
start_time = time.time()

# Create Dispatcher object
dispatcher = Dispatcher(lst_all_passengers, lst_kiosk, lst_vehicle, pax_waittime_threshold, routes_dict, fleetsize, MAX_CAPACITY, TIME_STEP)

# Run the simulation
dispatcher.runSimulation()

# Save the simulation output into animtion data file
EOD_metrics = dispatcher.getEODMetrics()
timeframe_metrics = dispatcher.getTimeframeMetrics()
trips = dispatcher.getAnimationTrips()
kiosk_metrics = dispatcher.getKioskTimeframeMetrics()
looplength = dispatcher.getFinalTimeInSec()

animation_data_file_dict = {
    "center_coordinates": center_coordinates,
    "TIME_STEP": TIME_STEP,
    "EOD_metrics": EOD_metrics,
    "timeframe_metrics": timeframe_metrics,
    "trips": trips,
    "kiosks": lst_kiosk_dict_animation,
    "kiosk_metrics": kiosk_metrics,
    "road_network": polylinesGeoJSON,
    "looplength": looplength,
}

with open("AnimationDataFile.json", "w") as f:
    json.dump(animation_data_file_dict, f)

# get execution time
runtime=time.time()-start_time
