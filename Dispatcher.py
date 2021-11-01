from Passenger import Passenger
from Vehicle import Vehicle
from DataFeed import DataFeed
import requests
import time
from geopy.distance import distance
import json

class Dispatcher:
    def __init__(self):
        self.num_vehicles = 0
        self.all_vehicle_list = []
        self.active_vehicle_list = {}
        self.idle_vehicle_list = {}
        self.display_vehicle_list = {}
        self.all_passenger_list = []
        self.active_passenger_list = []
        self.display_passenger_list = []
        self.vehicle_animations = []
        self.passenger_animations = []
        self.depot_animations = []
        self.resolution = 8
        self.time_rate = 1
        self.simulation_time_sec = 0
        self.active = False

    def createDataFeed(self, depot_csv=None, lst_passenger_csv=None, min_lat=None, max_lat=None, min_lng=None, max_lng=None, modesplit=None):
        self.DataFeed = DataFeed(depot_csv, lst_passenger_csv, min_lat, max_lat, min_lng, max_lng, modesplit)
        self.DataFeed.parsePassengers()
        self.DataFeed.parseDepots()

    def createNumVehicles(self, num_vehicles):
        self.num_vehicles = num_vehicles
        for i in range(num_vehicles):
            self.all_vehicle_list.append(Vehicle())

    def __str__(self):
        result = "Number of Active Passengers: {0}\nNumber of Active Vehicles: {1}\n".format(len(self.active_passenger_list), len(self.active_vehicle_list))
        result += "---ACTIVE PASSENGER LIST---\n"
        for pax in self.active_passenger_list:
            result += str(pax)
        result += "---ACTIVE VEHICLE LIST---\n"
        for vehicle in self.active_vehicle_list:
            result += str(vehicle)
        return result

    def getDepots(self):
        return self.DataFeed.getDepots()

    def addPassenger(self, aPassenger):
        self.all_passenger_list.append(aPassenger)
        self.active_passenger_list.append(aPassenger)
        self.display_passenger_list.append(aPassenger)

    def addVehicle(self, aVehicle):
        self.all_vehicle_list[id(aVehicle)] = aVehicle
        self.idle_vehicle_list[id(aVehicle)] = aVehicle

    def getDisplayPassengerList(self):
        temp = self.display_passenger_list
        self.display_passenger_list = []
        return temp

    def getDisplayVehicleList(self):
        temp = self.display_vehicle_list.values()
        self.display_vehicle_list = {}
        return temp

    def getActivePassengerList(self):
        return self.active_passenger_list

    def getActiveVehicleList(self):
        return self.active_vehicle_list.values()

    def getAllPassengerList(self):
        return self.DataFeed.getAllPassengers

    def getAllVehicleList(self):
        return self.all_vehicle_list.values()

    def getClosestDepot(self, lat, lon):
        lst_distances = []
        for depot in self.DataFeed.all_depots:
            lst_distances.append(distance((lat, lon), (depot.lat, depot.lon)).meters)
        closest_depot = self.DataFeed.all_depots[lst_distances.index(min(lst_distances))]
        return closest_depot

    def routeVehicle(self, starting_depot, passengers, matrix, start_time):
        lst_locations = list(set([pax.dest_depot for pax in passengers]))
        lst_locations.insert(0, starting_depot)
        lst_locations.append(starting_depot)
        trip_latlngs = []
        distances = {}
        trip_distance = 0
        trip_duration = 0
        trip_timestamps = []
        for idx, pair in enumerate(list(zip(lst_locations, lst_locations[1:]))):
            entry = matrix["{},{};{},{}".format(pair[0].lat, pair[0].lon, pair[1].lat, pair[1].lon)]
            trip_latlngs.extend(entry["route_latlngs"])
            trip_distance += entry["route_distance"]
            distances["{},{}".format(pair[1].lat, pair[1].lon)] = trip_distance
            trip_duration += entry["route_duration"]
            if idx == 0:
                trip_timestamps.extend([x+start_time for x in entry["timestamps"]])
            else:
                last_time = trip_timestamps[-1]
                trip_timestamps.extend([x+last_time for x in entry["timestamps"]])
        trip_latlngs = [[elem[1], elem[0]] for elem in trip_latlngs] # DeckGL requires coords in (lon,lat) format
        trip_latlngs[-1][1] += 0.000001 # weird bug: DeckGL animation cannot start and end at the same location - spawns two different points
        for pax in passengers:
            pax.distance_in_rideshare = distances["{},{}".format(pax.dest_depot.lat, pax.dest_depot.lon)]
            pax.distance_if_taken_alone = matrix["{},{};{},{}".format(starting_depot.lat, starting_depot.lon, pax.dest_depot.lat, pax.dest_depot.lon)]["route_distance"]
        return trip_latlngs, trip_distance, trip_duration, trip_timestamps



    def solve(self):
        self.active = True
        # Allocate vehicles to depots
        num_depots = len(self.DataFeed.getDepots())

        for idx, vehicle in enumerate(self.all_vehicle_list):
            depot = self.DataFeed.all_depots[idx % num_depots]
            depot.addVehicle(vehicle)
            vehicle.lat = depot.lat
            vehicle.lon = depot.lon
            vehicle.depot = depot


        start = time.time()

        max_wait_time_sec = 300
        max_capacity = 4
        total_passengers = 0
        served_passengers = 0
        time_sec = 0
        with open("Fleet_Simulator_App/static/depotmatrix.csv", "r") as f:
            matrix = json.load(f)
        trips = []
        metric_animations = {"NumOfActiveVehicles": [], "NumOfActivePassengers": [], "AVO": []}
        metrics = {"WalkDistToOriginKiosk": [], "WalkDistToDestKiosk": [], "RideDistIfTakenAlone": [], "RideDistInRideshare": [], "DifferenceInDistanceBetweenAloneAndRideshare": []}

        last_arrival_at_depot_time = 0

        accepting_passengers_until_time_sec = 1000

        while served_passengers < total_passengers or time_sec < accepting_passengers_until_time_sec or time_sec < last_arrival_at_depot_time + 1:
            # Assign riders to closest depots
            if time_sec<accepting_passengers_until_time_sec:
                lst_passengers_to_be_assigned = self.DataFeed.getRemainingPassengers(time_sec)
            for pax in lst_passengers_to_be_assigned:
                oDepot = self.getClosestDepot(pax.lat, pax.lon)
                pax.depot = oDepot
                dDepot = self.getClosestDepot(pax.dest_lat, pax.dest_lon)
                pax.dest_depot = dDepot
                if oDepot != dDepot:
                    oDepot.addPassenger(pax)
                    total_passengers += 1
                    metrics["WalkDistToOriginKiosk"].append(1.2*distance((pax.lat, pax.lon), (oDepot.lat, oDepot.lon)).meters)
                    metrics["WalkDistToDestKiosk"].append(1.2*distance((pax.dest_lat, pax.dest_lon), (dDepot.lat, dDepot.lon)).meters)



            # Assign riders to vehicles
            num_active_vehicles = 0
            num_active_passengers = 0
            for vehicle in self.all_vehicle_list:
                if vehicle.active == True:
                    num_active_vehicles += 1
                    num_active_passengers += vehicle.num_passengers
                    if vehicle.arrival_at_depot_time == time_sec:
                        vehicle.active = False
                        num_active_vehicles -= 1
                        num_active_passengers -= vehicle.num_passengers
                        continue
                if vehicle.active == False:
                    depot = vehicle.depot
                    if len(depot.lst_passengers) >= max_capacity:
                        # NEED TO REMOVE PASSENGER AT EACH COUNT, PLACE ANIMATION THAT SHOWS PASSENGER EXITS
                        passengers = depot.lst_passengers[:max_capacity]
                        trip_latlngs, trip_distance, trip_duration, trip_timestamps = self.routeVehicle(depot, passengers, matrix, time_sec)
                        trips.append({"vendor": max_capacity, "path": trip_latlngs, "timestamps": trip_timestamps})
                        for pax in passengers:
                            metrics["RideDistIfTakenAlone"].append(pax.distance_if_taken_alone)
                            metrics["RideDistInRideshare"].append(pax.distance_in_rideshare)
                            metrics["DifferenceInDistanceBetweenAloneAndRideshare"].append(pax.distance_in_rideshare - pax.distance_if_taken_alone)
                        vehicle.num_passengers = max_capacity
                        vehicle.arrival_at_depot_time = time_sec + int(trip_duration)
                        depot.lst_passengers = depot.lst_passengers[max_capacity:]
                        vehicle.active = True
                        num_active_vehicles += 1
                        num_active_passengers += max_capacity
                        served_passengers += max_capacity
                        last_arrival_at_depot_time = max(last_arrival_at_depot_time, vehicle.arrival_at_depot_time)
                    elif len(depot.lst_passengers) != 0:
                        if (time_sec - depot.lst_passengers[0].departure_time) >= max_wait_time_sec:
                            num_passengers = len(depot.lst_passengers)
                            passengers = depot.lst_passengers[:num_passengers]
                            trip_latlngs, trip_distance, trip_duration, trip_timestamps = self.routeVehicle(depot, passengers, matrix, time_sec)
                            trips.append({"vendor": num_passengers, "path": trip_latlngs, "timestamps": trip_timestamps})
                            for pax in passengers:
                                metrics["RideDistIfTakenAlone"].append(pax.distance_if_taken_alone)
                                metrics["RideDistInRideshare"].append(pax.distance_in_rideshare)
                                metrics["DifferenceInDistanceBetweenAloneAndRideshare"].append(pax.distance_in_rideshare - pax.distance_if_taken_alone)
                            vehicle.num_passengers = num_passengers
                            vehicle.arrival_at_depot_time = time_sec + int(trip_duration)
                            depot.lst_passengers = depot.lst_passengers[num_passengers:]
                            vehicle.active = True
                            num_active_vehicles += 1
                            num_active_passengers += num_passengers
                            served_passengers += num_passengers
                            last_arrival_at_depot_time = max(last_arrival_at_depot_time, vehicle.arrival_at_depot_time)

            metric_animations["NumOfActiveVehicles"].append(num_active_vehicles)
            metric_animations["NumOfActivePassengers"].append(num_active_passengers)
            if num_active_vehicles == 0:
                metric_animations["AVO"].append(0)
            else:
                metric_animations["AVO"].append(num_active_passengers/num_active_vehicles)

            time_sec += 1

        return json.dumps(trips), json.dumps(metrics), json.dumps(metric_animations), last_arrival_at_depot_time + 1, time.time() - start
