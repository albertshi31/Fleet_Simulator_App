from flask import Flask, render_template, make_response, request, redirect, url_for
import requests
from sys import argv, stderr, exit
import argparse
import json
import os
import time
import compress_json
import addfips
from zipfile import ZipFile
import csv
import shutil
from DepotMatrixAndBuildings import DepotMatrixAndBuildings
#from SortRoutesByPriority import Graph
import h3
from random import sample, random, randrange
import polyline
import numpy as np
from ratelimiter import RateLimiter

from Dispatcher import Dispatcher
from Passenger import Passenger
from Kiosk import Kiosk

from helper_functions import create_pixel_grid, latlng_to_xypixel, xypixel_to_latlng, get_locations_kiosks_in_regions
import pandas as pd

global THIS_FOLDER
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
global list_of_unzipped_files
global person_trip_lst_latlngs
global person_trips_in_kiosk_network
global person_trips_csv_header
global person_trip_lst_latlngs_by_h3_index
global lst_h3_indices
global h3_resolution
h3_resolution = 8

from floyd_warshall import initialise, constructPath, floydWarshall, printPath

app = Flask("__main__", template_folder=os.path.join(THIS_FOLDER, "templates"))

@app.route("/test")
def test():
    html = render_template("test.html")
    response = make_response(html)
    return response

@app.route("/")
def landing_page():
    odd_choices = []
    dir_names = os.listdir("user_data")
    for dir_name in dir_names:
        with open(os.path.join("user_data", dir_name, "meta_data.json"), "r") as f:
            meta_data = json.load(f)
            meta_data["dir"] = dir_name
            odd_choices.append(meta_data)
    html = render_template("landing_page.html", odd_choices = odd_choices)
    response = make_response(html)
    return response


# TODO: Does not work for multi-polygons yet
@app.route("/setup-interactive")
def setup_interactive():
    odd_choice_dir = request.args.get("odd_choice")
    # If no ODD is selected, make sure to choose new folder name to save it in
    if odd_choice_dir is None:
        random_dir_name = randrange(10000, 99999)
        dir_names = os.listdir("user_data")
        while random_dir_name in dir_names:
            random_dir_name = randrange(10000, 99999)
        odd_choice_dir = random_dir_name

    token = 'pk.eyJ1IjoiZ2xhbmlld3NraSIsImEiOiJja28weW13eHEwNWNwMnZzNTZyZzRrMDN4In0.P2-EylpYdzmCgdASgAKC5g'
    jawg_accessToken = 'uUILlBVmedZhJqrmWPczZMS9ytaAuTPvGqX5Z3bCC30qlHe2DSJCQZABdbznjyGr'
    html = render_template("setup-interactive.html", mapbox_access_token = token, jawg_accessToken = jawg_accessToken, odd_choice_dir = odd_choice_dir)
    response = make_response(html)
    return response

# Render ODD in setup_interactive page
@app.route("/load_odd")
def load_ODD():
    dir_name = request.args.get("odd_choice_dir")
    response = {}
    if dir_name in os.listdir("user_data"):
        with open(os.path.join("user_data", dir_name, "setup_interactive.json"), "r") as f:
            response = json.load(f)
        response["status"] = "FOUND"
    else:
        response["status"] = "NOT FOUND"
    return response

# Extract zipped files that contain person trips within the county
def extract_person_trip_files_helper(lst_county_state):
    global list_of_unzipped_files
    list_of_unzipped_files = []
    af = addfips.AddFIPS()
    for county_name, state_name in lst_county_state:
        fips_code = af.get_county_fips(county_name, state=state_name)
        global THIS_FOLDER
        for filename in os.listdir(os.path.join(THIS_FOLDER, "local_static", "StateTripFiles_Compressed")):
            if state_name.replace(" ", "") in filename:
                filepath = os.path.join(THIS_FOLDER, "local_static", "StateTripFiles_Compressed", filename)
                print(filepath)
                with ZipFile(filepath, 'r') as f:
                    list_of_zipped_files = ZipFile.namelist(f)
                    list_of_files_to_unzip = [filename for filename in list_of_zipped_files if fips_code in filename]
                    f.extractall(os.path.join(THIS_FOLDER, "local_static"), members = list_of_files_to_unzip)
                    list_of_unzipped_files.extend(list_of_files_to_unzip)
                break

