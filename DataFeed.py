from Depot import Depot
from Passenger import Passenger
from Vehicle import Vehicle
import csv
import random
import h3
from geopy.distance import distance


# Need to change to OFIPS instead of min/max lat/lon
class DataFeed:
    def __init__(self, depot_csv=None, lst_passenger_csv=None, min_lat=None, max_lat=None, min_lng=None, max_lng=None, modesplit=None):
        self.depot_csv = depot_csv
        self.lst_passenger_csv = lst_passenger_csv
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lng = min_lng
        self.max_lng = max_lng
        self.modesplit = modesplit
        self.all_depots = []
        self.current_index_passenger_list = 0
        self.all_passengers = []
        self.dict_h3_indices_depots = {}
        self.STARTING_RESOLUTION = 10
        self.SEARCH_RADIUS = 8

    def parseDepots(self):
        with open(self.depot_csv, 'r', encoding='utf-8-sig') as file:
            csvreader = csv.reader(file)
            header = next(csvreader)
            name_idx = header.index("Name")
            lat_idx = header.index("Lat")
            long_idx = header.index("Long")
            for row in csvreader:
                lat = float(row[lat_idx])
                long = float(row[long_idx])
                newDepot = Depot(row[name_idx], lat, long)
                self.all_depots.append(newDepot)
                for resolution in range(self.STARTING_RESOLUTION, 4, -1):
                    h3_index = h3.geo_to_h3(lat, long, resolution)
                    if h3_index in self.dict_h3_indices_depots:
                        self.dict_h3_indices_depots[h3_index].append(newDepot)
                    else:
                        self.dict_h3_indices_depots[h3_index] = [newDepot]

    def getDepots(self):
        return self.all_depots

    def isInBounds(self, lat, lng, dest_lat, dest_lng):
        result1 = self.min_lat <= lat and lat <= self.max_lat and self.min_lng <= lng and lng <= self.max_lng
        result2 = self.min_lat <= dest_lat and dest_lat <= self.max_lat and self.min_lng <= dest_lng and dest_lng <= self.max_lng
        return result1 and result2

    def parsePassengers(self):
        for filename in self.lst_passenger_csv:
            with open(filename, 'r', encoding='utf-8-sig') as file:
                csvreader = csv.reader(file)
                header = next(csvreader)
                lat_idx = header.index("OLat")
                long_idx = header.index("OLon")
                dest_lat_idx = header.index("DLat")
                dest_long_idx = header.index("DLon")
                departure_time_idx = header.index("ODepartureTime")
                for row in csvreader:
                    lat = float(row[lat_idx])
                    lng = float(row[long_idx])
                    dest_lat = float(row[dest_lat_idx])
                    dest_lng = float(row[dest_long_idx])
                    departure_time = int(row[departure_time_idx])
                    if self.isInBounds(lat, lng, dest_lat, dest_lng):
                        if random.choices([1, 0], weights=(self.modesplit, 100-self.modesplit))[0]:
                            newPassenger = Passenger(lat,
                                                    lng,
                                                    dest_lat,
                                                    dest_lng,
                                                    departure_time,
                                                    random.choice([0, 1, 2]))
                            # for resolution in [8, 7, 6, 5]:
                            #     h3_index_origin = h3.geo_to_h3(lat, lng, resolution)
                            #     newPassenger.lst_h3_indices_origin.append(h3_index_origin)
                            #     h3_index_destination = h3.geo_to_h3(lat, lng, resolution)
                            #     newPassenger.lst_h3_indices_destination.append(h3_index_destination)
                            self.all_passengers.append(newPassenger)

        # Sort passengers by departure_time
        self.all_passengers.sort(key=lambda pax: pax.departure_time)
        self.remaining_passengers = self.all_passengers.copy()

    def getAllPassengers(self):
        return self.all_passengers

    def getLastPassengerTime(self):
        return self.all_passengers[-1].departure_time

    def resetPassengerList(self):
        self.remaining_passengers = self.all_passengers.copy()

    def resetDepots(self):
        for depot in self.all_depots:
            depot.reset()

    def getRemainingPassengers(self, time):
        result = []
        if time > self.all_passengers[-1].departure_time:
            return result
        start_index = self.current_index_passenger_list
        advance_counter = 0
        while(True):
            if start_index + advance_counter == len(self.all_passengers):
                break
            pax = self.all_passengers[start_index + advance_counter]
            if pax.departure_time > time:
                break
            advance_counter += 1
        self.current_index_passenger_list += advance_counter
        result = self.all_passengers[start_index:start_index+advance_counter]
        return result


    def getClosestDepot(self, lat, lon):
        resolution = self.STARTING_RESOLUTION
        while resolution > 4:
            h3_index = h3.geo_to_h3(lat, lon, resolution)
            if h3_index in self.dict_h3_indices_depots:
                if len(self.dict_h3_indices_depots[h3_index]) == 1:
                    return self.dict_h3_indices_depots[h3_index][0]
                else:
                    lst_distances = []
                    for depot in self.dict_h3_indices_depots[h3_index]:
                        lst_distances.append(distance((lat, lon), (depot.lat, depot.lon)).meters)
                    closest_depot = self.dict_h3_indices_depots[h3_index][lst_distances.index(min(lst_distances))]
                    return closest_depot
            else:
                resolution -= 1

    def getNearbyDepots(self, lat, lon):
        lst_nearby_depots = []
        resolution = self.STARTING_RESOLUTION
        h3_index = h3.geo_to_h3(lat, lon, resolution)
        for idx in list(h3.k_ring(h3_index, self.SEARCH_RADIUS)):
            if idx in self.dict_h3_indices_depots:
                lst_nearby_depots.extend(self.dict_h3_indices_depots[idx])
        return lst_nearby_depots


#a = DataFeed("local_static/Trenton_AV_Station.csv", ['local_static/2020_OriginPixel34021_1.csv', 'local_static/2020_OriginPixel34021_2.csv'], 40.1976591962, 40.2573225184, -74.7999188569, -74.734932536, float(100.0))
#a.parseDepots()
#a.parsePassengers()
#print(a.getClosestDepot(40.19865883770,-74.77))
# print(a.getDepots())
#print(len(a.getAllPassengers()))
