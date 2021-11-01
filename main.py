from flask import Flask, render_template, make_response, request
import json

from Dispatcher import Dispatcher

app = Flask("__main__")

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
    fleetsize = int(request.args.get('fleetsize'))
    modesplit = int(request.args.get('modesplit'))
    aDispatcher = Dispatcher()
    aDispatcher.createDataFeed("static/Trenton_AV_Station.csv", ["static/FinalOriginPixel34021_1.csv", "static/FinalOriginPixel34021_2.csv"], 40.194431, 40.259060, -74.808413, -74.720080, modesplit)
    aDispatcher.createNumVehicles(fleetsize)
    trips, metrics, metric_animations, loop_length, run_time = aDispatcher.solve()
    with open("static/depotbuildings.csv", "r") as f:
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

app.run(debug=True)