def isInBoundsLatLng(lat, lng, min_lat, max_lat, min_lng, max_lng):
    result1 = lat >= min_lat and lat <= max_lat
    result2 = lng >= min_lng and lng <= max_lng
    return result1 and result2

#decode an encoded string
def decode(encoded):
  #six degrees of precision in valhalla
  inv = 1.0 / 1e6;

  decoded = []
  previous = [0,0]
  i = 0
  #for each byte
  while i < len(encoded):
    #for each coord (lat, lon)
    ll = [0,0]
    for j in [0, 1]:
      shift = 0
      byte = 0x20
      #keep decoding bytes until you have this coord
      while byte >= 0x20:
        byte = ord(encoded[i]) - 63
        i += 1
        ll[j] |= (byte & 0x1f) << shift
        shift += 5
      #get the final value adding the previous offset and remember it for the next
      ll[j] = previous[j] + (~(ll[j] >> 1) if ll[j] & 1 else (ll[j] >> 1))
      previous[j] = ll[j]
    #scale by the precision and chop off long coords, keep positions as lat, lon
    decoded.append([float('%.6f' % (ll[0] * inv)), float('%.6f' % (ll[1] * inv))])
  #hand back the list of coordinates
  return decoded


def getTimestamps(lst_route_leg_maneuvers, route_duration, len_route_latlngs):
    raw_timestamps = []
    for maneuver in lst_route_leg_maneuvers:
        number_of_timestamp_slots = maneuver['end_shape_index'] - maneuver['begin_shape_index']
        maneuver_time = maneuver['time']
        split_times = []
        for i in range(number_of_timestamp_slots):
            split_times.append(maneuver_time/number_of_timestamp_slots)
        raw_timestamps.extend(split_times)
    # timestamps = list(np.cumsum(raw_timestamps))
    raw_timestamps.insert(0, 0)
    assert len(raw_timestamps) == len_route_latlngs, "The number of timestamps should be equal to number of latlngs coordinates in polyline"
    return raw_timestamps


def getRouteMeta(latlng1, latlng2):
    loc = "{},{};{},{}".format(latlng1[1], latlng1[0], latlng2[1], latlng2[0])
    url = "http://localhost:5000/route/v1/driving/"
    r = requests.get(url + loc + "?overview=full&annotations=true&exclude=motorway") #&exclude=motorway
    res = r.json()
    raw_timestamps = res['routes'][0]['legs'][0]['annotation']['duration']
    raw_timestamps.insert(0, 0) # raw_timestamps gives list of times you should add to previous sum
    route_timestamps = [float(elem) for elem in list(np.cumsum(raw_timestamps))]

    route_latlngs = polyline.decode(res['routes'][0]['geometry'])
    route_distance = res['routes'][0]['distance']
    route_duration = res['routes'][0]['duration']

    return route_latlngs, route_distance, route_duration, route_timestamps
    #
    # valhalla_route_dict = {
    #   "locations": [
    #     {
    #       "lat": latlng1[0],
    #       "lon": latlng1[1]
    #     },
    #     {
    #       "lat": latlng2[0],
    #       "lon": latlng2[1]
    #     }
    #   ],
    #   "costing": "auto",
    #   "costing_options": {
    #     "auto": {
    #       "use_highways": 0,
    #       "use_tolls": 0,
    #       "top_speed": 45 * 1.609, # convert from mph to kph
    #     }
    #   },
    #   "exclude_locations": avoidLocations,
    #   "units": "miles",
    #   "id": "my_work_route"
    # }
    # url = "https://valhalla1.openstreetmap.de/route?json={}".format(json.dumps(valhalla_route_dict))
    # print("URL", url)
    # r = requests.get(url)
    # if r.status_code != 200:
    #     print("VALHALLA RETURNED ERROR", r.status_code)
    #     print(r.json()['error'])
    #     return {}
    # res = r.json()
    # route_latlngs = decode(res['trip']['legs'][0]['shape'])
    # route_distance = res['trip']['summary']['length']
    # route_duration = res['trip']['summary']['time']
    # route_timestamps = getTimestamps(res['trip']['legs'][0]['maneuvers'], route_duration, len(route_latlngs))
    #
    # return route_latlngs, route_distance, route_duration, route_timestamps

