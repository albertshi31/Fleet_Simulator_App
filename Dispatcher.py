from Passenger import Passenger
from Vehicle import Vehicle
from DataFeed import DataFeed
import requests
import time
from geopy.distance import distance
import json
import os

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

    def routeVehicle(self, starting_depot, passengers, ending_depot, matrix, start_time, total_num_passengers, trips, num_active_passengers_decreases_over_time):
        lst_locations = list(set([pax.dest_depot for pax in passengers]))
        lst_locations.insert(0, starting_depot)
        if ending_depot:
            lst_locations.append(ending_depot)
            #print("THIS MEANS REPOSITIONING IS HAPPENING")
        trip_latlngs = []
        distances = {}
        trip_distance = 0
        trip_duration = 0
        trip_timestamps = []
        num_passengers = total_num_passengers
        for idx, pair in enumerate(list(zip(lst_locations, lst_locations[1:]))):
            entry = matrix["{},{};{},{}".format(pair[0].lat, pair[0].lon, pair[1].lat, pair[1].lon)]
            trip_latlngs = entry["route_latlngs"]
            trip_latlngs = [[elem[1], elem[0]] for elem in trip_latlngs] # DeckGL requires coords in (lon,lat) format
            trip_timestamps = [x+start_time+trip_duration for x in entry["timestamps"]]
            # Used for trips animations
            new_entry = {"vendor": num_passengers, "path": trip_latlngs, "timestamps": trip_timestamps}
            trips.append(new_entry)

            trip_duration += entry["route_duration"]

            num_passengers_exiting_vehicle_at_this_stop = 0
            for pax in passengers:
                if pax.dest_depot == pair[1]:
                    num_passengers_exiting_vehicle_at_this_stop += 1

            key = start_time + int(trip_duration)
            if key in num_active_passengers_decreases_over_time:
                num_active_passengers_decreases_over_time[key] += num_passengers_exiting_vehicle_at_this_stop
            else:
                num_active_passengers_decreases_over_time[key] = num_passengers_exiting_vehicle_at_this_stop

            num_passengers -= num_passengers_exiting_vehicle_at_this_stop # Passenger(s) exit

            # Used for passenger metrics
            trip_distance += entry["route_distance"]
            distances["{},{}".format(pair[1].lat, pair[1].lon)] = trip_distance

        assert (num_passengers == 0), "Vehicle should have droppped off all passengers"

        # Update passenger values
        for pax in passengers:
            pax.distance_in_rideshare = distances["{},{}".format(pax.dest_depot.lat, pax.dest_depot.lon)]
            pax.distance_if_taken_alone = matrix["{},{};{},{}".format(starting_depot.lat, starting_depot.lon, pax.dest_depot.lat, pax.dest_depot.lon)]["route_distance"]
            #assert (pax.distance_if_taken_alone <= pax.distance_in_rideshare) FIGURE OUT WHY THIS ISN'T WORKING
        return trip_duration, lst_locations[-1]



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
        leave_after_wait_time_sec = 480
        max_capacity = 4
        total_passengers = 0
        served_passengers = 0
        time_sec = 0
        THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
        my_file = os.path.join(THIS_FOLDER, "static", "depotmatrix.csv")
        with open(my_file, "r") as f:
            matrix = json.load(f)
        trips = []
        depot_locations = []
        waiting_passengers = []
        waiting_vehicles = []
        num_active_passengers_decreases_over_time = {}
        metric_animations = {"NumOfActiveVehicles": [], "NumOfActivePassengers": [], "AVO": [], "PassengersLeft": []}
        metrics = {"WalkDistToOriginKiosk": [], "WalkDistToDestKiosk": [], "RideDistIfTakenAlone": [], "RideDistInRideshare": [], "DifferenceInDistanceBetweenAloneAndRideshare": [], "AVO": []}

        last_arrival_at_depot_time = 0

        accepting_passengers_until_time_sec = 5000

        num_active_vehicles = 0
        num_active_passengers = 0
        passengers_left = 0

        kiosks_havent_received_repositioned_vehicles = []

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


            if time_sec % leave_after_wait_time_sec == 0: # FIX NUMBER
                kiosks_havent_received_repositioned_vehicles = self.DataFeed.all_depots[:]
                #print("REFRESH:", len(kiosks_havent_received_repositioned_vehicles))

            # Assign riders to vehicles
            for vehicle in self.all_vehicle_list:
                # If vehicle has left home depot with passengers
                if vehicle.active == True:
                    if vehicle.arrival_at_depot_time == time_sec:
                        vehicle.active = False
                        vehicle.depot.addVehicle(vehicle)
                        num_active_vehicles -= 1
                        continue
                # If vehicle is currently waiting at home depot
                if vehicle.active == False:
                    depot = vehicle.depot
                    if len(depot.lst_passengers) >= max_capacity:
                        # NEED TO REMOVE PASSENGER AT EACH COUNT, PLACE ANIMATION THAT SHOWS PASSENGER EXITS
                        passengers = depot.lst_passengers[:max_capacity]
                        trip_duration, last_depot = self.routeVehicle(depot, passengers, None, matrix, time_sec, max_capacity, trips, num_active_passengers_decreases_over_time)
                        for pax in passengers:
                            metrics["RideDistIfTakenAlone"].append(pax.distance_if_taken_alone)
                            metrics["RideDistInRideshare"].append(pax.distance_in_rideshare)
                            metrics["DifferenceInDistanceBetweenAloneAndRideshare"].append(pax.distance_in_rideshare - pax.distance_if_taken_alone)
                        vehicle.num_passengers = max_capacity
                        vehicle.arrival_at_depot_time = time_sec + int(trip_duration)
                        depot.lst_passengers = depot.lst_passengers[max_capacity:]
                        vehicle.active = True
                        vehicle.depot.removeVehicle(vehicle)
                        vehicle.depot = last_depot
                        num_active_vehicles += 1
                        num_active_passengers += max_capacity
                        served_passengers += max_capacity
                        last_arrival_at_depot_time = max(last_arrival_at_depot_time, vehicle.arrival_at_depot_time)
                    elif len(depot.lst_passengers) != 0:
                        # If vehicle is present at depot, then depart with < max_capacity passengers
                        if (time_sec - depot.lst_passengers[0].departure_time) >= max_wait_time_sec:
                            num_passengers = len(depot.lst_passengers)
                            passengers = depot.lst_passengers[:num_passengers]
                            trip_duration, last_depot = self.routeVehicle(depot, passengers, None, matrix, time_sec, num_passengers, trips, num_active_passengers_decreases_over_time)
                            for pax in passengers:
                                metrics["RideDistIfTakenAlone"].append(pax.distance_if_taken_alone)
                                metrics["RideDistInRideshare"].append(pax.distance_in_rideshare)
                                metrics["DifferenceInDistanceBetweenAloneAndRideshare"].append(pax.distance_in_rideshare - pax.distance_if_taken_alone)
                            vehicle.num_passengers = num_passengers
                            vehicle.arrival_at_depot_time = time_sec + int(trip_duration)
                            depot.lst_passengers = depot.lst_passengers[num_passengers:]
                            vehicle.active = True
                            vehicle.depot.removeVehicle(vehicle)
                            vehicle.depot = last_depot
                            num_active_vehicles += 1
                            num_active_passengers += num_passengers
                            served_passengers += num_passengers
                            last_arrival_at_depot_time = max(last_arrival_at_depot_time, vehicle.arrival_at_depot_time)
                    else: # Empty vehicle repositioning
                        number_of_waiting_passengers_at_each_depot = [len(depot.lst_passengers) for depot in kiosks_havent_received_repositioned_vehicles]
                        depot_with_most_waiting_passengers = kiosks_havent_received_repositioned_vehicles[number_of_waiting_passengers_at_each_depot.index(max(number_of_waiting_passengers_at_each_depot))]
                        if max(number_of_waiting_passengers_at_each_depot) > len(depot_with_most_waiting_passengers.lst_vehicles)*max_capacity: # FIX NUMBER
                            kiosks_havent_received_repositioned_vehicles.remove(depot_with_most_waiting_passengers)
                            #print(len(kiosks_havent_received_repositioned_vehicles))
                            trip_duration, last_depot = self.routeVehicle(depot, [], depot_with_most_waiting_passengers, matrix, time_sec, 0, trips, num_active_passengers_decreases_over_time)
                            vehicle.num_passengers = 0
                            vehicle.arrival_at_depot_time = time_sec + int(trip_duration)
                            vehicle.active = True
                            vehicle.depot.removeVehicle(vehicle)
                            vehicle.depot = last_depot
                            num_active_vehicles += 1
                            num_active_passengers += 0
                            served_passengers += 0
                            last_arrival_at_depot_time = max(last_arrival_at_depot_time, vehicle.arrival_at_depot_time)

            waiting_passengers_for_this_time_frame = []
            waiting_vehicles_for_this_time_frame = []
            # Check all depots for waiting passengers
            for depot in self.DataFeed.all_depots:
                for pax in depot.lst_passengers:
                    # Passengers begin leaving after very long wait time
                    if time_sec - pax.departure_time >= leave_after_wait_time_sec:
                        depot.lst_passengers = depot.lst_passengers[1:]
                        served_passengers += 1
                        passengers_left += 1
                        # Add passenger leaving animation to Trips Layer
                        trips.append({"vendor": 5, "path": [[depot.lon, depot.lat], [depot.lon, depot.lat-0.004]], "timestamps": [time_sec, time_sec+60]})
                # count number of passengers and vehicles still waiting at this depot
                waiting_passengers_for_this_time_frame.append({"coordinates": [depot.lon, depot.lat], "number": str(len(depot.lst_passengers))})
                waiting_vehicles_for_this_time_frame.append({"coordinates": [depot.lon, depot.lat], "number": str(len(depot.lst_vehicles))})

            waiting_passengers.append(waiting_passengers_for_this_time_frame)
            waiting_vehicles.append(waiting_vehicles_for_this_time_frame)


            metric_animations["NumOfActiveVehicles"].append(num_active_vehicles)

            decrease = 0
            if time_sec in num_active_passengers_decreases_over_time:
                decrease = num_active_passengers_decreases_over_time[time_sec]
            num_active_passengers -= decrease
            metric_animations["NumOfActivePassengers"].append(num_active_passengers)

            if num_active_vehicles == 0:
                metric_animations["AVO"].append(0)
                metrics["AVO"].append(0)
            else:
                metric_animations["AVO"].append(num_active_passengers/num_active_vehicles)
                metrics["AVO"].append(round(num_active_passengers/num_active_vehicles, 2))

            metric_animations["PassengersLeft"].append(passengers_left)

            # print("TIME", time_sec)
            time_sec += 1

        # Generate depot locations
        for depot in self.DataFeed.all_depots:
            depot_locations.append({"coordinates": [depot.lon, depot.lat]})

        return json.dumps(trips), json.dumps(depot_locations), json.dumps(waiting_passengers), json.dumps(waiting_vehicles), json.dumps(metrics), json.dumps(metric_animations), last_arrival_at_depot_time + 1, time.time() - start
