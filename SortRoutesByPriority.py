import numpy as np
import sys
# Python program for Kruskal's algorithm to find
# Minimum Spanning Tree of a given connected,
# undirected and weighted graph

# This code is contributed by Neelam Yadav

# Class to represent a graph
class Graph:

    def __init__(self, vertices):
        self.V = vertices  # No. of vertices
        self.graph = []  # default dictionary
        # to store graph
        self.arr = []

    # function to add an edge to graph
    def addEdge(self, u, v, w):
        self.graph.append([u, v, w])

    def removeMostRecentEdge(self):
        self.graph = self.graph[:-1]

    # A utility function to find set of an element i
    # (uses path compression technique)
    def find(self, parent, i):
        if parent[i] == i:
            return i
        return self.find(parent, parent[i])

    # A function that does union of two sets of x and y
    # (uses union by rank)
    def union(self, parent, rank, x, y):
        xroot = self.find(parent, x)
        yroot = self.find(parent, y)

        # Attach smaller rank tree under root of
        # high rank tree (Union by Rank)
        if rank[xroot] < rank[yroot]:
            parent[xroot] = yroot
        elif rank[xroot] > rank[yroot]:
            parent[yroot] = xroot

        # If ranks are same, then make one as root
        # and increment its rank by one
        else:
            parent[yroot] = xroot
            rank[xroot] += 1

    # The main function to construct MST using Kruskal's
        # algorithm
    def KruskalMST(self):

        result = []  # This will store the resultant MST

        # An index variable, used for sorted edges
        i = 0

        # An index variable, used for result[]
        e = 0

        # Step 1:  Sort all the edges in
        # non-decreasing order of their
        # weight.  If we are not allowed to change the
        # given graph, we can create a copy of graph
        self.graph = sorted(self.graph,
                            key=lambda item: item[2])

        parent = []
        rank = []

        # Create V subsets with single elements
        for node in range(self.V):
            parent.append(node)
            rank.append(0)

        # Number of edges to be taken is equal to V-1
        while e < self.V - 1:

            # Step 2: Pick the smallest edge and increment
            # the index for next iteration
            u, v, w = self.graph[i]
            i = i + 1
            x = self.find(parent, u)
            y = self.find(parent, v)

            # If including this edge doesn't
            #  cause cycle, include it in result
            #  and increment the indexof result
            # for next edge
            if x != y:
                e = e + 1
                result.append('{};{}'.format(u, v))
                self.union(parent, rank, x, y)
            # Else discard the edge
        return result

    # Floyd Warshall Algorithm in python
    def createMatrix(self):
        arr = np.zeros((self.V, self.V))
        for i in range(len(arr)):
            for j in range(len(arr)):
                if not i is j:
                    arr[i][j] = sys.maxsize
        for u, v, w in self.graph:
            arr[u][v] = w
        self.arr = arr

    def floyd_warshall(self):
        self.createMatrix()
        #print("BEFORE SOLVING:")
        #self.printSolution(self.arr)
        distance = list(map(lambda i: list(map(lambda j: j, i)), self.arr))

        # Adding vertices individually
        for k in range(self.V):
            for i in range(self.V):
                for j in range(self.V):
                    distance[i][j] = min(distance[i][j], distance[i][k] + distance[k][j])
        #print("UNOPTIMIZED SOLVE:")
        #self.printSolution(distance)
        return distance

    def printSolution(self, dist):
        print ("Following matrix shows the shortest distances between every pair of vertices")
        for i in range(self.V):
            for j in range(self.V):
                if(dist[i][j] == sys.maxsize):
                    print ("%7s" % ("INF"),end=" ")
                else:
                    print ("%7d" % (dist[i][j]),end=' ')
                if j == self.V-1:
                    print ()


    def getAllSortedRoutes(self, route_metas):
        remaining_route_metas = route_metas.copy()
        temp_graph = Graph(self.V)
        priority = 0
        keys_for_minimum_spanning_tree = self.KruskalMST()
        if len(keys_for_minimum_spanning_tree) == 0:
            return {}
        assert(self.V-1 == len(keys_for_minimum_spanning_tree))
        for key in keys_for_minimum_spanning_tree:
            route_metas[key]["duration_matrix_minutes"] = None
            route_metas[key]["duration_matrix_multiple"] = None
            route_metas[key]["priority"] = priority
            remaining_route_metas.pop(key)
            idx1, idx2 = [int(elem) for elem in key.split(';')]
            temp_graph.addEdge(idx1, idx2, route_metas[key]["duration"])
            temp_graph.addEdge(idx2, idx1, route_metas[key]["duration"])
            priority += 1

        #STARTING MINIMUM SPANNING TREE DISTANCE MATRIX
        mst_distance = temp_graph.floyd_warshall()
        #print("MST")
        #self.printSolution(mst_distance)
        route_metas[key]["duration_matrix_minutes"] = np.around(mst_distance).tolist()

        best_distance_matrix = mst_distance
        while len(remaining_route_metas) > 0:
            best_route_to_add_next_key = None
            min_sum_distance = sys.maxsize*sys.maxsize
            best_distance_matrix = None
            for key, value in remaining_route_metas.items():
                idx1, idx2 = [int(elem) for elem in key.split(';')]
                temp_graph.addEdge(idx1, idx2, route_metas[key]["duration"])
                temp_graph.addEdge(idx2, idx1, route_metas[key]["duration"])
                distance = temp_graph.floyd_warshall()
                if np.sum(distance) < min_sum_distance:
                    best_route_to_add_next_key = key
                    min_sum_distance = np.sum(distance)
                    best_distance_matrix = distance
                temp_graph.removeMostRecentEdge()
                temp_graph.removeMostRecentEdge()
            idx1, idx2 = [int(elem) for elem in best_route_to_add_next_key.split(';')]
            temp_graph.addEdge(idx1, idx2, route_metas[best_route_to_add_next_key]["duration"])
            temp_graph.addEdge(idx2, idx1, route_metas[best_route_to_add_next_key]["duration"])
            route_metas[best_route_to_add_next_key]["priority"] = priority
            route_metas[best_route_to_add_next_key]["duration_matrix_minutes"] = np.around(best_distance_matrix).tolist()
            remaining_route_metas.pop(best_route_to_add_next_key)
            priority += 1
            #self.printSolution(best_distance_matrix)
            #print("SUM", np.sum(best_distance_matrix))


        # Go back and populate "duration_matrix_multiple" after knowing shortest path between vertices
        for key in route_metas:
            if not route_metas[key]["duration_matrix_minutes"] is None:
                route_metas[key]["duration_matrix_multiple"] = np.around(np.nan_to_num(np.array(route_metas[key]["duration_matrix_minutes"])/np.array(best_distance_matrix)), decimals=2).tolist()
        return route_metas

# Driver code
# g = Graph(3)
# g.addEdge(0, 1, 377.3)
# g.addEdge(0, 2, 559.4)
# g.addEdge(1, 2, 213.5)
# g.KruskalMST()
# g.floyd_warshall()
#
# # Function call