@app.route("/get_nearest_coordinates")
def getNearestStreetCoordinate():
    lat = float(request.args.get("lat"))
    lng = float(request.args.get("lng"))
    loc = "{},{}".format(lng, lat)
    url = "http://localhost:5000/nearest/v1/driving/"
    r = requests.get(url + loc)
    if r.status_code != 200:
        return {}
    res = r.json()
    lng, lat = res['waypoints'][0]['location']
    name = res['waypoints'][0]['name']
    return { "lat": lat, "lng": lng, "name": name }

@app.route("/get_route", methods=['POST'])
def get_route():
    received_data = request.get_json()
    lst_latlngs = received_data['lst_latlngs']

    route_matrix = {}

    for latlng1 in lst_latlngs:
        for latlng2 in lst_latlngs:
            key = str([(latlng1[0], latlng1[1]), (latlng2[0], latlng2[1])])
            route_latlngs, route_distance, route_duration, route_timestamps = getRouteMeta(latlng1, latlng2)
            route_matrix[key] = {
                'key': key,
                'latlngs': route_latlngs,
                'distance': route_distance,
                'duration': route_duration,
                'timestamps': route_timestamps
            }
    return route_matrix

    # rate_limiter = RateLimiter(max_calls=1, period=1)
    # with rate_limiter:
    #     str_latlng1 = ','.join(str(x) for x in latlng1)
    #     str_latlng2 = ','.join(str(x) for x in latlng2)
    #     key = '{};{}'.format(str_latlng1, str_latlng2)
    #     route_latlngs, route_distance, route_duration, route_timestamps = getRouteMeta(latlng1, latlng2, avoidLocations)
    # response = {
    #     'key': key,
    #     'latlngs': route_latlngs,
    #     'distance': route_distance,
    #     'duration': route_duration,
    #     'timestamps': route_timestamps
    # }
    # print(response)
    # return response

@app.route("/extract_files", methods=['POST'])
def extract_person_trip_files():
    received_data = request.get_json()

    lst_county_state = received_data["lst_county_state"]
    deduped_lst_county_state = []
    [deduped_lst_county_state.append(x) for x in lst_county_state if x not in deduped_lst_county_state]
    print(deduped_lst_county_state)

    extract_person_trip_files_helper(deduped_lst_county_state)

    print("EXTRACTED FILES")

    return {"status": "SUCCESS"}

@app.route("/get_heatmap")
def get_heatmap():
    global person_trip_lst_latlngs
    pixel_dict = {}
    for lat, lng in person_trip_lst_latlngs:
        xpixel, ypixel = latlng_to_xypixel(lat, lng)
        if (xpixel, ypixel) in pixel_dict:
            pixel_dict[(xpixel, ypixel)] += 1
        else:
            pixel_dict[(xpixel, ypixel)] = 1

    heatmap_data = {"max": 0, "min": 0, "data": []}
    max = 0
    for key, value in pixel_dict.items():
        if value > max:
            max = value
        lat, lng = xypixel_to_latlng(key[0], key[1])
        new_h3_heatmap_entry = {"lat": lat, "lng": lng, "count": value}
        heatmap_data["data"].append(new_h3_heatmap_entry)
    heatmap_data["max"] = max

    return heatmap_data


@app.route("/get_pixel_grid")
def get_pixel_grid():
    north_lat = float(request.args.get("north"))
    south_lat = float(request.args.get("south"))
    east_lng = float(request.args.get("east"))
    west_lng = float(request.args.get("west"))
    feature_collection = create_pixel_grid(north_lat, south_lat, east_lng, west_lng)

    return { "pixel_grid_geojson": feature_collection }

@app.route("/get_geocoded_address")
def get_geocoded_address():
    name = request.args.get("name")
    address = request.args.get("address")

    # api-endpoint
    URL = "http://localhost:8080/search.php"

    # defining a params dict for the parameters to be sent to the API
    PARAMS = {'q': address}

    # sending get request and saving the response as response object
    r = requests.get(url = URL, params = PARAMS)

    # extracting data in json format
    data = r.json()

    print(data)
    success = True
    lat, lng = 0, 0
    try:
        lat, lng = data[0]['lat'], data[0]['lon']
    except:
        success = False

    response = {
        "success": success,
        "name": name,
        "lat": lat,
        "lng": lng
    }

    return response


