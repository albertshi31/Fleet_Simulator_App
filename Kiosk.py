class Kiosk:
    def __init__(self, name, lat, lng, xcoord, ycoord):
        # Initialization Data
        self.name = name
        self.lat = lat
        self.lng = lng
        self.xcoord = xcoord
        self.ycoord = ycoord

        # State data
        self.lst_vehicle_objects = []
        self.lst_tuples_of_incoming_vehicle_objects_and_arrival_times = []
        self.lst_passenger_objects = [] # This refers to list of departing passenger objects
        self.lst_new_departing_passenger_objects = []
        self.dict_lst_lsts_passenger_groupings = {} # The key should be the latest that the group can depart without anyone leaving
        self.lst_missed_passenger_objects = []
        self.net_vehicle_balance = 0

        # History data
        self.lst_all_departing_passengers = [] # Remembers all passengers that departed from this kiosk
        self.lst_all_arriving_passengers = [] # Remembers all passengers that arrived to this kiosk

    def __str__(self):
        return "Name: {}\nLat, Lng: ({}, {})\nPixel Coordinates: ({}, {})\n".format(self.name, self.lat, self.lng, self.xcoord, self.ycoord)

    def printState(self):
        ret_str = "Name: {}\nLat, Lng: ({}, {})\nWaiting Passengers: {}\nVehicles: {}\nIncoming Vehicles: {}\nPax Groups: {}\nArrived Pax: {}"\
                    .format(self.name, self.lat, self.lng, self.lst_passenger_objects, self.lst_vehicle_objects, self.lst_tuples_of_incoming_vehicle_objects_and_arrival_times, self.dict_lst_lsts_passenger_groupings, self.lst_all_arriving_passengers)
        return ret_str

    def getLatLng(self):
        return (self.lat, self.lng)

    def getXYPixelCoords(self):
        return (self.xcoord, self.ycoord)

    def addVehicle(self, vehicle_object):
        self.lst_vehicle_objects.append(vehicle_object)

    def addIncomingVehicle(self, vehicle_object, arrival_time):
        self.lst_tuples_of_incoming_vehicle_objects_and_arrival_times.append((vehicle_object, arrival_time))

    def removeVehicle(self, vehicle_object):
        self.lst_vehicle_objects.remove(vehicle_object)

    def removeIncomingVehicle(self, vehicle_object):
        tup_dict = dict(self.lst_tuples_of_incoming_vehicle_objects_and_arrival_times)
        tup_dict.pop(vehicle_object)
        self.lst_tuples_of_incoming_vehicle_objects_and_arrival_times = list(tuple(tup_dict.items()))

    def getVehicles(self):
        return self.lst_vehicle_objects

    def addDepartingPassenger(self, passenger_object):
        self.lst_passenger_objects.append(passenger_object)
        self.lst_all_departing_passengers.append(passenger_object)

    def removeDepartingPassenger(self, passenger_object):
        self.lst_passenger_objects.remove(passenger_object)

    def removeDepartingPassengers(self, passenger_group):
        for pax in passenger_group:
            self.lst_passenger_objects.remove(pax)
        key = min(passenger_group, key=lambda pax: pax.odeparturetime).odeparturetime
        self.dict_lst_lsts_passenger_groupings[key].remove(passenger_group)

    def addArrivingPassengers(self, lst_passenger_objects):
        self.lst_all_arriving_passengers.extend(lst_passenger_objects)

    def addMissedPassenger(self, passenger_object):
        self.lst_missed_passenger_objects.append(passenger_object)

    def getMissedPassengers(self):
        return self.lst_missed_passenger_objects

    def getArrivedPassengers(self):
        return self.lst_all_arriving_passengers

    def getPassengerObjects(self):
        return self.lst_passenger_objects

    def addNewDepartingPassenger(self, passenger_object):
        self.lst_new_departing_passenger_objects.append(passenger_object)

    def getNewDepartingPassengerObjects(self):
        return self.lst_new_departing_passenger_objects

    def resetNewDepartingPassengerObjects(self):
        self.lst_new_departing_passenger_objects = []

    def getPassengerGroupings(self):
        return self.dict_lst_lsts_passenger_groupings

    def setPassengerGroupings(self, sorted_dict_passenger_groups):
        self.dict_lst_lsts_passenger_groupings = sorted_dict_passenger_groups

    def getNumPassengerGroupings(self):
        num = 0
        for lst_passenger_groups in self.dict_lst_lsts_passenger_groupings.values():
            num += len(lst_passenger_groups)
        return num

    # Will be positive if we have a surplus of vehicles
    def updateNetVehicleBalance(self, passenger_waittime_threshhold):
        # The number of vehicles the kiosk should request is the difference between the number of passenger groupings
        # and the combination of (incoming vehicles that arrive before the first passenger group departs) and (vehicles it currently has at the kiosk)
        num_incoming_vehicles_that_arrive_on_time = 0
        i = 0 # Arrival times index - for incoming vehicles
        j = 0 # Departing times index - for passenger groups
        arrival_times = [arrival_time for vehicle, arrival_time in self.lst_tuples_of_incoming_vehicle_objects_and_arrival_times]
        arrival_times.sort()
        departing_times = []
        # Key is departing time of passenger groups
        # Value is the list of passenger groups (2D array)
        for key, value in self.dict_lst_lsts_passenger_groupings.items():
            for i in range(len(value)):
                departing_times.append(key+passenger_waittime_threshhold)

        while i < len(arrival_times) and j < len(departing_times):
            if arrival_times[i] <= departing_times[j]:
                i += 1
                j += 1
                num_incoming_vehicles_that_arrive_on_time += 1
            else:
                j += 1
        self.net_vehicle_balance = (len(self.lst_vehicle_objects) + num_incoming_vehicles_that_arrive_on_time) - self.getNumPassengerGroupings()

    def getNetVehicleBalance(self):
        return self.net_vehicle_balance

    def removeMissedPassengers(self, curr_time_in_sec, passenger_waittime_threshold):
        ret_lst_missed_passengers = []
        idx = 0
        for idx, pax in enumerate(self.lst_passenger_objects):
            missed_time = pax.odeparturetime + passenger_waittime_threshold
            if missed_time < curr_time_in_sec:
                ret_lst_missed_passengers.append(pax)
            else:
                break
        for pax in ret_lst_missed_passengers:
            self.lst_passenger_objects.remove(pax)
        self.lst_missed_passenger_objects.extend(ret_lst_missed_passengers)
        return ret_lst_missed_passengers

    # Kiosk should check if any of its passenger groupings should be assigned a vehicle
    # There are two possible scenarios:
    # 1. A passenger in any passenger grouping waits passenger_waittime_threshold time
    # 2. Length of any passenger grouping equals the MAX_CAPACITY
    # Return these passenger groupings as 2D array
    def getPassengerGroupsReadyToLeave(self, curr_time_in_sec, passenger_waittime_threshold, MAX_CAPACITY):
        return_lst_of_lsts_of_passenger_groupings = []
        # Look at all passenger groups and see if any of their members waited equal to or more than the threshold
        for key, lst_lsts_passenger_groupings in self.dict_lst_lsts_passenger_groupings.items():
            if curr_time_in_sec - key >= passenger_waittime_threshold: # passenger group waits the threshold time
                return_lst_of_lsts_of_passenger_groupings.extend(lst_lsts_passenger_groupings)
            else:
                # Look at all passenger groups and see if any have MAX_CAPACITY passengers and add them to the return list
                for lst_passenger_grouping in lst_lsts_passenger_groupings:
                    if len(lst_passenger_grouping) == MAX_CAPACITY:
                        return_lst_of_lsts_of_passenger_groupings.append(lst_passenger_grouping)

        return return_lst_of_lsts_of_passenger_groupings
