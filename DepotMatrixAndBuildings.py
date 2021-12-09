import requests
import json
import polyline
from DataFeed import DataFeed
from geopy.distance import distance

class DepotMatrixAndBuildings:
    def __init__(self, depot_csv = None, city_name = None):
        self.depot_csv = depot_csv
        self.city_name = city_name
        self.DataFeed = DataFeed(self.depot_csv)
        self.DataFeed.parseDepots()

    def getDepots(self):
        self.lst_depots = self.DataFeed.getDepots()

    def getRouteMeta(self, location1, location2):
        loc = "{},{};{},{}".format(location1[1], location1[0], location2[1], location2[0])
        url = "http://127.0.0.1:5000/route/v1/driving/"
        r = requests.get(url + loc)
        if r.status_code != 200:
            return {}
        res = r.json()
        route_latlngs = polyline.decode(res['routes'][0]['geometry'])
        route_distance = res['routes'][0]['distance']
        route_duration = res['routes'][0]['duration']
        return route_latlngs, route_distance, route_duration

    def getRouteTimeStamps(self, route_latlngs, route_distance, route_duration):
        timestamps = [0]
        if route_distance == 0:
            return timestamps
        length = len(list(zip(route_latlngs, route_latlngs[1:])))
        for idx, pair in enumerate(zip(route_latlngs, route_latlngs[1:])):
            if idx == length-1:
                timestamps.append(route_duration)
                break
            percentage = distance(pair[0], pair[1]).meters/route_distance
            time_spent = percentage * route_duration
            timestamps.append(time_spent+timestamps[idx])
        return timestamps

    def createDepotMatrix(self):
        self.getDepots()
        matrix = {}
        for depot_i in self.lst_depots:
            for depot_j in self.lst_depots:
                route_latlngs, route_distance, route_duration = self.getRouteMeta((depot_i.lat, depot_i.lon), (depot_j.lat, depot_j.lon))
                timestamps = self.getRouteTimeStamps(route_latlngs, route_distance, route_duration)
                matrix["{},{};{},{}".format(depot_i.lat, depot_i.lon, depot_j.lat, depot_j.lon)] = {"route_latlngs": route_latlngs, "route_distance": route_distance, "route_duration": route_duration, "timestamps": timestamps}
        with open("static/" + self.city_name + "/depotmatrix.csv", "w") as f:
            json.dump(matrix, f)

    def createDepotBuildings(self, height, offset):
        self.getDepots()
        buildings = []
        for depot in self.lst_depots:
            polygon = [[depot.lat-offset, depot.lon+offset],
                       [depot.lat+offset, depot.lon+offset],
                       [depot.lat+offset, depot.lon-offset],
                       [depot.lat-offset, depot.lon-offset]]
            polygon = [[elem[1], elem[0]] for elem in polygon]
            buildings.append({"height": height, "polygon": polygon, "m": str(depot)})
        with open("static/" + self.city_name + "/depotbuildings.csv", "w") as f:
            json.dump(buildings, f)

a = DepotMatrixAndBuildings("local_static/Washington_DC_AV_Station.csv", "Washington_DC")
a.createDepotMatrix()
a.createDepotBuildings(50, 0.0002)

#with open("depotmatrix.txt", "r") as f:
#    data = json.load(f)
#    print(data["{},{};{},{}".format(40.23214321892,-74.7813941689,40.2417532347,-74.7540253465)])
