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
from random import sample
import polyline
import numpy as np
from ratelimiter import RateLimiter

from Dispatcher import Dispatcher

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
@app.route("/choose_city")
def choosecity():
    html = render_template("choose_city.html")
    response = make_response(html)
    return response


@app.route("/setup")
def setup():
    html = render_template("setup.html")
    response = make_response(html)
    return response

# TODO: Does not work for multi-polygons yet
@app.route("/setup-interactive")
def setup_interactive():
    token = 'pk.eyJ1IjoiZ2xhbmlld3NraSIsImEiOiJja28weW13eHEwNWNwMnZzNTZyZzRrMDN4In0.P2-EylpYdzmCgdASgAKC5g'
    jawg_accessToken = 'uUILlBVmedZhJqrmWPczZMS9ytaAuTPvGqX5Z3bCC30qlHe2DSJCQZABdbznjyGr'
    html = render_template("setup-interactive.html", mapbox_access_token = token, jawg_accessToken = jawg_accessToken)
    response = make_response(html)
    return response

# Extract zipped files that contain person trips within the county
def extract_person_trip_files_helper(county_name, state_name):
    af = addfips.AddFIPS()
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
                global list_of_unzipped_files
                list_of_unzipped_files = list_of_files_to_unzip
            break

def isInBoundsLatLng(lat, lng, min_lat, max_lat, min_lng, max_lng):
    result1 = lat >= min_lat and lat <= max_lat
    result2 = lng >= min_lng and lng <= max_lng
    return result1 and result2

def filter_person_trip_files(list_of_unzipped_files):
    global person_trip_lst_latlngs
    global person_trip_lst_latlngs_by_h3_index
    person_trip_lst_latlngs_by_h3_index = {}
    global lst_h3_indices
    global h3_resolution
    global person_trips_in_kiosk_network
    global person_trips_csv_header
    person_trips_in_kiosk_network = []
    person_trip_lst_latlngs = []
    for filename in list_of_unzipped_files:
        with open(filename, 'r', encoding='utf-8-sig') as file:
            csvreader = csv.reader(file)
            header = next(csvreader)
            person_trips_csv_header = header
            lat_idx = header.index("OLat")
            long_idx = header.index("OLon")
            dest_lat_idx = header.index("DLat")
            dest_long_idx = header.index("DLon")
            gcdistance_idx = header.index("GCDistance")
            for row in csvreader:
                lat = float(row[lat_idx])
                lng = float(row[long_idx])
                dest_lat = float(row[dest_lat_idx])
                dest_lng = float(row[dest_long_idx])
                gcdistance = float(row[gcdistance_idx])
                origin_h3_index = h3.geo_to_h3(lat, lng, h3_resolution)
                dest_h3_index = h3.geo_to_h3(dest_lat, dest_lng, h3_resolution)
                if origin_h3_index in lst_h3_indices and dest_h3_index in lst_h3_indices and gcdistance > .707:
                    person_trip_lst_latlngs.append([lat, lng])
                    person_trip_lst_latlngs.append([dest_lat, dest_lng])
                    person_trips_in_kiosk_network.append(row)
                    if not origin_h3_index in person_trip_lst_latlngs_by_h3_index:
                        person_trip_lst_latlngs_by_h3_index[origin_h3_index] = [[lat, lng]]
                    else:
                        person_trip_lst_latlngs_by_h3_index[origin_h3_index].append([lat, lng])
                    if not dest_h3_index in person_trip_lst_latlngs_by_h3_index:
                        person_trip_lst_latlngs_by_h3_index[dest_h3_index] = [[dest_lat, dest_lng]]
                    else:
                        person_trip_lst_latlngs_by_h3_index[dest_h3_index].append([dest_lat, dest_lng])


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


