from flask import Flask, render_template, make_response, request, redirect, url_for
import requests
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

from Dispatcher import Dispatcher

global THIS_FOLDER
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
global CITY_NAME
CITY_NAME = ""
global list_of_unzipped_files

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
def extract_person_trip_files(county_name, state_name):
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

def filter_person_trip_files(list_of_unzipped_files, min_lat, max_lat, min_lng, max_lng):
    result_lst_latlngs = []
    for filename in list_of_unzipped_files:
        with open(filename, 'r', encoding='utf-8-sig') as file:
            csvreader = csv.reader(file)
            header = next(csvreader)
            lat_idx = header.index("OLat")
            long_idx = header.index("OLon")
            dest_lat_idx = header.index("DLat")
            dest_long_idx = header.index("DLon")
            for row in csvreader:
                lat = float(row[lat_idx])
                lng = float(row[long_idx])
                dest_lat = float(row[dest_lat_idx])
                dest_lng = float(row[dest_long_idx])
                if isInBoundsLatLng(lat, lng, min_lat, max_lat, min_lng, max_lng) and isInBoundsLatLng(dest_lat, dest_lng, min_lat, max_lat, min_lng, max_lng):
                    result_lst_latlngs.append([lat, lng])
                    result_lst_latlngs.append([dest_lat, dest_lng])
    return result_lst_latlngs

def getRouteMeta(latlng1, latlng2):
    loc = "{},{};{},{}".format(latlng1[1], latlng1[0], latlng2[1], latlng2[0])
    url = "http://127.0.0.1:5000/route/v1/driving/"
    r = requests.get(url + loc + "?overview=full&steps=true")
    if r.status_code != 200:
        print("ERROR")
        return {}
    res = r.json()
    test_duration = 0
    for step in res['routes'][0]['legs'][0]['steps']:
        test_duration += step['duration']
    route_latlngs = polyline.decode(res['routes'][0]['geometry'])
    route_distance = res['routes'][0]['distance']
    route_duration = res['routes'][0]['duration']
    return route_latlngs, route_distance, route_duration

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
    #graph = Graph(len(lst_latlngs))
    for lat_lng in lst_latlngs:
        if not lat_lng == new_marker_lat_lng:
            str_new_marker_lat_lng = ','.join(str(x) for x in new_marker_lat_lng)
            str_lat_lng = ','.join(str(x) for x in lat_lng)
            route_latlngs, route_distance, route_duration = getRouteMeta(new_marker_lat_lng, lat_lng)
            route_metas['{};{}'.format(str_new_marker_lat_lng, str_lat_lng)] = {'latlngs': route_latlngs, 'distance': route_distance, 'duration': route_duration}
            route_latlngs, route_distance, route_duration = getRouteMeta(lat_lng, new_marker_lat_lng)
            route_metas['{};{}'.format(str_lat_lng, str_new_marker_lat_lng)] = {'latlngs': route_latlngs, 'distance': route_distance, 'duration': route_duration}
            #graph.addEdge(idx1, idx2, route_duration)

    #sorted_route_metas = graph.getAllSortedRoutes(route_metas)
    print(route_metas)
    return route_metas

@app.route("/get_heatmap")
def get_heatmap():
    county_name = request.args.get('county_name')
    state_name = request.args.get('state_name')
    min_lng, min_lat, max_lng, max_lat = [float(elem) for elem in request.args.get('bbox').split(',')]
    print(min_lng, min_lat, max_lng, max_lat)

    extract_person_trip_files(county_name, state_name)

    global list_of_unzipped_files

    input_datafeed_trip_data = []
    for trip_data_csv in list_of_unzipped_files:
        input_datafeed_trip_data.append("local_static/" + trip_data_csv)

    lst_latlngs = filter_person_trip_files(input_datafeed_trip_data, min_lat, max_lat, min_lng, max_lng)

    h3_dict = {}
    for lat, lng in lst_latlngs:
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


# Very delicate structure!
def parseDepotMatrix(routes_dict_converted_to_lst):
    depot_matrix = {}
    i = 0
    while i < len(routes_dict_converted_to_lst):
        key = routes_dict_converted_to_lst[i]
        lst_latlngs = []
        i += 2
        while routes_dict_converted_to_lst[i] != "distance":
            latlng = [float(routes_dict_converted_to_lst[i]), float(routes_dict_converted_to_lst[i+1])]
            lst_latlngs.append(latlng)
            i += 2
        i += 1
        distance = float(routes_dict_converted_to_lst[i])
        i += 2
        duration = float(routes_dict_converted_to_lst[i])
        i += 1
        depot_matrix[key] = {"route_latlngs": lst_latlngs, "route_distance": distance, "route_duration": duration}
    return depot_matrix


@app.route("/create_simulation", methods=['POST'])
def create_animation():
    CITY_NAME = request.args.get('city_name')
    county_name = request.args.get('county_name')
    state_name = request.args.get('state_name')
    url_path = request.args.get('url_path')
    lst_latlngs = request.args.get('lst_latlngs').split(',')
    lst_latlngs = [[float(lat), float(lon)] for lat, lon in [lst_latlngs[x:x+2] for x in range(0, len(lst_latlngs), 2)]]
    center_lng_lat = [float(elem) for elem in request.args.get('center_lng_lat').split(',')]
    routes_dict_converted_to_lst = request.args.get('routes_dict_converted_to_lst').split(',')
    depot_matrix = parseDepotMatrix(routes_dict_converted_to_lst)

    print(depot_matrix)
    print(CITY_NAME, county_name, state_name, url_path, lst_latlngs, center_lng_lat)

    depot_data_filename = CITY_NAME+state_name+"_AV_Station.csv"
    fields = ["Name", "Lat", "Long"]
    with open(os.path.join(THIS_FOLDER, "local_static", depot_data_filename), 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(fields)
        csvwriter.writerows(list_kiosks)

    r = requests.get('https://raw.githubusercontent.com/whosonfirst-data/whosonfirst-data-admin-us/master/data/' + url_path)
    lst_lnglats = r.json()['geometry']['coordinates'][0]

    # Make the CITY_NAME folder to store files inside
    shutil.rmtree(os.path.join(THIS_FOLDER, "static", CITY_NAME), ignore_errors=True)
    os.mkdir(os.path.join(THIS_FOLDER, "static", CITY_NAME))

    # Create Depot Matrix and Depot Building Objects for Visualization
    a = DepotMatrixAndBuildings(os.path.join(THIS_FOLDER, "local_static", depot_data_filename), CITY_NAME)
    a.createDepotMatrix()
    a.createDepotBuildings(50, 0.0002)

    start_time = time.time()
    input_datafeed_depot_data = os.path.join(THIS_FOLDER, "local_static", depot_data_filename)
    input_datafeed_trip_data = []
    global list_of_unzipped_files
    for trip_data_csv in list_of_unzipped_files:
        input_datafeed_trip_data.append("local_static/" + trip_data_csv)

    # TODO: Allow users to choose these variables
    modesplit = 10
    angry_passenger_threshold_sec = 300
    lst_fleetsize = [100]

    print(input_datafeed_trip_data)
    print("MODESPLIT:", modesplit)

    lst_passengers_left = []

    aDispatcher = Dispatcher(CITY_NAME, angry_passenger_threshold_sec)
    aDispatcher.createDataFeed(input_datafeed_depot_data, lst_lnglats, input_datafeed_trip_data, modesplit)

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

#Comment out before updating PythonAnywhere
app.run(host="localhost", port=8000, debug=True)
