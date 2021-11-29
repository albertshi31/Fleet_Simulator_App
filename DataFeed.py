from Depot import Depot
from Passenger import Passenger
from Vehicle import Vehicle
import csv
import random

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
        self.all_passengers = []

    def parseDepots(self):
        with open(self.depot_csv, 'r', encoding='utf-8-sig') as file:
            csvreader = csv.reader(file)
            header = next(csvreader)
            name_idx = header.index("Name")
            lat_idx = header.index("Lat")
            long_idx = header.index("Long")
            for row in csvreader:
                newDepot = Depot(row[name_idx], row[lat_idx], row[long_idx])
                self.all_depots.append(newDepot)

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
        idx = 0
        for pax in self.remaining_passengers:
            if pax.departure_time > time:
                break
            idx += 1
        result = self.remaining_passengers[:idx]
        self.remaining_passengers = self.remaining_passengers[idx:]
        return result
