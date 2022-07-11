import numpy as np
import math

class Vehicle:
    def __init__(self, lat=None, lng=None, MAX_CAPACITY=4, kiosk=None):
        # Initialization variables
        self.lat = lat
        self.lng = lng
        self.kiosk = kiosk
        self.MAX_CAPACITY = MAX_CAPACITY

        #  Trip data
        self.lst_passengers = []
        self.curr_trip = []
        self.lst_arrival_times_by_kiosk = []
        self.num_passengers = 0
        self.trip_duration = None
        self.lst_leg_durations = []
        self.trip_distance = None
        self.lst_leg_distances = []
        self.lst_leg_latlngs = []
        self.lst_leg_timestamps = []
        self.enroute = False

        # Animation data
        self.popup_content = {}
        self.trips = []

    def __str__(self):
        return "Location: ({},{})\nCurrent Kiosk: {}\nNumber of passengers: {}\nDestinations:{}\n"\
            .format(self.lat,self.lng,self.kiosk.name,len(self.lst_passengers), self.curr_trip)

    def addTripLegs(self, lst_passengers, curr_trip, num_passengers, trip_duration, trip_distance, lst_leg_durations, lst_leg_distances, lst_leg_latlngs, lst_leg_timestamps, curr_time_in_sec):
        assert self.enroute == False, "You cannot assign a new route to this vehicle until the last one has finished."
        self.lst_passengers = lst_passengers
        self.curr_trip = curr_trip.copy()
        self.num_passengers = num_passengers
        self.trip_duration = trip_duration
        self.lst_leg_durations = lst_leg_durations.copy()
        self.trip_distance = trip_distance
        self.lst_leg_distances = lst_leg_distances.copy()
        self.lst_arrival_times_by_kiosk = list(np.cumsum(lst_leg_durations) + curr_time_in_sec)
        self.lst_leg_latlngs = lst_leg_latlngs.copy()
        self.lst_leg_timestamps = lst_leg_timestamps.copy()

    def hasArrivedAtNewKiosk(self, curr_time_in_sec):
        #print(self.lst_arrival_times_by_kiosk)
        if self.lst_arrival_times_by_kiosk[0] <= curr_time_in_sec:
            return True
        else:
            return False

    def isAtLastKiosk(self):
        return len(self.curr_trip) == 0

    def updateKiosk(self):
        new_kiosk = self.curr_trip[0]
        self.kiosk = new_kiosk
        self.lat = new_kiosk.lat
        self.lng = new_kiosk.lng
        return self.kiosk

    def removeTripLeg(self):
        self.curr_trip.pop(0)
        self.lst_arrival_times_by_kiosk.pop(0)
        self.trip_duration -= self.lst_leg_durations.pop(0)
        self.trip_distance -= self.lst_leg_distances.pop(0)
        self.lst_leg_latlngs.pop(0)
        self.lst_leg_timestamps.pop(0)

    def printTrip(self):
        print("CURR TRIP:",self.curr_trip)
        print("ARRIVAL TIMES:",self.lst_arrival_times_by_kiosk)
        print("TRIP DURATION:",self.trip_duration)
        print("TRIP DISTANCE:",self.trip_distance)
        print("LEG LATLNGS:",self.lst_leg_latlngs)
        print("LEG TIMESTAMPS:",self.lst_leg_timestamps)

    def resetTrip(self):
        self.lst_passengers = []
        self.curr_trip = []
        self.lst_arrival_times_by_kiosk = []
        self.num_passengers = 0
        self.trip_duration = None
        self.lst_leg_durations = []
        self.trip_distance = None
        self.lst_leg_distances = []
        self.lst_leg_latlngs = []
        self.lst_leg_timestamps = []

    def depart(self, curr_time_in_sec):
        self.enroute = True
        self.popup_content[curr_time_in_sec] = {
            "num_passengers": self.num_passengers,
            "passengers": [str(pax) for pax in self.lst_passengers],
            "destinations": [str(kiosk) for kiosk in self.curr_trip],
            "trip_duration": self.trip_duration,
            "trip_distance": self.trip_distance,
            "lst_leg_latlngs": self.lst_leg_latlngs,
            "lst_leg_durations": self.lst_leg_durations
        }
        self.trips.append({
            "num_passengers": self.num_passengers,
            "lnglats": [[lng, lat] for lat, lng in self.lst_leg_latlngs[0]],
            "timestamps": self.lst_leg_timestamps[0]
        })


    def arrive(self):
        self.enroute = False

    def isEnRoute(self):
        return self.enroute

    def getFinalKioskDestination(self):
        assert len(self.curr_trip) > 0, "This vehicle currently has no destinations set"
        return self.curr_trip[-1], self.lst_arrival_times_by_kiosk[-1]

    def getDroppedOffPassengers(self):
        passengers_that_are_dropped_off = []
        for pax in self.lst_passengers:
            if self.kiosk == pax.dest_kiosk:
                passengers_that_are_dropped_off.append(pax)
        return passengers_that_are_dropped_off

    def removePassengers(self, lst_passenger_objects):
        for pax in lst_passenger_objects:
            self.lst_passengers.remove(pax)
        self.num_passengers -= len(lst_passenger_objects)

    def getTrips(self):
        return self.trips
