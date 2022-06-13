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

        print(result)
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
        distance = list(map(lambda i: list(map(lambda j: j, i)), self.arr))

        # Adding vertices individually
        for k in range(self.V):
            for i in range(self.V):
                for j in range(self.V):
                    distance[i][j] = min(distance[i][j], distance[i][k] + distance[k][j])
        np.sum(distance)

    def getAllSortedRoutes(self):
        keys_for_minimum_spanning_tree = self.KruskalMST()


        for key, value in route_metas.items():
            print(key, value)
        return route_metas

print(sys.maxsize)
# Driver code
g = Graph(3)
g.addEdge(0, 1, 377.3)
g.addEdge(0, 2, 559.4)
g.addEdge(1, 2, 213.5)
g.floyd_warshall()
#
# # Function call
# g.KruskalMST()