@app.route("/draw_precalculated_kiosks", methods=['POST'])
def draw_precalculated_kiosks():
    received_data = request.get_json()

    north_lat = float(received_data["north"])
    south_lat = float(received_data["south"])
    east_lng = float(received_data["east"])
    west_lng = float(received_data["west"])
    regions_osm_geojsons = received_data["regions_osm_geojsons"]

    # Get all possible kiosk locations (whose centroids lie within the regions created by user)
    lst_kiosk_pixels = get_locations_kiosks_in_regions(north_lat, south_lat, east_lng, west_lng, regions_osm_geojsons)

    # Track kiosk metrics
    global list_of_unzipped_files

    lst_trips_within_odd = []
    for filename in list_of_unzipped_files:
        print(filename)
        df = pd.read_csv("local_static/" + filename)
        lst_trips = [(oxcoord, oycoord, dxcoord, dycoord) for oxcoord, oycoord, dxcoord, dycoord, dist in zip(df['OXCoord'], df['OYCoord'], df['DXCoord'], df['DYCoord'], df['GCDistance']) \
        if (oxcoord, oycoord) in lst_kiosk_pixels and (dxcoord, dycoord) in lst_kiosk_pixels and dist > 0.707]
        lst_trips_within_odd.extend(lst_trips)

    print(len(lst_trips_within_odd))
    # Instantiate dict with kiosk metrics we will track
    dict_pixel_info = {}
    for xypixel in lst_kiosk_pixels:
        dict_pixel_info[xypixel] = {
            "sumOTrips": 0,
            "sumDTrips": 0
        }

    for oxcoord, oycoord, dxcoord, dycoord in lst_trips_within_odd:
        opixel = (oxcoord, oycoord)
        dict_pixel_info[opixel]["sumOTrips"] += 1
        dpixel = (dxcoord, dycoord)
        dict_pixel_info[dpixel]["sumDTrips"] += 1

    # Only return the top kiosks that serve at least 90% of total oTrips
    sumOTrips = 0
    result_lst_kiosk_pixels = []
    print("BEGIN SORT")
    for pixel, value in sorted(dict_pixel_info.items(), key=lambda item: item[1]["sumOTrips"], reverse=True):
        result_lst_kiosk_pixels.append(pixel)
        sumOTrips += value["sumOTrips"]
        if sumOTrips/len(lst_trips_within_odd) >= 1:
            break
    print("END SORT")

    result_lst_marker_latlngs = []
    for xcoord, ycoord in result_lst_kiosk_pixels:
        lat, lng = xypixel_to_latlng(xcoord, ycoord)
        result_lst_marker_latlngs.append([lat, lng])

    # Convert dict keys to string
    stringify_dict_pixel_info = {}
    for key, value in dict_pixel_info.items():
        stringify_dict_pixel_info[str(key)] = value

    result = {
        "lst_marker_latlngs": result_lst_marker_latlngs,
        "numTripsInKioskNetwork": len(lst_trips_within_odd),
        "dict_pixel_info": stringify_dict_pixel_info
    }

    print(result)

    return result

@app.route("/save_ODD", methods=['POST'])
def save_ODD():
    received_data = request.get_json()

    odd_choice_dir = received_data["odd_choice_dir"]

    os.mkdir(os.path.join("user_data", str(odd_choice_dir)))

    meta_data_dict = received_data["meta_data_dict"]

    with open(os.path.join("user_data", str(odd_choice_dir), "meta_data.json"), "w") as f:
        json.dump(meta_data_dict, f)

    setup_interactive_dict = received_data["setup_interactive_dict"]

    with open(os.path.join("user_data", str(odd_choice_dir), "setup_interactive.json"), "w") as f:
        json.dump(setup_interactive_dict, f)

    response = {
        "message": "Your ODD saved successfully."
    }
    return response

