from flask import Flask, render_template, make_response, request
import json
import os

from Dispatcher import Dispatcher

global THIS_FOLDER
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

app = Flask("__main__", template_folder=os.path.join(THIS_FOLDER, "templates"))

global trips
global metrics
global metric_animations
global buildings
global loop_length

@app.route("/")
@app.route("/setup")
def setup():
    html = render_template("setup.html")
    response = make_response(html)
    return response


@app.route("/create_animation", methods=['GET'])
def create_animation():
    global trips
    global metrics
    global metric_animations
    global buildings
    global loop_length
    global THIS_FOLDER
    fleetsize = int(request.args.get('fleetsize'))
    modesplit = int(request.args.get('modesplit'))
    aDispatcher = Dispatcher()
    csv1 = os.path.join(THIS_FOLDER, "static", "Trenton_AV_Station.csv")
    csv2 = os.path.join(THIS_FOLDER, "static", "FinalOriginPixel34021_1.csv")
    csv3 = os.path.join(THIS_FOLDER, "static", "FinalOriginPixel34021_2.csv")

    aDispatcher.createDataFeed(csv1, [csv2, csv3], 40.194431, 40.259060, -74.808413, -74.720080, modesplit)
    aDispatcher.createNumVehicles(fleetsize)
    trips, metrics, metric_animations, loop_length, run_time = aDispatcher.solve()
    csv4 = os.path.join(THIS_FOLDER, "static", "depotbuildings.csv")
    with open(csv4, "r") as f:
        buildings = json.load(f)
    html = render_template("create_animation.html", run_time = run_time)
    response = make_response(html)
    return response


@app.route("/animation")
def my_index():
    global trips
    global metric_animations
    global buildings
    global loop_length
    html = render_template("index.html", buildings=buildings, trips = json.loads(trips), metric_animations = json.loads(metric_animations), loop_length = loop_length)
    response = make_response(html)
    return response


@app.route("/graphs")
def graph_page():
    global metrics
    html = render_template("graphs.html", metrics = json.loads(metrics))
    response = make_response(html)
    return response

#Remove before updating PythonAnywhere
app.run()