def getRouteMeta(latlng1, latlng2, avoidLocations):
    # loc = "{},{};{},{}".format(latlng1[1], latlng1[0], latlng2[1], latlng2[0])
    # url = "http://127.0.0.1:5000/route/v1/driving/"
    # r = requests.get(url + loc + "?overview=full&annotations=true&exclude=motorway")
    # raw_timestamps = res['routes'][0]['legs'][0]['annotation']['duration']
    # raw_timestamps.insert(0, 0) # raw_timestamps gives list of times you should add to previous sum
    # route_timestamps = list(np.cumsum(raw_timestamps))
    #
    # route_latlngs = polyline.decode(res['routes'][0]['geometry'])
    # route_distance = res['routes'][0]['distance']
    # route_duration = res['routes'][0]['duration']

    valhalla_route_dict = {
      "locations": [
        {
          "lat": latlng1[0],
          "lon": latlng1[1]
        },
        {
          "lat": latlng2[0],
          "lon": latlng2[1]
        }
      ],
      "costing": "auto",
      "costing_options": {
        "auto": {
          "use_highways": 0,
          "use_tolls": 0,
          "top_speed": 45 * 1.609, # convert from mph to kph
        }
      },
      "exclude_locations": avoidLocations,
      "units": "miles",
      "id": "my_work_route"
    }
    url = "https://valhalla1.openstreetmap.de/route?json={}".format(json.dumps(valhalla_route_dict))
    print("URL", url)
    r = requests.get(url)
    if r.status_code != 200:
        print("VALHALLA RETURNED ERROR", r.status_code)
        print(r.json()['error'])
        return {}
    res = r.json()
    route_latlngs = decode(res['trip']['legs'][0]['shape'])
    route_distance = res['trip']['summary']['length']
    route_duration = res['trip']['summary']['time']
    route_timestamps = getTimestamps(res['trip']['legs'][0]['maneuvers'], route_duration, len(route_latlngs))

    return route_latlngs, route_distance, route_duration, route_timestamps

def getNearestStreetCoordinate(latlng1):
    loc = "{},{}".format(latlng1[1], latlng1[0])
    url = "http://127.0.0.1:5000/nearest/v1/driving/"
    r = requests.get(url + loc)
    if r.status_code != 200:
        return {}
    res = r.json()
    print(res)
    return "SUCCESS"

@app.route("/get_route", methods=['POST'])
def get_route():
    received_data = request.get_json()
    latlng1 = received_data['latlng1']
    latlng2 = received_data['latlng2']
    avoidLocations = received_data['avoidLocations']
    print(avoidLocations)

    rate_limiter = RateLimiter(max_calls=1, period=1)
    with rate_limiter:
        str_latlng1 = ','.join(str(x) for x in latlng1)
        str_latlng2 = ','.join(str(x) for x in latlng2)
        key = '{};{}'.format(str_latlng1, str_latlng2)
        route_latlngs, route_distance, route_duration, route_timestamps = getRouteMeta(latlng1, latlng2, avoidLocations)
    response = {
        'key': key,
        'latlngs': route_latlngs,
        'distance': route_distance,
        'duration': route_duration,
        'timestamps': route_timestamps
    }
    print(response)
    return response

@app.route("/extract_person_trip_files")
def extract_person_trip_files():
    county_name = request.args.get('county_name')
    state_name = request.args.get('state_name')

    extract_person_trip_files_helper(county_name, state_name)

    global list_of_unzipped_files

    input_datafeed_trip_data = []
    for trip_data_csv in list_of_unzipped_files:
        input_datafeed_trip_data.append("local_static/" + trip_data_csv)

    filter_person_trip_files(input_datafeed_trip_data)
    global person_trips_in_kiosk_network
    return { "numTripsInKioskNetwork": len(person_trips_in_kiosk_network) }


@app.route("/get_heatmap")
def get_heatmap():
    global person_trip_lst_latlngs
    h3_dict = {}
    for lat, lng in person_trip_lst_latlngs:
        h3_index = h3.geo_to_h3(lat, lng, 14) # Larger means more granular heatmap
        if h3_index in h3_dict:
            h3_dict[h3_index] += 1
        else:
            h3_dict[h3_index] = 1

    heatmap_data = {"max": 0, "min": 0, "data": []}
    max = 0
    for key, value in h3_dict.items():
        if value > max:
            max = value
        lat, lng = h3.h3_to_geo(key)
        new_h3_heatmap_entry = {"lat": lat, "lng": lng, "count": value}
        heatmap_data["data"].append(new_h3_heatmap_entry)
    heatmap_data["max"] = max

    return heatmap_data


@app.route("/draw_h3_polygons", methods=['POST'])
def draw_h3_polygons():
    url_path = request.args.get('url_path')
    print('https://raw.githubusercontent.com/whosonfirst-data/whosonfirst-data-admin-us/master/data/' + url_path)
    r = requests.get('https://raw.githubusercontent.com/whosonfirst-data/whosonfirst-data-admin-us/master/data/' + url_path)
    geojson = {"type":r.json()['geometry']['type'],
               "coordinates":r.json()['geometry']['coordinates']}
    global lst_h3_indices
    global h3_resolution
    lst_h3_indices = h3.polyfill(geojson, h3_resolution, geo_json_conformant=True) # res of 8 gives roughly .25 mi^2 area hexagons
    lst_polygons = []
    for h3_index in lst_h3_indices:
        lst_polygons.append([h3.h3_to_geo_boundary(h3_index)])
    return { "lst_polygons": lst_polygons }


