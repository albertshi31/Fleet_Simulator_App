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

from Dispatcher import Dispatcher

global THIS_FOLDER
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
global CITY_NAME
CITY_NAME = ""
global list_of_unzipped_files
global person_trip_lst_latlngs
global person_trips_in_kiosk_network
global person_trips_csv_header
global person_trip_lst_latlngs_by_h3_index
global lst_h3_indices
global h3_resolution
h3_resolution = 8

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
                if origin_h3_index in lst_h3_indices and dest_h3_index in lst_h3_indices and gcdistance > .5:
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


def getRouteMeta(latlng1, latlng2):
    loc = "{},{};{},{}".format(latlng1[1], latlng1[0], latlng2[1], latlng2[0])
    url = "http://127.0.0.1:5000/route/v1/driving/"
    r = requests.get(url + loc + "?overview=full&annotations=true")
    if r.status_code != 200:
        print("ERROR")
        return {}
    res = r.json()
    raw_timestamps = res['routes'][0]['legs'][0]['annotation']['duration']
    raw_timestamps.insert(0, 0) # raw_timestamps gives list of times you should add to previous sum
    route_timestamps = list(np.cumsum(raw_timestamps))

    route_latlngs = polyline.decode(res['routes'][0]['geometry'])
    route_distance = res['routes'][0]['distance']
    route_duration = res['routes'][0]['duration']
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

@app.route("/get_routes")
def get_routes():
    route_metas = {}
    lst_latlngs = request.args.get('lst_latlngs').split(',')
    lst_latlngs = [[float(lat), float(lon)] for lat, lon in [lst_latlngs[x:x+2] for x in range(0, len(lst_latlngs), 2)]]
    new_marker_lat, new_marker_lng = request.args.get('new_marker').split(',')
    new_marker_lat_lng = [float(new_marker_lat), float(new_marker_lng)]
    for lat_lng in lst_latlngs:
        if not lat_lng == new_marker_lat_lng:
            str_new_marker_lat_lng = ','.join(str(x) for x in new_marker_lat_lng)
            str_lat_lng = ','.join(str(x) for x in lat_lng)
            route_latlngs, route_distance, route_duration, route_timestamps = getRouteMeta(new_marker_lat_lng, lat_lng)
            route_metas['{};{}'.format(str_new_marker_lat_lng, str_lat_lng)] = {'latlngs': route_latlngs, 'distance': route_distance, 'duration': route_duration, 'timestamps': route_timestamps}
            route_latlngs, route_distance, route_duration, route_timestamps = getRouteMeta(lat_lng, new_marker_lat_lng)
            route_metas['{};{}'.format(str_lat_lng, str_new_marker_lat_lng)] = {'latlngs': route_latlngs, 'distance': route_distance, 'duration': route_duration, 'timestamps': route_timestamps}
    return route_metas

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
    lst_h3_indices = h3.polyfill(geojson, h3_resolution, geo_json_conformant=True) # res of 8 gives roughly ..25 mi^2 area hexagons
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