def getRouteDictFromPath(path, lst_latlngs, str_lst_latlngs, routes_dict):
    result = {}
    assert len(path) > 0, "There must be a path to every node from every other node"
    if len(path) == 1:
        idx = path[0]
        result = {'latlngs': [lst_latlngs[idx], lst_latlngs[idx]], 'distance': 0, 'duration': 0, 'timestamps': [0]}
    else:
        total_latlngs = []
        total_distance = 0
        total_duration = 0
        total_raw_timestamps = []
        list_of_tuples = list(zip(path, path[1:]))
        for first_idx, second_idx in list_of_tuples:
            key = '{};{}'.format(str_lst_latlngs[first_idx], str_lst_latlngs[second_idx])
            leg_data = routes_dict[key]
            total_latlngs.extend(leg_data['latlngs'])
            total_distance += leg_data['distance']
            total_duration += leg_data['duration']
            total_raw_timestamps.extend(leg_data['timestamps'])
        total_timestamps = list(np.cumsum(total_raw_timestamps))
        total_timestamps[-1] = total_duration
        result = {'latlngs': total_latlngs, 'distance': total_distance, 'duration': total_duration, 'timestamps': total_timestamps}
    return result


def getCompleteRoutesMatrix(lst_latlngs, routes_dict):
    return_complete_route_matrix = {}
    str_lst_latlngs = [",".join([str(lat), str(lng)]) for lat, lng in lst_latlngs]

    print(str_lst_latlngs)
    print(routes_dict)

    V = len(lst_latlngs)
    INF = 10**7
    graph = np.empty([V, V])
    for i in range(V):
        for j in range(V):
            if i == j:
                graph[i][j] = 0
            else:
                key1 = '{};{}'.format(str_lst_latlngs[i], str_lst_latlngs[j])
                key2 = '{};{}'.format(str_lst_latlngs[j], str_lst_latlngs[i])
                if key1 in routes_dict:
                    graph[i][j] = routes_dict[key1]['duration']
                    graph[j][i] = routes_dict[key1]['duration']
                    if not key2 in routes_dict:
                        routes_dict[key2] = routes_dict[key1]
                elif key2 in routes_dict:
                    graph[i][j] = routes_dict[key2]['duration']
                    graph[j][i] = routes_dict[key2]['duration']
                    if not key1 in routes_dict:
                        routes_dict[key1] = routes_dict[key2]
                else:
                    graph[i][j] = INF
    print("GRAPH")
    print(graph)

    MAXM = 100
    dis = [[-1 for i in range(MAXM)] for i in range(MAXM)]
    Next = [[-1 for i in range(MAXM)] for i in range(MAXM)]

    initialise(V, dis, Next, graph, INF)
    floydWarshall(V, Next, dis, INF)
    path = []

    for i in range(V):
        for j in range(V):
            print("Shortest path from {} to {}: ".format(str_lst_latlngs[i], str_lst_latlngs[j]), end = "")
            path = constructPath(i, j, graph, Next)
            printPath(path)
            return_complete_route_matrix['{};{}'.format(str_lst_latlngs[i], str_lst_latlngs[j])] = getRouteDictFromPath(path, lst_latlngs, str_lst_latlngs, routes_dict)
    return return_complete_route_matrix