@app.route("/draw_precalculated_kiosks")
def draw_precalculated_kiosks():
    lst_marker_latlngs = []
    global person_trip_lst_latlngs_by_h3_index
    for key, lst_latlngs in person_trip_lst_latlngs_by_h3_index.items():
        average_lat = 0
        average_lng = 0
        for lat, lng in lst_latlngs:
            average_lat += lat
            average_lng += lng
        average_lat /= len(lst_latlngs)
        average_lng /= len(lst_latlngs)
        lst_marker_latlngs.append([average_lat, average_lng])
    return { "lst_marker_latlngs": lst_marker_latlngs }

@app.route("/save_ODD", methods=['POST'])
def save_ODD():
    received_data = request.get_json()

    city_name = received_data['city_name']
    city_name = "PERTH_AMBOY_TESTING"
    avoidLocationsGeoJSON = received_data['avoidLocationsGeoJSON']
    markersGeoJSON = received_data['markersGeoJSON']
    circlesGeoJSON = received_data['circlesGeoJSON']
    polylinesGeoJSON = received_data['polylinesGeoJSON']

    with open("static/" + city_name + "/avoidLocationsGeoJSON.geojson", "w") as f:
        json.dump(avoidLocationsGeoJSON, f)
    with open("static/" + city_name + "/markersGeoJSON.geojson", "w") as f:
        json.dump(markersGeoJSON, f)
    with open("static/" + city_name + "/circlesGeoJSON.geojson", "w") as f:
        json.dump(circlesGeoJSON, f)
    with open("static/" + city_name + "/polylinesGeoJSON.geojson", "w") as f:
        json.dump(polylinesGeoJSON, f)

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