@app.route("/create_simulation", methods=['POST'])
def prepare_simulation():
        received_data = request.get_json()

        CITY_NAME = received_data['city_name']
        CITY_NAME = "TRENTON_TESTING"
        county_name = received_data['county_name']
        state_name = received_data['state_name']
        center_lng_lat = received_data['center_lng_lat']
        lst_latlngs = received_data['lst_marker_latlngs']
        depot_matrix = received_data['routes_dict']
        lst_fleetsize = [int(elem) for elem in received_data['lst_fleetsize']]
        modesplit = float(received_data['modesplit'])
        print(CITY_NAME, county_name, state_name, center_lng_lat, lst_latlngs)

        # IS THIS NECESSARY? We get errors trying to render empty routes in the setup page
        for latlng in lst_latlngs:
            str_lat_lng = ','.join(str(x) for x in latlng)
            depot_matrix['{};{}'.format(str_lat_lng, str_lat_lng)] = {'latlngs': [latlng, latlng], 'distance': 0, 'duration': 0, 'timestamps': [0]}

        # Make the CITY_NAME folder to store files inside
        shutil.rmtree(os.path.join(THIS_FOLDER, "static", CITY_NAME), ignore_errors=True)
        os.mkdir(os.path.join(THIS_FOLDER, "static", CITY_NAME))

        depot_data_filename = CITY_NAME+state_name+"_AV_Station.csv"
        COL_FIELDS = ["Name", "Lat", "Long"]
        with open(os.path.join(THIS_FOLDER, "static", CITY_NAME, depot_data_filename), 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(COL_FIELDS)
            csvwriter.writerows([[idx, latlng[0], latlng[1]] for idx, latlng in enumerate(lst_latlngs)]) # Switch this to kiosks with names

        # Create Depot Matrix and Depot Building Objects for Visualization
        with open("static/" + CITY_NAME + "/depotmatrix.csv", "w") as f:
            json.dump(depot_matrix, f)

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

        with open("static/" + CITY_NAME + "/depotbuildings.csv", "w") as f:
            json.dump(buildings, f)

        global person_trips_in_kiosk_network
        global person_trips_csv_header

        create_animation_dict = {
            'CITY_NAME': CITY_NAME,
            'depot_data_filename': depot_data_filename,
            'person_trips_in_kiosk_network': person_trips_in_kiosk_network,
            'person_trips_csv_header': person_trips_csv_header,
            'modesplit': modesplit,
            'lst_fleetsize': lst_fleetsize
        }

        saveCreateAnimationDict(create_animation_dict)
        response = create_animation(CITY_NAME)
        return response

def saveCreateAnimationDict(create_animation_dict):
    city_name = create_animation_dict['CITY_NAME']
    with open("static/" + city_name + "/createanimationdict.csv", "w") as f:
        json.dump(create_animation_dict, f)

def create_animation(CITY_NAME):
    with open("static/" + CITY_NAME + "/createanimationdict.csv", "r") as f:
        create_animation_dict = json.load(f)

    CITY_NAME = create_animation_dict['CITY_NAME']
    depot_data_filename = create_animation_dict['depot_data_filename']
    person_trips_in_kiosk_network = create_animation_dict['person_trips_in_kiosk_network']
    person_trips_csv_header = create_animation_dict['person_trips_csv_header']
    modesplit = create_animation_dict['modesplit']
    lst_fleetsize = create_animation_dict['lst_fleetsize']

    start_time = time.time()

    # TODO: Allow users to choose these variables
    angry_passenger_threshold_sec = 300

    lst_passengers_left = []

    aDispatcher = Dispatcher(CITY_NAME, angry_passenger_threshold_sec)
    depot_csv_name = os.path.join(THIS_FOLDER, "static", CITY_NAME, depot_data_filename)
    aDispatcher.createDataFeed(depot_csv_name, person_trips_in_kiosk_network, person_trips_csv_header, modesplit)


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

    html = render_template("create_animation.html", run_time=time.time()-start_time)
    response = make_response(html)
    return response

@app.route("/animation")
def my_index():
    global THIS_FOLDER
    global CITY_NAME
    CITY_NAME = request.args.get('city_choice', default = CITY_NAME)
    animation_speed = request.args.get('animation_speed', default = 1, type = int)
    start_time = request.args.get('start_time', default = 0, type = int)

    my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "depotbuildings.csv")
    with open(my_file, "r") as f:
        buildings = json.load(f)

    my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "trips.json.gz")
    trips = compress_json.load(my_file)

    my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "depot_locations.txt")
    with open(my_file, "r") as f:
        depot_locations = f.read()

    my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "missed_passengers.json.gz")
    missed_passengers = compress_json.load(my_file)

    my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "waiting.json.gz")
    waiting = compress_json.load(my_file)

    my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "metric_animations.json.gz")
    metric_animations = compress_json.load(my_file)

    my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "looplength.txt")
    with open(my_file, "r") as f:
        loop_length = int(f.read())

    my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "index_metrics.txt")
    with open(my_file, "r") as f:
        index_metrics = f.read()

    my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "metrics.json.gz")
    metrics = compress_json.load(my_file)

    my_file = os.path.join(THIS_FOLDER, "static", CITY_NAME, "viewstate_coordinates.txt")
    with open(my_file, "r") as f:
        viewstate_coordinates = f.read()

    html = render_template("index.html", buildings=buildings, trips = trips, depot_locations = depot_locations, missed_passengers = missed_passengers, waiting = waiting, metric_animations = metric_animations, loop_length = loop_length, animation_speed=animation_speed, start_time=start_time, metrics = metrics, index_metrics = index_metrics, viewstate_coordinates=viewstate_coordinates)
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
        CITY_NAME = "TRENTON_TESTING"
        create_animation(CITY_NAME)
        print("TEST")
    else:
        app.run(host="localhost", port=8000, debug=True)

#Comment out before updating PythonAnywhere
if __name__ == '__main__':
    main(argv)
