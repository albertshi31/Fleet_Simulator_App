class Depot:
    def __init__(self, name, lat, lon):
        self.name = name
        self.lat = float(lat)
        self.lon = float(lon)
        self.lst_vehicles = []
        self.lst_incoming_vehicles = []
        self.lst_passengers = []
        self.num_passengers = 0
        self.max_passengers = 0

    def __str__(self):
        return "Name: {0}\nLocation: ({1}, {2})".format(self.name, self.lat, self.lon)

    def addVehicle(self, aVehicle):
        self.lst_vehicles.append(aVehicle)

    def removeVehicle(self, aVehicle):
        self.lst_vehicles.remove(aVehicle)

    def addPassenger(self, aPassenger):
        self.lst_passengers.append(aPassenger)

    def removePassenger(self, aPassenger):
        self.lst_passengers.remove(aPassenger)

    def getAnimationDetails(self):
        result = {'depot_idx': id(self), 'num_pax': len(self.lst_passengers)}
        return result

    def reset(self):
        self.lst_vehicles = []
        self.lst_passengers = []
        self.num_passengers = 0
        self.max_passengers = 0
