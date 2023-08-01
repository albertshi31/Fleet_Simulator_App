import numpy as np
import math

class Vehicle:
    def __init__(self, id=None, lat=None, lng=None, MAX_CAPACITY=4, kiosk=None):
        # Initialization variables
        self.id = id
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
        self.tripsCompleted = 0

        # Animation data
        self.trips = []

        # EOD data
        self.all_passengers_served = []
        self.total_distance_traveled = 0
        self.total_empty_distance_traveled = 0
        self.departure_vehicle_occupancy = []
        self.total_duration_traveled = 0
        self.total_empty_duration_traveled = 0

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
        self.total_distance_traveled += self.lst_leg_distances[0]
        self.total_duration_traveled += self.lst_leg_durations[0]
        self.tripsCompleted += 1
        if self.num_passengers == 0:
            self.total_empty_distance_traveled += self.lst_leg_distances[0]
            self.total_empty_duration_traveled += self.lst_leg_durations[0]
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

    # This is where the overlay popup info for the vehicles comes from
    def depart(self, curr_time_in_sec):
        self.enroute = True
        self.departure_vehicle_occupancy.append(self.num_passengers)
        msg = "Vehicle ID: {}".format(self.id)
        if self.num_passengers == 0:
            msg += "\nRepositioning to Kiosk #{}".format(self.curr_trip[0].getID())
        else:
            msg += "\nComing From Kiosk #{}\nDropping off:".format(self.kiosk.getID())
            for pax in self.lst_passengers:
                msg += "\nPax at Kiosk {}, waittime {}s".format(pax.getDKiosk().getID(), pax.getWaittime())
        msg += "\nTrip Duration: {}min\nTrip Distance: {}mi".format(round(self.trip_duration/60, 1), round(self.trip_distance/1609.34, 1))
        msg += "\nTrips Completed So Far: {}".format(self.getTripsCompleted())
        self.trips.append({
            "id": self.id,
            "num_passengers": self.num_passengers,
            "lnglats": [[lng, lat] for lat, lng in self.lst_leg_latlngs[0]],
            "timestamps": self.lst_leg_timestamps[0],
            "msg": msg,
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
        self.all_passengers_served.extend(lst_passenger_objects)

    def getPassengers(self):
        return self.lst_passengers

    def getTrips(self):
        return self.trips

    def getTripsCompleted(self):
        return self.tripsCompleted

    def getDVO(self):
        return self.departure_vehicle_occupancy

    def getTotalDistanceTraveled(self):
        return self.total_distance_traveled

    def getTotalEmptyDistanceTraveled(self):
        return self.total_empty_distance_traveled

    def setID(self, id):
        self.ID = id

    def getTotalDurationTraveled(self):
        return self.total_duration_traveled

    def getTotalEmptyDurationTraveled(self):
        return self.total_empty_duration_traveled