"""
Function attempts to augment an ODD but code is not working as intended.
Inserting an error message does not run at all
Need to look at each input/parameter for Dispatcher 
"""
@app.route("/create_simulation", methods=['POST'])
def prepare_simulation():
    received_data = request.get_json()
    with open('received_data.txt', 'w') as test_file:
        test_file.write(json.dumps(received_data))
    odd_choice_dir = received_data['odd_choice_dir']
    center_coordinates = received_data['center_coordinates']
    kiosks_dict = received_data['kiosks_dict']
    routes_dict = received_data['routes_dict']
    fleetsize = int(received_data['fleetsize'])
    modesplit = float(received_data['modesplit']) / 100
    pax_waittime_threshold = int(received_data['pax_waittime_threshold'])
    max_circuity = float(received_data['max_circuity']) / 100
    MAX_CAPACITY = int(received_data['max_capacity'])
    polylinesGeoJSON = received_data['polylinesGeoJSON']
    TIME_STEP = 10

    # Initialize a bunch of lists and append kiosks, pixels, etc.
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

    # Creates passenger object for each row in a PersonTrip file (not present in the code, data may have been extracted locally)
    # Reads columns of data file --> takes all trips within a kiosk pixels and if the person actually went somewhere (destination coordinates are different from the origin coordinates) --> extend into the current passenger list
    lst_all_passengers_within_ODD = []
    for filename in list_of_unzipped_files:
        df = pd.read_csv("local_static/" + filename)
        curr_lst_pax = [Passenger(personID, lat, lng, dest_lat, dest_lng, oxcoord, oycoord, dxcoord, dycoord, odeparturetime, max_circuity) for personID, lat, lng, dest_lat, dest_lng, oxcoord, oycoord, dxcoord, dycoord, odeparturetime in \
        zip(df['Person ID'], df['OLat'], df['OLon'], df['DLon'], df['DLon'], df['OXCoord'], df['OYCoord'], df['DXCoord'], df['DYCoord'], df['ODepartureTime']) if (oxcoord, oycoord) in lst_kiosk_pixels and (dxcoord, dycoord) in lst_kiosk_pixels and (oxcoord, oycoord) != (dxcoord, dycoord)]
        lst_all_passengers_within_ODD.extend(curr_lst_pax)

    df_departure_times = pd.DataFrame([pax.getDepartureTime() for pax in lst_all_passengers_within_ODD], columns=["DepartureTime"])
    print("Num Pax", len(lst_all_passengers_within_ODD))

    # Some modesplit stuff
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

    print(len(groups), len(modesplits_by_timestep))

    lst_all_passengers = []
    for pax in lst_all_passengers_within_ODD:
        modesplit = modesplits_by_timestep[pax.getDepartureTime()//TIME_STEP]
        if random() <= modesplit:
            lst_all_passengers.append(pax)

    # Sort all passengers by departure time from origin
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

    # Creates a dictionary for all of the metrics
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

    # Creates the animation data file that is used to run the simulation
    with open(os.path.join("user_data", str(odd_choice_dir), "animation_data_file.json"), "w") as f:
        json.dump(animation_data_file_dict, f)

    # get execution time
    runtime=time.time()-start_time

    response = {
    'runtime': runtime,
    'odd_choice': odd_choice_dir
    }
    return response

# This visualizer is all pre-computed, and it just runs an animation whenever you run main.py
# This is not actually computing anything in realtime (the data and numbers are the same each time)
# All of the data is taken from animation_data_file.json, which is created above by Dispatcher
@app.route("/animation")
def animation():
    # raise Exception("intended error")
    odd_choice_dir = request.args.get("odd_choice")

    with open(os.path.join("user_data", str(odd_choice_dir), "animation_data_file.json"), "r") as f:
        animation_data_file_dict = json.load(f)

    # Retrieve all values from the data file (created by dispatcher)
    center_coordinates = animation_data_file_dict['center_coordinates']
    TIME_STEP = animation_data_file_dict['TIME_STEP']
    trips = animation_data_file_dict['trips']
    EOD_metrics = animation_data_file_dict['EOD_metrics']
    timeframe_metrics = animation_data_file_dict['timeframe_metrics']
    kiosks = animation_data_file_dict['kiosks']
    kiosk_metrics = animation_data_file_dict['kiosk_metrics']
    road_network = animation_data_file_dict['road_network']
    looplength = animation_data_file_dict['looplength']

    # Display the animation template
    html = render_template("index.html",
                            center_coordinates=center_coordinates,
                            time_step=TIME_STEP,
                            trips=trips,
                            kiosks=kiosks,
                            kiosk_metrics = kiosk_metrics,
                            road_network = road_network,
                            EOD_metrics = EOD_metrics,
                            timeframe_metrics = timeframe_metrics,
                            looplength = looplength)
    response = make_response(html)
    return response


@app.route("/graphs")
def graph_page():
    my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "metrics.json.gz")
    metrics = compress_json.load(my_file)

    my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "pax_left_vs_fleetsize.txt")
    with open(my_file, "r") as f:
        pax_left_vs_fleetsize_data = f.read()

    html = render_template("graphs.html", metrics = metrics, pax_left_vs_fleetsize_data = pax_left_vs_fleetsize_data)
    response = make_response(html)
    return response

def main(argv):
    parser = argparse.ArgumentParser(description='Create ODD and Simulate Trips')
    parser.add_argument('-t', '--testing', type = bool, help="only test simulate trips", default=False)
    args = parser.parse_args()
    print(args)

    if args.testing:
        CITY_NAME = "PERTH_AMBOY_TESTING"
        create_animation(CITY_NAME)

    app.run(host="0.0.0.0", port=8000, debug=False)
    # Go on http://localhost:8000/animation?city_choice=TRENTON_TESTING

#Comment out before updating PythonAnywhere
if __name__ == '__main__':
    main(argv)
