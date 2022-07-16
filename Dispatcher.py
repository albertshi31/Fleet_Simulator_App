from Vehicle import Vehicle
import numpy as np
from geopy.distance import distance
import json
class Dispatcher:
    def __init__(self, lst_all_passenger_objects, lst_all_kiosk_objects, lst_all_vehicle_objects, passenger_waittime_threshold, kiosk_to_kiosk_route_matrix, MAX_VEHICLES, MAX_CAPACITY, TIME_STEP):
        self.lst_all_passenger_objects = lst_all_passenger_objects
        self.lst_remaining_passenger_objects = lst_all_passenger_objects
        self.lst_all_kiosk_objects = lst_all_kiosk_objects
        self.lst_all_vehicle_objects = lst_all_vehicle_objects
        self.passenger_waittime_threshold = passenger_waittime_threshold
        self.kiosk_to_kiosk_route_matrix = kiosk_to_kiosk_route_matrix
        self.MAX_VEHICLES = MAX_VEHICLES
        self.MAX_CAPACITY = MAX_CAPACITY
        self.TIME_STEP = TIME_STEP

        # Metrics
        self.timeframe_metrics = {}
        self.EOD_metrics = {}
        self.animation_trips = []
        self.kiosk_timeframe_metrics = {}

    ############################################################################
    # ASSIGNING PASSENGERS TO KIOSKS FUNCTIONS #

    # Takes in curr_time_in_sec(int)
    # Returns passenger objects that have odeparturetime <= curr_time_in_sec (lst)
    def getPassengersThatLeaveByTimeXInSec(self, curr_time_in_sec):
        return_lst_passengers_that_leave_by_time_x_in_sec = []
        if len(self.lst_remaining_passenger_objects) == 0:
            return return_lst_passengers_that_leave_by_time_x_in_sec

        for idx, pax in enumerate(self.lst_remaining_passenger_objects):
            if pax.odeparturetime <= curr_time_in_sec:
                return_lst_passengers_that_leave_by_time_x_in_sec.append(pax)
                if idx == (len(self.lst_remaining_passenger_objects) - 1):
                    idx += 1
            else:
                break
        self.lst_remaining_passenger_objects = self.lst_remaining_passenger_objects[idx:]
        return return_lst_passengers_that_leave_by_time_x_in_sec

    # Takes in list of kiosks (of length at least 1) and outputs the kiosk closest to the given (lat,lng)
    # This accounts for possibility of more than one kiosk per pixel
    def getClosestKioskToLatLng(self, lst_kiosks, lat, lng):
        closest_kiosk = min(lst_kiosks, key=lambda kiosk:distance((kiosk.lat, kiosk.lng), (lat, lng)))
        return closest_kiosk

    # This function takes in a list of kiosks (of length at least 1), a kiosk, and a matrix of routes and returns
    # the closest kiosk in the list. This reduces runtime because geopy does not need to be used
    def getClosestKioskToKiosk(self, lst_kiosks, okiosk, matrix):
        closest_kiosk = lst_kiosks[0]
        dist_btwn_kiosks = matrix[str([okiosk.getLatLng(), closest_kiosk.getLatLng()])]["duration"]
        for kiosk in lst_kiosks:
            if (matrix[str([okiosk.getLatLng(), kiosk.getLatLng()])]["duration"] < dist_btwn_kiosks):
                closest_kiosk = kiosk
                dist_btwn_kiosks = matrix[str([okiosk.getLatLng(), kiosk.getLatLng()])]["duration"]
        return closest_kiosk

    # Create dictionary to make enable easy lookup of kiosk by pixel coords:
        # Key: (XCoord, YCoord)
        # Value: Kiosk object in that pixel
    def getDictKiosksByPixel(self):
        dict_kiosks_by_pixel = {}
        for kiosk in self.lst_all_kiosk_objects:
            key = kiosk.getXYPixelCoords()
            if key in dict_kiosks_by_pixel:
                dict_kiosks_by_pixel[key].append(kiosk)
            else:
                dict_kiosks_by_pixel[key] = [kiosk]
        return dict_kiosks_by_pixel


    ############################################################################
    # VEHICLE ROUTING ALGORITHMS #

    def create_vehicle_with_passengers_route(self, starting_kiosk, passengers, matrix, curr_time_in_sec):
        ret_list = []
        remaining_dests = []
        trip_duration = 0
        trip_distance = 0
        lst_leg_durations = []
        lst_leg_distances = []
        lst_leg_latlngs = []
        lst_leg_timestamps = []

        for pax in passengers:
            if pax.dest_kiosk not in remaining_dests:
                remaining_dests.append(pax.dest_kiosk)

        curr = starting_kiosk
        while remaining_dests:
            distances = []
            durations = []
            latlngs = []
            timestamps = []
            for i in range(len(remaining_dests)):
                matrix_data = matrix[str([curr.getLatLng(), remaining_dests[i].getLatLng()])]

                currduration = matrix_data["duration"]
                durations.append(currduration)

                currdistance = matrix_data["distance"]
                distances.append(currdistance)

                currlatlngs = matrix_data["latlngs"]
                latlngs.append(currlatlngs)

                currtimestamps = matrix_data["timestamps"]
                timestamps.append(currtimestamps)

            idx = np.argmin(durations)
            curr = remaining_dests[idx]
            remaining_dests.remove(curr)
            ret_list.append(curr)
            trip_duration += durations[idx]
            trip_distance += distances[idx]
            lst_leg_durations.append(durations[idx])
            lst_leg_distances.append(distances[idx])
            lst_leg_latlngs.append(latlngs[idx])
            lst_leg_timestamps.append([x+curr_time_in_sec for x in matrix_data["timestamps"]])

        assert len(ret_list) == len(lst_leg_latlngs), "All lists should have the same length"
        curr_trip = ret_list
        return passengers, curr_trip, len(passengers), trip_duration, trip_distance, lst_leg_durations, lst_leg_distances, lst_leg_latlngs, lst_leg_timestamps

    def create_empty_vehicle_route(self, starting_kiosk, ending_kiosk, matrix, curr_time_in_sec):
        matrix_data = matrix[str([starting_kiosk.getLatLng(), ending_kiosk.getLatLng()])]
        passengers = []
        curr_trip = [ending_kiosk]
        trip_duration = matrix_data["duration"]
        trip_distance = matrix_data["distance"]
        lst_leg_durations = [trip_duration]
        lst_leg_distances = [trip_distance]
        lst_leg_latlngs = []
        lst_leg_latlngs.append(matrix_data["latlngs"])
        lst_leg_timestamps = []
        lst_leg_timestamps.append([x+curr_time_in_sec for x in matrix_data["timestamps"]])
        return passengers, curr_trip, len(passengers), trip_duration, trip_distance, lst_leg_durations, lst_leg_distances, lst_leg_latlngs, lst_leg_timestamps

    ############################################################################
    # PASSENGER GROUPING ALGORITHMS #

    def isInconvenient(self, new_pax, group, starting_kiosk, i, matrix):
        # Calculate time added from dropping off this passenger as "i" place in line
        added_triptime_for_existing_pax = 0

        if i == 0:
            added_triptime_for_existing_pax = matrix[str([starting_kiosk.getLatLng(), new_pax.dest_kiosk.getLatLng()])]['duration']
        elif i < len(group):
            added_triptime_for_existing_pax = matrix[str([group[i-1].dest_kiosk.getLatLng(), new_pax.dest_kiosk.getLatLng()])]['duration'] \
                                            + matrix[str([new_pax.dest_kiosk.getLatLng(),group[i].dest_kiosk.getLatLng()])]['duration'] \
                                            - matrix[str([group[i-1].dest_kiosk.getLatLng(),group[i].dest_kiosk.getLatLng()])]['duration']

        # Check if adding new_pax in index i inconveniences subsequent passengers
        for pax in group[i:]:
            if pax.total_triptime + added_triptime_for_existing_pax > pax.max_triptime:
                return True

        # Check if adding new_pax in index i inconveniences new_pax
        if i == 0:
            triptime_for_new_pax = new_pax.alone_triptime
        else:
            triptime_for_new_pax = group[i-1].total_triptime + matrix[str([group[i-1].dest_kiosk.getLatLng(),new_pax.dest_kiosk.getLatLng()])]['duration']

        if (triptime_for_new_pax > new_pax.max_triptime):
            return True

        # If code reaches this point, it means no one is inconvenienced by dropping off the passenger at "i" place in line

        # Adjust the total triptime for the subsequent passengers
        for pax in group[i:]:
            pax.total_triptime += added_triptime_for_existing_pax

        # Set the total triptime for the new passenger
        new_pax.total_triptime = triptime_for_new_pax

        return False

    def calculatePassengerGroupings(self, dict_existing_passenger_groups, new_passengers, starting_kiosk, MAX_CAPACITY):
        dict_passenger_groupings = dict_existing_passenger_groups
        for new_pax in new_passengers:
            try:
              for key, lst_groups in dict_passenger_groupings.items():
                for group in lst_groups:
                  if(len(group) < MAX_CAPACITY):
                    for i in range(len(group)+1):
                      if not self.isInconvenient(new_pax, group, starting_kiosk, i, self.kiosk_to_kiosk_route_matrix):
                        group.insert(i,new_pax)
                        updated_key = min(group, key=lambda pax: pax.odeparturetime).odeparturetime
                        assert updated_key == key, "New Passengers should have a greater odeparturetime than previous ones"
                        raise StopIteration

              new_group = [new_pax]
              key = min(new_group, key=lambda pax: pax.odeparturetime).odeparturetime
              if not key in dict_passenger_groupings:
                dict_passenger_groupings[key] = [new_group]
              else:
                dict_passenger_groupings[key].append(new_group)
              raise StopIteration
            except StopIteration:
              pass
        return dict(sorted(dict_passenger_groupings.items()))

    ############################################################################

    # Save trips used in the animation TripsLayer
    def saveAnimationTrips(self):
        lst_trips = []
        for vehicle in self.lst_all_vehicle_objects:
            lst_trips.extend(vehicle.getTrips())

        self.animation_trips = lst_trips

    # Save metrics calculated at EOD
    def saveEODMetrics(self):
        total_vehicle_distance_traveled_meters = 0
        total_empty_vehicle_distance_traveled_meters = 0
        lst_vehicle_distance_traveled = []
        dvo = []
        utilization_time = []
        for vehicle in self.lst_all_vehicle_objects:
            dvo.extend(vehicle.getDVO())
            total_vehicle_distance_traveled_meters += vehicle.getTotalDistanceTraveled()
            lst_vehicle_distance_traveled.append(vehicle.getTotalDistanceTraveled())
            total_empty_vehicle_distance_traveled_meters += vehicle.getTotalEmptyDistanceTraveled()
            utilization_time.append(vehicle.getTotalDurationTraveled() - vehicle.getTotalEmptyDurationTraveled())

        total_vehicle_distance_traveled_miles = total_vehicle_distance_traveled_meters*0.000621371192
        total_empty_vehicle_distance_traveled_miles = total_empty_vehicle_distance_traveled_meters * 0.000621371192

        self.EOD_metrics["total_vehicle_distance_traveled"] = total_vehicle_distance_traveled_miles
        self.EOD_metrics["total_empty_vehicle_distance_traveled"] = total_empty_vehicle_distance_traveled_miles
        self.EOD_metrics["lst_vehicle_distance_traveled"] = lst_vehicle_distance_traveled
        self.EOD_metrics["dvo"] = dvo
        self.EOD_metrics["avg_utilization_time"] = sum(utilization_time) / (len(utilization_time)*3600)

        person_alone_trip_length = []
        pax_waittime = []
        walk_to_okiosk_dist = []
        walk_to_dkiosk_dist = []
        pax_added_triptime = []
        for pax in self.lst_all_passenger_objects:
            if not pax.isMissed():
                person_alone_trip_length.append(pax.getAloneTripLength())
                pax_waittime.append(pax.getWaittime())
                walk_to_okiosk_dist.append(pax.getWalkToKioskDistance())
                walk_to_dkiosk_dist.append(pax.getWalkToDestKioskDistance())
                pax_added_triptime.append(pax.getAddedTriptime())

        self.EOD_metrics["person_alone_trip_length"] = person_alone_trip_length
        self.EOD_metrics["pax_waittime"] = pax_waittime
        self.EOD_metrics["avg_pax_waittime_minutes"] = sum(pax_waittime) / (len(pax_waittime) * 60)
        self.EOD_metrics["pax_added_triptime"] = pax_added_triptime
        self.EOD_metrics["avg_pax_added_triptime"] = sum(pax_added_triptime) / len(pax_added_triptime)
        self.EOD_metrics["walk_to_okiosk_dist"] = walk_to_okiosk_dist
        self.EOD_metrics["walk_to_dkiosk_dist"] = walk_to_dkiosk_dist

        # AVO is lower because the numerator is alone trip length instead of person miles traveled
        avo = sum(person_alone_trip_length) / total_vehicle_distance_traveled_meters
        self.EOD_metrics["avo"] = avo

        total_num_vehicles = len(self.lst_all_vehicle_objects)
        print("Total vehicle number:", total_num_vehicles)
        num_total_passengers = 0
        num_served_passengers = 0
        num_missed_passengers = 0
        for kiosk in self.lst_all_kiosk_objects:
            num_total_passengers += len(kiosk.lst_all_arriving_passengers)
            num_served_passengers += len(kiosk.lst_all_arriving_passengers)
            num_total_passengers += len(kiosk.lst_missed_passenger_objects)
            num_missed_passengers += len(kiosk.lst_missed_passenger_objects)
        print("Total passengers served:", num_served_passengers)
        print("Missed passengers:", num_missed_passengers)
        print("AVO:", avo)
        print("DVO:", sum(dvo)/len(dvo))
        print("Avg utilization time:",self.EOD_metrics["avg_utilization_time"])
        assert num_total_passengers == len(self.lst_all_passenger_objects), "Some passengers are unaccounted for"
        assert len(person_alone_trip_length) == num_served_passengers, "Some served passengers are unaccounted for"

        self.EOD_metrics["total_num_vehicles"] = total_num_vehicles
        self.EOD_metrics["num_total_passengers"] = num_total_passengers
        self.EOD_metrics["num_served_passengers"] = num_served_passengers
        self.EOD_metrics["num_missed_passengers"] = num_missed_passengers


    # Save metrics calculaged in current timestep
    def saveCurrentTimeframeMetrics(self, curr_time_in_sec):
        vehicles_moving = 0
        vehicles_with_pax_moving = 0
        empty_vehicles_moving = 0
        vehicles_not_moving = 0
        pax_moving = 0
        for vehicle in self.lst_all_vehicle_objects:
            if vehicle.isEnRoute():
                vehicles_moving += 1
                if len(vehicle.getPassengers()) > 0:
                    vehicles_with_pax_moving += 1
                    pax_moving += len(vehicle.getPassengers())
                else:
                    empty_vehicles_moving += 1
            else:
                vehicles_not_moving += 1

        pax_waiting = 0
        pax_arrived_running_total = 0
        pax_missed_running_total = 0
        for kiosk in self.lst_all_kiosk_objects:
            pax_waiting += len(kiosk.getPassengerObjects())
            pax_arrived_running_total += len(kiosk.getArrivedPassengers())
            pax_missed_running_total += len(kiosk.getMissedPassengers())
            new_kiosk_timeframe_entry = {
                "c": kiosk.getLngLatList(),
                "n": kiosk.getID(),
                "v": len(kiosk.getVehicles()),
                "p": len(kiosk.getPassengerObjects()),
                "g": kiosk.getNumPassengerGroupings()
            }
            if curr_time_in_sec in self.kiosk_timeframe_metrics:
                self.kiosk_timeframe_metrics[curr_time_in_sec].append(new_kiosk_timeframe_entry)
            else:
                self.kiosk_timeframe_metrics[curr_time_in_sec] = [new_kiosk_timeframe_entry]

        total_pax = pax_moving + pax_waiting

        assert vehicles_moving + vehicles_not_moving == len(self.lst_all_vehicle_objects), "Some vehicles are missing in the count"
        timeframe_metric_entry = {
            "vehicles_moving": vehicles_moving,
            "vehicles_with_pax_moving": vehicles_with_pax_moving,
            "empty_vehicles_moving": empty_vehicles_moving,
            "vehicles_not_moving": vehicles_not_moving,
            "total_pax": total_pax,
            "pax_moving": pax_moving,
            "pax_waiting": pax_waiting,
            "pax_served_running_total": pax_arrived_running_total,
            "pax_missed_running_total": pax_missed_running_total
        }
        self.timeframe_metrics[curr_time_in_sec] = timeframe_metric_entry


    ############################################################################

    def runSimulation(self):
        curr_time_in_sec = 0

        # It is possible to have more than 1 kiosk per pixel
        dict_kiosks_by_pixel = self.getDictKiosksByPixel()
        #print(dict_kiosks_by_pixel)

        # Create dictionary of "possible" trips
        # A "possible" trip is a trip with at least one passenger destination
        # such that no one's travel time increases by more than X% in duration
        # as opposed to traveling on their own
        # WORK IN PROGRESS

        # Keep iterating until all passengers have been served/missed
        while True:
            if len(self.lst_remaining_passenger_objects) == 0:
                arrived_pax = 0
                missed_pax = 0
                for kiosk in self.lst_all_kiosk_objects:
                    arrived_pax += len(kiosk.getArrivedPassengers())
                    missed_pax += len(kiosk.getMissedPassengers())
                if arrived_pax + missed_pax == len(self.lst_all_passenger_objects):
                    break

            print("Time: ", curr_time_in_sec)
            # Deal with the arriving passengers first then deal with the departing passengers #

            ####################################################################
            ### ARRIVING PASSENGERS SECTION ###

            # Iterate through all vehicles and update states of both vehicles and kiosks
            for vehicle in self.lst_all_vehicle_objects:
                if not vehicle.isEnRoute():
                    continue
                if vehicle.hasArrivedAtNewKiosk(curr_time_in_sec):
                    # Update vehicle kiosk to its next destination
                    new_kiosk = vehicle.updateKiosk()
                    #print("Vehicle arriving with ",
                          #[pax for pax in vehicle.lst_passengers if vehicle.kiosk == pax.dest_kiosk]," to ",vehicle.kiosk.name)
                    # Remove the last vehicle trip since it is completed
                    vehicle.removeTripLeg()
                    # Get the passengers that the vehicle is dropping off at this new kiosk
                    lst_dropped_off_passengers = vehicle.getDroppedOffPassengers()
                    # Remove dropped off passengers from the vehicle passenger list
                    vehicle.removePassengers(lst_dropped_off_passengers)
                    # Add dropped off passengers as arriving passengers to the new kiosk (used for tracking purposes)
                    new_kiosk.addArrivingPassengers(lst_dropped_off_passengers)
                    # Allow the vehicle to begin accepting trips again (no longer enroute)
                    vehicle.arrive()

                    # See if this is the last kiosk destination for vehicle since it will reset all its trip data and wait for a new trip assignment
                    if vehicle.isAtLastKiosk():
                        # print("At last kiosk")
                        # Reset the vehicle's trip data
                        vehicle.resetTrip()
                        # Since the trip ended, add the vehicle to list of vehicles currently at this kiosk
                        new_kiosk.addVehicle(vehicle)
                        # Remove vehicle from list of incoming vehicles so that the kiosk doesn't double-count this vehicle in its net vehicle balance
                        new_kiosk.removeIncomingVehicle(vehicle)
                    else: # If the vehicle still has more trips to go
                        # Depart the vehicle
                        vehicle.depart(curr_time_in_sec)



            ####################################################################
            ### DEPARTING PASSENGERS SECTION ###

            # Get all passengers that leave in this second
            return_lst_passengers_that_leave_by_time_x_in_sec = self.getPassengersThatLeaveByTimeXInSec(curr_time_in_sec)

            # Add passengers to their respective oKiosk
            for pax in return_lst_passengers_that_leave_by_time_x_in_sec:
                assert pax.getOXYPixelCoords() in dict_kiosks_by_pixel, "This person trip does not happen within the ODD"
                assert pax.getDXYPixelCoords() in dict_kiosks_by_pixel, "This person trip does not happen within the ODD"

                # Find all kiosks closest to the passengers origin
                # There might be multiple kiosks in each pixel
                lst_okiosks = dict_kiosks_by_pixel[pax.getOXYPixelCoords()]
                closest_okiosk = self.getClosestKioskToLatLng(lst_okiosks, pax.lat, pax.lng)

                # Save oKiosk in Passenger object memory
                pax.setOKiosk(closest_okiosk)

                # Add passenger to kiosk since they are currently waiting for pickup
                closest_okiosk.addDepartingPassenger(pax)
                # Remember to reset list of new departing passengers after each time step
                closest_okiosk.addNewDepartingPassenger(pax)

                # Find all kiosks closest to the passengers destination
                lst_dkiosks = dict_kiosks_by_pixel[pax.getDXYPixelCoords()]
                closest_dkiosk = self.getClosestKioskToLatLng(lst_dkiosks, pax.dest_lat, pax.dest_lng)

                # Save dKiosk in Passenger object memory
                pax.setDKiosk(closest_dkiosk)

                # Set the Passenger alone travel time (if they went straight to their kiosk)
                # and their max travel time (max additional time they are willing to spend traveling)
                pax.setTripInfo(self.kiosk_to_kiosk_route_matrix[str([pax.kiosk.getLatLng(), pax.dest_kiosk.getLatLng()])]['duration'],
                                self.kiosk_to_kiosk_route_matrix[str([pax.kiosk.getLatLng(), pax.dest_kiosk.getLatLng()])]['distance'])

            # Iterate through kiosks and assign waiting passengers to vehicles
            for kiosk in self.lst_all_kiosk_objects:
                # Get list of new departing passengers that showed up within the last time step
                lst_passengers_new_departing_at_kiosk = kiosk.getNewDepartingPassengerObjects()

                # Get dict of existing passenger groupings
                dict_existing_passenger_groups = kiosk.getPassengerGroupings()

                # Get groupings of passengers at each kiosks
                # Each group consists of passengers traveling to kiosks along a shared route
                # such that no one's travel time increases by more than X% in duration
                # in this carpool scenario as opposed to traveling directly to their destination (with no stops in between)
                sorted_dict_passenger_groups = self.calculatePassengerGroupings(dict_existing_passenger_groups,
                                                                           lst_passengers_new_departing_at_kiosk,
                                                                           kiosk,
                                                                           self.MAX_CAPACITY)

                # Kiosk should update its dict of passenger groupings (dict where keys are min passenger departure time and values are 2D arrays of passenger groups)
                kiosk.setPassengerGroupings(sorted_dict_passenger_groups)

                # Kiosk needs to have a 1:1 matching between vehicles and unique passenger groupings
                # The kiosk will send a request out to all kiosks for vehicles if it doesn't have
                # enough incoming and current vehicles to assign a vehicle to each passenger grouping
                kiosk.updateNetVehicleBalance(self.passenger_waittime_threshold)

                # Kiosk should check if any of its passenger groupings should be assigned a vehicle
                # There are two possible scenarios:
                # 1. Length of any passenger grouping equals the MAX_CAPACITY
                # 2. A passenger in any passenger grouping waits passenger_waittime_threshold time
                # Get the passenger groupings that are ready to leave
                lst_of_lsts_of_passenger_groupings_ready_to_leave = kiosk.getPassengerGroupsReadyToLeave(curr_time_in_sec, self.passenger_waittime_threshold, self.MAX_CAPACITY)

                # if (len(kiosk.lst_passenger_objects) != 0):
                #     print(kiosk.name)
                #     print("Passengers waiting at kiosk: ",kiosk.lst_passenger_objects)
                #     print("Passengers ready to leave: ",lst_of_lsts_of_passenger_groupings_ready_to_leave)

                #### MAGICALLY GENERATED VEHICLES ####
                # Generate new vehicles at this kiosk if we don't have enough vehicles for passenger groups that are ready to leave
                if len(self.lst_all_vehicle_objects) < self.MAX_VEHICLES:
                    num_vehicles_to_generate = len(lst_of_lsts_of_passenger_groupings_ready_to_leave) - len(kiosk.getVehicles())
                    for i in range(num_vehicles_to_generate):
                        if len(self.lst_all_vehicle_objects) >= self.MAX_VEHICLES:
                            break
                        new_vehicle = Vehicle(len(self.lst_all_vehicle_objects)+1, kiosk.lat, kiosk.lng, self.MAX_CAPACITY, kiosk)
                        kiosk.addVehicle(new_vehicle)
                        self.lst_all_vehicle_objects.append(new_vehicle)
                        #print("Vehicle created at ",kiosk.name)

                # if (len(kiosk.getVehicles()) != 0):
                #     print(kiosk.name," vehicles: ",kiosk.getVehicles())

                # Assign passenger groupings to vehicles and depart the passengers in vehicles
                #assert len(kiosk.getVehicles()) >= len(lst_of_lsts_of_passenger_groupings_ready_to_leave), "There must be a vehicle for every passenger group"
                for vehicle, passenger_grouping in list(zip(kiosk.getVehicles(), lst_of_lsts_of_passenger_groupings_ready_to_leave)):
                    passengers, curr_trip, num_passengers, trip_duration, trip_distance, lst_leg_durations, lst_leg_distances, lst_leg_latlngs, lst_leg_timestamps = self.create_vehicle_with_passengers_route(kiosk, passenger_grouping, self.kiosk_to_kiosk_route_matrix, curr_time_in_sec)
                    # Set the route of the vehicle
                    vehicle.addTripLegs(passengers, curr_trip, num_passengers, trip_duration, trip_distance, lst_leg_durations, lst_leg_distances, lst_leg_latlngs, lst_leg_timestamps, curr_time_in_sec)
                    # Depart vehicle
                    vehicle.depart(curr_time_in_sec)
                    #print("Vehicle departing with ", passenger_grouping)
                    #print()
                    # Remove passengers from kiosk since they left in the vehicle
                    kiosk.removeDepartingPassengers(passenger_grouping, curr_time_in_sec)
                    # Remove the vehicle from the kiosk
                    kiosk.removeVehicle(vehicle)

                    # Alert the last kiosk on its route that it will arrive there
                    final_kiosk_destination, arrival_time = vehicle.getFinalKioskDestination()
                    final_kiosk_destination.addIncomingVehicle(vehicle, arrival_time)


                # Check if any passengers waited more than passenger_waittime_threshold and make them leave
                num_missed_passengers = len(kiosk.removeMissedPassengers(curr_time_in_sec, self.passenger_waittime_threshold))
                #if (num_missed_passengers != 0):
                #    print(kiosk.name," ",num_missed_passengers," missd passenger(s)")
                # If there are any missed passengers, then the passenger groupings need to be updated
                if num_missed_passengers:
                    sorted_dict_passenger_groups = self.calculatePassengerGroupings({}, # Erase the existing passenger groupings
                                                                               kiosk.getPassengerObjects(), # Need to regroup all passengers currently at kiosk
                                                                               kiosk,
                                                                               self.MAX_CAPACITY)
                    # Overwrite the existing passenger groupings
                    kiosk.setPassengerGroupings(sorted_dict_passenger_groups)
                    # Update the number of vehicles that a kiosk still needs (might be zero since everyone left)
                    kiosk.updateNetVehicleBalance(self.passenger_waittime_threshold)


                # Reset the new departing passenger list
                kiosk.resetNewDepartingPassengerObjects()


            ####################################################################
            # EMPTY VEHICLE REPOSITIONING #

            lst_kiosks_in_need_of_vehicle = []
            lst_kiosks_with_excess_vehicles = []
            for kiosk in self.lst_all_kiosk_objects:
                # Find all kiosks in need of a vehicle
                if kiosk.getNetVehicleBalance() < 0:
                    lst_kiosks_in_need_of_vehicle.append(kiosk)
                # Find all kiosks with excess vehicles that are not currently needed by kiosk
                if kiosk.getNetVehicleBalance() > 0:
                    lst_kiosks_with_excess_vehicles.append(kiosk)

            #print("######################################")
            #print(lst_kiosks_in_need_of_vehicle, lst_kiosks_with_excess_vehicles)
            # Match kiosks in need of a vehicle to kiosks with excess vehicles, based on distance
            for kiosk_in_need in lst_kiosks_in_need_of_vehicle:
                # Edge case: If lst_kiosks_with_excess_vehicles is empty, just break the for loop
                if len(lst_kiosks_with_excess_vehicles) == 0:
                    break

                # Send all the vehicles that this kiosk needs
                # Keep giving this needy kiosk vehicles until its net vehicle balance becomes 0
                while kiosk_in_need.getNetVehicleBalance() < 0:
                    if len(lst_kiosks_with_excess_vehicles) == 0:
                        break
                    closest_kiosk_with_excess_vehicles = self.getClosestKioskToKiosk(lst_kiosks_with_excess_vehicles, kiosk_in_need, self.kiosk_to_kiosk_route_matrix)
                    #print(closest_kiosk_with_excess_vehicles)
                    # Preplan route empty vehicle to kiosk in need
                    passengers, curr_trip, num_passengers, trip_duration, trip_distance, lst_leg_durations, lst_leg_distances, lst_leg_latlngs, lst_leg_timestamps = self.create_empty_vehicle_route(
                        closest_kiosk_with_excess_vehicles, kiosk_in_need, self.kiosk_to_kiosk_route_matrix,
                        curr_time_in_sec)
                    assert len(passengers) == 0, "There should be no passengers in this empty trip"
                    kiosk_in_need, arrival_time = curr_trip[-1], curr_time_in_sec + trip_duration  # Get arrival time of vehicle to kiosk in need
                    if (arrival_time > min(
                            kiosk_in_need.getPassengerGroupings().keys()) + self.passenger_waittime_threshold):
                        break
                    # Start going through the vehicles of the closest kiosk
                    for vehicle in closest_kiosk_with_excess_vehicles.getVehicles(): # It's possible for getVehicles() to return empty if there are incoming vehicles but no vehicles currently stationed at the kiosk, which makes the net_vehicle_balance for this kiosk positive
                        # Two cases will case this loop to end:
                        # 1. The closest kiosk might run out of vehicles (currently stationed at this kiosk), so the next closest kiosk must be found
                        # 2. The kiosk in need no longer needs any more vehicles
                        if closest_kiosk_with_excess_vehicles.getNetVehicleBalance() == 0:
                            break
                        elif kiosk_in_need.getNetVehicleBalance() == 0:
                            break
                        # Send vehicles from excess kiosk to kiosk in need
                        else:
                            vehicle.addTripLegs(passengers, curr_trip, num_passengers, trip_duration, trip_distance,
                                                    lst_leg_durations, lst_leg_distances, lst_leg_latlngs,
                                                    lst_leg_timestamps,
                                                    curr_time_in_sec)  # Send empty vehicle to kiosk in need
                            vehicle.depart(curr_time_in_sec) # Depart vehicle
                            closest_kiosk_with_excess_vehicles.removeVehicle(vehicle) # Remove vehicle from current vehicles stationed at closest kiosk
                            closest_kiosk_with_excess_vehicles.updateNetVehicleBalance(self.passenger_waittime_threshold) # Update the net vehicle balance of closest kiosk - THIS MIGHT UPDATE TWICE
                            kiosk_in_need.addIncomingVehicle(vehicle, arrival_time) # Update list of incoming vehicles to kiosk in need
                            kiosk_in_need.updateNetVehicleBalance(self.passenger_waittime_threshold) # Update kiosk in need net vehicle balance
                    lst_kiosks_with_excess_vehicles.remove(closest_kiosk_with_excess_vehicles)

            # Save current timeframe metrics
            self.saveCurrentTimeframeMetrics(curr_time_in_sec)

            # Iterate time by time step
            curr_time_in_sec += self.TIME_STEP

        # Save EOD metrics
        self.saveEODMetrics()

        # Save trips used in animation
        self.saveAnimationTrips()

    # Get EOD Metrics
    def getEODMetrics(self):
        return self.EOD_metrics

    # Get animation trips
    def getAnimationTrips(self):
        return self.animation_trips

    # Get timeframe metrics
    def getTimeframeMetrics(self):
        return self.timeframe_metrics

    def getKioskTimeframeMetrics(self):
        return self.kiosk_timeframe_metrics
