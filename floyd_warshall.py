# Python3 program to find the shortest
# path between any two nodes using
# Floyd Warshall Algorithm.

# Initializing the distance and
# Next array
def initialise(V, dis, Next, graph, INF):
	for i in range(V):
		for j in range(V):
			dis[i][j] = graph[i][j]

			# No edge between node
			# i and j
			if (graph[i][j] == INF):
				Next[i][j] = -1
			else:
				Next[i][j] = j

# Function construct the shortest
# path between u and v
def constructPath(u, v, graph, Next):
	# If there's no path between
	# node u and v, simply return
	# an empty array
	if (Next[u][v] == -1):
		return {}

	# Storing the path in a vector
	path = [u]
	while (u != v):
		u = Next[u][v]
		path.append(u)

	return path

# Standard Floyd Warshall Algorithm
# with little modification Now if we find
# that dis[i][j] > dis[i][k] + dis[k][j]
# then we modify next[i][j] = next[i][k]
def floydWarshall(V, Next, dis, INF):
	for k in range(V):
		for i in range(V):
			for j in range(V):

				# We cannot travel through
				# edge that doesn't exist
				if (dis[i][k] == INF or dis[k][j] == INF):
					continue
				if (dis[i][j] > dis[i][k] + dis[k][j]):
					dis[i][j] = dis[i][k] + dis[k][j]
					Next[i][j] = Next[i][k]

# Print the shortest path
def printPath(path):
    n = len(path)
    if n == 0:
        print("No Path exists")
        return -1
    for i in range(n - 1):
        print(path[i], end=" -> ")
    print(path[n - 1])


# This code is contributed by mohit kumar 29
