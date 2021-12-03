from flask import Flask, render_template, make_response, request, redirect, url_for
import json
import os
import time

from Dispatcher import Dispatcher

global THIS_FOLDER
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

app = Flask("__main__", template_folder=os.path.join(THIS_FOLDER, "templates"))

@app.route("/")
@app.route("/setup")
def setup():
    html = render_template("setup.html")
    response = make_response(html)
    return response


@app.route("/create_animation", methods=['GET'])
def create_animation():
    depot_data_csv = request.args.get('depot_data_csv')
    lst_trip_data_csv = [string.strip() for string in request.args.get('lst_trip_data_csv').split(",")]
    lst_fleetsize = [int(num) for num in request.args.get('lst_fleetsize').split(",")]
    modesplit = float(request.args.get('modesplit'))
    min_lat = float(request.args.get('min_lat'))
    max_lat = float(request.args.get('max_lat'))
    min_lng = float(request.args.get('min_lng'))
    max_lng = float(request.args.get('max_lng'))
    angry_passenger_threshold_sec = int(request.args.get('angry_passenger_threshold_sec'))

    start_time = time.time()
    global THIS_FOLDER
    input_datafeed_depot_data = os.path.join(THIS_FOLDER, "static", depot_data_csv)
    input_datafeed_trip_data = []
    for trip_data_csv in lst_trip_data_csv:
        input_datafeed_trip_data.append("static/" + trip_data_csv)

    lst_passengers_left = []

    aDispatcher = Dispatcher(angry_passenger_threshold_sec)
    aDispatcher.createDataFeed(input_datafeed_depot_data, input_datafeed_trip_data, min_lat, max_lat, min_lng, max_lng, modesplit)

    for idx, fleetsize in enumerate(lst_fleetsize):
        print("Fleetsize:", fleetsize)
        aDispatcher.resetDataFeed()
        aDispatcher.createNumVehicles(fleetsize)
        index_metrics, trips, depot_locations, missed_passengers, waiting, metrics, metric_animations, last_arrival_at_depot_time, looplength, runtime = aDispatcher.solve()
        passengers_left = index_metrics[1]
        lst_passengers_left.append(passengers_left)
        print(passengers_left)
        if (passengers_left == 0) or (idx == len(lst_fleetsize)-1):
            print("DONE, PRINTING RESULTS")
            # Write to files
            my_file = os.path.join(THIS_FOLDER, "static", "index_metrics.txt")
            with open(my_file, "w") as f:
                index_metrics.append(fleetsize)
                f.write(str(index_metrics))

            my_file = os.path.join(THIS_FOLDER, "static", "looplength.txt")
            with open(my_file, "w") as f:
                f.write(str(looplength))

            my_file = os.path.join(THIS_FOLDER, "static", "trips.json")
            with open(my_file, "w") as f:
                json.dump(trips, f)

            my_file = os.path.join(THIS_FOLDER, "static", "depot_locations.txt")
            with open(my_file, "w") as f:
                f.write(str(depot_locations))

            my_file = os.path.join(THIS_FOLDER, "static", "missed_passengers.json")
            with open(my_file, "w") as f:
                json.dump(missed_passengers, f)

            my_file = os.path.join(THIS_FOLDER, "static", "waiting.json")
            with open(my_file, "w") as f:
                json.dump(waiting, f)

            my_file = os.path.join(THIS_FOLDER, "static", "metrics.json")
            with open(my_file, "w") as f:
                json.dump(metrics, f)

            my_file = os.path.join(THIS_FOLDER, "static", "metric_animations.json")
            with open(my_file, "w") as f:
                json.dump(metric_animations, f)

            my_file = os.path.join(THIS_FOLDER, "static", "looplength.txt")
            with open(my_file, "w") as f:
                f.write(str(looplength))

            my_file = os.path.join(THIS_FOLDER, "static", "runtime.txt")
            with open(my_file, "w") as f:
                f.write(str(runtime))

            my_file = os.path.join(THIS_FOLDER, "static", "pax_left_vs_fleetsize.txt")
            with open(my_file, "w") as f:
                f.write(str([lst_fleetsize, lst_passengers_left]))

            my_file = os.path.join(THIS_FOLDER, "static", "viewstate_coordinates.txt")
            with open(my_file, "w") as f:
                avg_lat = (min_lat + max_lat)/2
                avg_lng = (min_lng + max_lng)/2
                f.write(str([avg_lat, avg_lng]))

            break

    html = render_template("create_animation.html", run_time=time.time()-start_time)
    response = make_response(html)
    return response

@app.route("/animation")
def my_index():
    global THIS_FOLDER
    animation_speed = request.args.get('animation_speed', default = 1, type = int)
    start_time = request.args.get('start_time', default = 0, type = int)

    my_file = os.path.join(THIS_FOLDER, "static", "depotbuildings.csv")
    with open(my_file, "r") as f:
        buildings = json.load(f)

    my_file = os.path.join(THIS_FOLDER, "static", "trips.json")
    with open(my_file, "r") as f:
        trips = json.load(f)

    my_file = os.path.join(THIS_FOLDER, "static", "depot_locations.txt")
    with open(my_file, "r") as f:
        depot_locations = f.read()

    my_file = os.path.join(THIS_FOLDER, "static", "missed_passengers.json")
    with open(my_file, "r") as f:
        missed_passengers = json.load(f)

    my_file = os.path.join(THIS_FOLDER, "static", "waiting.json")
    with open(my_file, "r") as f:
        waiting = json.load(f)

    my_file = os.path.join(THIS_FOLDER, "static", "metric_animations.json")
    with open(my_file, "r") as f:
        metric_animations = json.load(f)

    my_file = os.path.join(THIS_FOLDER, "static", "looplength.txt")
    with open(my_file, "r") as f:
        loop_length = int(f.read())

    my_file = os.path.join(THIS_FOLDER, "static", "index_metrics.txt")
    with open(my_file, "r") as f:
        index_metrics = f.read()

    my_file = os.path.join(THIS_FOLDER, "static", "metrics.json")
    with open(my_file, "r") as f:
        metrics = json.load(f)

    my_file = os.path.join(THIS_FOLDER, "static", "viewstate_coordinates.txt")
    with open(my_file, "r") as f:
        viewstate_coordinates = f.read()

    html = render_template("index.html", buildings=buildings, trips = trips, depot_locations = depot_locations, missed_passengers = missed_passengers, waiting = waiting, metric_animations = metric_animations, loop_length = loop_length, animation_speed=animation_speed, start_time=start_time, metrics = metrics, index_metrics = index_metrics, viewstate_coordinates=viewstate_coordinates)
    response = make_response(html)
    return response


@app.route("/graphs")
def graph_page():
    my_file = os.path.join(THIS_FOLDER, "static", "metrics.json")
    with open(my_file, "r") as f:
        metrics = json.load(f)

    my_file = os.path.join(THIS_FOLDER, "static", "pax_left_vs_fleetsize.txt")
    with open(my_file, "r") as f:
        pax_left_vs_fleetsize_data = f.read()

    html = render_template("graphs.html", metrics = metrics, pax_left_vs_fleetsize_data = pax_left_vs_fleetsize_data)
    response = make_response(html)
    return response

#Remove before updating PythonAnywhere
app.run()
