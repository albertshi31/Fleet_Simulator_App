from flask import Flask, render_template, make_response, request
import json
import os

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
    global THIS_FOLDER
    fleetsize = int(request.args.get('fleetsize'))
    modesplit = float(request.args.get('modesplit'))
    aDispatcher = Dispatcher()
    csv1 = os.path.join(THIS_FOLDER, "static", "Trenton_AV_Station.csv")
    csv2 = os.path.join(THIS_FOLDER, "static", "FinalOriginPixel34021_1.csv")
    csv3 = os.path.join(THIS_FOLDER, "static", "FinalOriginPixel34021_2.csv")
    aDispatcher.createDataFeed(csv1, [csv2, csv3], 40.194431, 40.259060, -74.808413, -74.720080, modesplit)
    aDispatcher.createNumVehicles(fleetsize)
    aDispatcher.solve()
    csv4 = os.path.join(THIS_FOLDER, "static", "runtime.txt")
    with open(csv4, "r") as f:
        run_time = float(f.read())
    html = render_template("create_animation.html", run_time = run_time)
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

    my_file = os.path.join(THIS_FOLDER, "static", "trips.csv")
    with open(my_file, "r") as f:
        trips = json.load(f)

    my_file = os.path.join(THIS_FOLDER, "static", "depot_locations.csv")
    with open(my_file, "r") as f:
        depot_locations = json.load(f)

    my_file = os.path.join(THIS_FOLDER, "static", "waiting_passengers.csv")
    with open(my_file, "r") as f:
        waiting_passengers = json.load(f)

    my_file = os.path.join(THIS_FOLDER, "static", "waiting_vehicles.csv")
    with open(my_file, "r") as f:
        waiting_vehicles = json.load(f)

    my_file = os.path.join(THIS_FOLDER, "static", "metric_animations.csv")
    with open(my_file, "r") as f:
        metric_animations = json.load(f)

    my_file = os.path.join(THIS_FOLDER, "static", "looplength.txt")
    with open(my_file, "r") as f:
        loop_length = int(f.read())

    html = render_template("index.html", buildings=buildings, trips = trips, depot_locations = depot_locations, waiting_passengers = waiting_passengers, waiting_vehicles = waiting_vehicles, metric_animations = metric_animations, loop_length = loop_length, animation_speed=animation_speed, start_time=start_time)
    response = make_response(html)
    return response


@app.route("/graphs")
def graph_page():
    my_file = os.path.join(THIS_FOLDER, "static", "metrics.csv")
    with open(my_file, "r") as f:
        metrics = json.load(f)

    html = render_template("graphs.html", metrics = metrics)
    response = make_response(html)
    return response

#Remove before updating PythonAnywhere
app.run()
