class Vehicle:
    def __init__(self, lat=None, lon=None, capacity=4, SoC=100):
        self.lat = lat
        self.lon = lon
        self.depot = None
        self.capacity = capacity
        self.SoC = SoC
        self.active = False
        self.current_passenger = None
        # Trip Info
        self.trip_latlngs = None
        self.trip_distance = None
        self.trip_duration = None
        self.arrival_at_depot_time = 0
        # Next Destination
        self.dest_lat = None
        self.dest_lon = None
        self.route_latlngs = None
        self.route_distance = None
        self.route_duration = None
        # List of Destinations
        self.total_num_destinations = None
        self.num_destinations_remaining = None
        self.lst_lat = None
        self.lst_lon = None
        self.lst_route_latlngs = None
        self.lst_route_distance = None
        self.lst_route_duration = None
        self.lst_passengers = None
        self.num_passengers = None

    def __str__(self):
        return "Location: {0}\nCapacity: {1}\nSoC: {2}\nActive?: {3}\n".format((self.lat, self.lon), self.capacity, self.SoC, self.active)

    def getCurrentLocation(self):
        return (self.lat, self.lon)

    def setTrip(self, trip_latlngs, trip_distance, trip_duration, passengers):
        self.trip_latlngs = trip_latlngs
        self.trip_distance = trip_distance
        self.trip_duration = trip_duration
        self.lst_passengers = passengers

    def getPaxIds(self):
        lst_ids = []
        for passenger in self.lst_passengers:
            lst_ids.append(id(passenger))
        return lst_ids

    def setListDestinations(self, num_destinations, passengers, lst_lat, lst_lon, lst_route_latlngs, lst_route_distance, lst_route_duration):
        self.total_num_destinations = num_destinations
        self.num_destinations_remaining = num_destinations
        self.lst_passengers = passengers
        self.lst_lat = lst_lat
        self.lst_lon = lst_lon
        self.lst_route_latlngs = lst_route_latlngs
        self.lst_route_distance = lst_route_distance
        self.lst_route_duration = lst_route_duration

    def moveToNextDestination(self):
        curr_destination_index = self.total_num_destinations - self.num_destinations_remaining
        self.current_passenger = self.lst_passengers[curr_destination_index]
        self.dest_lat = self.lst_lat[curr_destination_index]
        self.dest_lon = self.lst_lon[curr_destination_index]
        self.route_latlngs = self.lst_route_latlngs[curr_destination_index]
        self.route_distance = self.lst_route_distance[curr_destination_index]
        self.route_duration = self.lst_route_duration[curr_destination_index]

    def decreaseCapacity(self):
        self.capacity -= 1

    def decreaseSoC(self):
        self.SoC = self.SoC - self.route_distance

    def arrivedAtDestination(self):
        self.num_destinations_remaining -= 1
        self.decreaseSoC()
        self.decreaseCapacity()

        if self.num_destinations_remaining > 0:
            self.moveToNextDestination()
            return False
        else:
            return True

    def setActive(self, bool):
        self.active = bool

    def getAnimationDetails(self):
        result = {'car_idx': id(self), 'latlngs': self.trip_latlngs, 'speed': self.trip_duration, 'lst_pax_id': self.getPaxIds(), 'distance': self.trip_distance}
        return result

    def start(self):
        self.active = True
