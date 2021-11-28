from flask import Flask, render_template, make_response, request
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
    start = time.time()
    global THIS_FOLDER
    fleetsize = int(request.args.get('fleetsize', default = 100))
    modesplit = float(request.args.get('modesplit', default = 100))
    csv1 = os.path.join(THIS_FOLDER, "static", "Trenton_AV_Station.csv")
    csv2 = os.path.join(THIS_FOLDER, "static", "FinalOriginPixel34021_1.csv")
    csv3 = os.path.join(THIS_FOLDER, "static", "FinalOriginPixel34021_2.csv")
    lst_fleetsize = []
    lst_passengers_left = []
    for fleetsize in range(100, 1000, 20):
        print("Fleetsize:", fleetsize)
        lst_fleetsize.append(fleetsize)
        aDispatcher = Dispatcher()
        aDispatcher.createDataFeed(csv1, [csv2, csv3], 40.194431, 40.259060, -74.808413, -74.720080, modesplit)
        aDispatcher.createNumVehicles(fleetsize)
        passengers_left, trips, depot_locations, missed_passengers, waiting, metrics, metric_animations, last_arrival_at_depot_time, looplength, runtime = aDispatcher.solve()
        lst_passengers_left.append(passengers_left)
        if passengers_left == 0:
            print("DONE, PRINTING RESULTS")
            # Write to files
            my_file = os.path.join(THIS_FOLDER, "static", "trips.json")
            with open(my_file, "w") as f:
                json.dump(trips, f)

            my_file = os.path.join(THIS_FOLDER, "static", "depot_locations.json")
            with open(my_file, "w") as f:
                json.dump(depot_locations, f)

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
            break

    print(lst_passengers_left)
    html = render_template("create_animation.html", run_time = time.time() - start)
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

    my_file = os.path.join(THIS_FOLDER, "static", "depot_locations.json")
    with open(my_file, "r") as f:
        depot_locations = json.load(f)

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

    my_file = os.path.join(THIS_FOLDER, "static", "metrics.json")
    with open(my_file, "r") as f:
        metrics = json.load(f)

    html = render_template("index.html", buildings=buildings, trips = trips, depot_locations = depot_locations, missed_passengers = missed_passengers, waiting = waiting, metric_animations = metric_animations, loop_length = loop_length, animation_speed=animation_speed, start_time=start_time, metrics = metrics)
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
#app.run()