@app.route("/create_simulation", methods=['POST'])
def prepare_simulation():
    received_data = request.get_json()

    CITY_NAME = received_data['city_name']
    CITY_NAME = "PERTH_AMBOY_TESTING"
    county_name = received_data['county_name']
    state_name = received_data['state_name']
    center_lng_lat = received_data['center_lng_lat']
    lst_latlngs = received_data['lst_marker_latlngs']
    routes_dict = received_data['routes_dict']
    lst_fleetsize = [int(elem) for elem in received_data['lst_fleetsize']]
    modesplit = float(received_data['modesplit'])

    # depot_matrix = getCompleteRoutesMatrix(lst_latlngs, routes_dict)
    # print(depot_matrix)
    with open("static/" + city_name + "/depotmatrix.json", "w") as f:
        depot_matrix = json.load(f)

    print(CITY_NAME, county_name, state_name, center_lng_lat, lst_latlngs)

    # Make the CITY_NAME folder to store files inside
    shutil.rmtree(os.path.join(THIS_FOLDER, "static", CITY_NAME), ignore_errors=True)
    os.mkdir(os.path.join(THIS_FOLDER, "static", CITY_NAME))

    depot_data_filename = CITY_NAME+state_name+"_AV_Station.csv"
    COL_FIELDS = ["Name", "Lat", "Long"]
    with open(os.path.join(THIS_FOLDER, "static", CITY_NAME, depot_data_filename), 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(COL_FIELDS)
        csvwriter.writerows([[idx, latlng[0], latlng[1]] for idx, latlng in enumerate(lst_latlngs)]) # Switch this to kiosks with names

    # Create Depot Building Objects for Visualization
    offset = 0.0002
    height = 50
    buildings = []
    for depot in lst_latlngs:
        polygon = [[depot[0]-offset, depot[0]+offset],
                   [depot[0]+offset, depot[0]+offset],
                   [depot[0]+offset, depot[0]-offset],
                   [depot[0]-offset, depot[0]-offset]]
        polygon = [[elem[1], elem[0]] for elem in polygon]
        buildings.append({"height": height, "polygon": polygon, "m": "Depot"})

    with open("static/" + CITY_NAME + "/depotbuildings.json", "w") as f:
        json.dump(buildings, f)

    global person_trips_in_kiosk_network
    global person_trips_csv_header

    create_animation_dict = {
        'CITY_NAME': CITY_NAME,
        'depot_data_filename': depot_data_filename,
        'depot_matrix': depot_matrix,
        'person_trips_in_kiosk_network': person_trips_in_kiosk_network,
        'person_trips_csv_header': person_trips_csv_header,
        'modesplit': modesplit,
        'lst_fleetsize': lst_fleetsize,
        'center_lng_lat': center_lng_lat
    }

    saveCreateAnimationDict(create_animation_dict)
    response = create_animation(CITY_NAME)
    return response

def saveCreateAnimationDict(create_animation_dict):
    city_name = create_animation_dict['CITY_NAME']
    with open("static/" + city_name + "/createanimationdict.json", "w") as f:
        json.dump(create_animation_dict, f)

def create_animation(CITY_NAME):
    with open("static/" + CITY_NAME + "/createanimationdict.json", "r") as f:
        create_animation_dict = json.load(f)

    CITY_NAME = create_animation_dict['CITY_NAME']
    #depot_data_filename = create_animation_dict['depot_data_filename']
    #depot_matrix = create_animation_dict['depot_matrix']
    #person_trips_in_kiosk_network = create_animation_dict['person_trips_in_kiosk_network']
    person_trips_csv_header = create_animation_dict['person_trips_csv_header']
    #modesplit = create_animation_dict['modesplit']
    #lst_fleetsize = create_animation_dict['lst_fleetsize']
    center_lng_lat = create_animation_dict['center_lng_lat']

    depot_data_filename = "PERTH_AMBOY_TESTING_AV_Stations.csv"
    with open("static/" + CITY_NAME + "/depotmatrix.json", "r") as f:
        depot_matrix = json.load(f)

    with open("static/" + CITY_NAME + "/person_trips_in_xypixel_ODD.json") as f:
        person_trips_in_xypixel_ODD = json.load(f)['person_trips_in_xypixel_ODD']


    lst_fleetsize = [50]
    modesplit = 25.0

    start_time = time.time()

    # TODO: Allow users to choose these variables
    angry_passenger_threshold_sec = 300

    lst_passengers_left = []

    aDispatcher = Dispatcher(CITY_NAME, angry_passenger_threshold_sec, depot_matrix)
    depot_csv_name = os.path.join(THIS_FOLDER, "static", CITY_NAME, depot_data_filename)
    aDispatcher.createDataFeed(depot_csv_name, person_trips_in_xypixel_ODD, person_trips_csv_header, modesplit)


    for idx, fleetsize in enumerate(lst_fleetsize):
        print("Fleetsize:", fleetsize)
        aDispatcher.resetDataFeed()
        aDispatcher.createNumVehicles(fleetsize)
        index_metrics, trips, depot_locations, missed_passengers, waiting, metrics, metric_animations, last_arrival_at_depot_time, looplength, runtime = aDispatcher.solve()
        passengers_left = index_metrics[1]
        lst_passengers_left.append(passengers_left)
        print("MISSED PASSENGERS:", passengers_left)
        if (passengers_left == 0) or (idx == len(lst_fleetsize)-1):
            print("DONE, PRINTING RESULTS")
            # Write to files
            my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "index_metrics.txt")
            with open(my_file, "w") as f:
                index_metrics.append(fleetsize)
                f.write(str(index_metrics))

            my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "looplength.txt")
            with open(my_file, "w") as f:
                f.write(str(looplength))

            my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "trips.json.gz")
            compress_json.dump(trips, my_file)

            my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "depot_locations.txt")
            with open(my_file, "w") as f:
                f.write(str(depot_locations))

            my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "missed_passengers.json.gz")
            compress_json.dump(missed_passengers, my_file)

            my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "waiting.json.gz")
            compress_json.dump(waiting, my_file)

            my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "metrics.json.gz")
            compress_json.dump(metrics, my_file)

            my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "metric_animations.json.gz")
            compress_json.dump(metric_animations, my_file)

            my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "looplength.txt")
            with open(my_file, "w") as f:
                f.write(str(looplength))

            my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "runtime.txt")
            with open(my_file, "w") as f:
                f.write(str(runtime))

            my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "pax_left_vs_fleetsize.txt")
            with open(my_file, "w") as f:
                f.write(str([lst_fleetsize, lst_passengers_left]))

            my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "viewstate_coordinates.txt")
            with open(my_file, "w") as f:
                avg_lat = center_lng_lat[1]
                avg_lng = center_lng_lat[0]
                f.write(str([avg_lat, avg_lng]))

            break

    runtime=time.time()-start_time
    response = {
    'runtime': runtime
    }
    return response

@app.route("/animation")
def my_index():
    with open("local_static/trips.json", "r") as f:
        trips = json.load(f)

    html = render_template("index.html", trips=trips)
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

    app.run(host="localhost", port=8000, debug=False)
    # Go on http://localhost:8000/animation?city_choice=TRENTON_TESTING

#Comment out before updating PythonAnywhere
if __name__ == '__main__':
    main(argv)
