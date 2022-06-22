from ast import literal_eval
from sklearn.cluster import KMeans
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
sns.set()


class CreateBuckets:
    def __init__(self, CITY_NAME):
        self.city = CITY_NAME

    def CreateBuckets(self):

        array = np.array(literal_eval(
            open("./static/Honolulu/depot_locations.txt").read()))
        kmeans = KMeans(3)
        kmeans.fit(array)
        print(kmeans.fit_predict(array))
        wcss = []

        for i in range(1, 7):
        kmeans = KMeans(i)
        kmeans.fit(x)
        wcss_iter = kmeans.inertia_
        wcss.append(wcss_iter)

        number_clusters = range(1, 7)
        plt.plot(number_clusters, wcss)
        plt.title('The Elbow title')
        plt.xlabel('Number of clusters')
        plt.ylabel('WCSS')
        print(array[0])


def main():
    CITY_NAME = "Honolulu"
    bucks = CreateBuckets("Honolulu")
    bucks.CreateBuckets()


if __name__ == "__main__":
    main()
