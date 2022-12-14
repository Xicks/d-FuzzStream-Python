from fmic import FMiC
from math import sqrt


class DFuzzStreamSummarizer:

    def __init__(self, min_fmics=5, max_fmics=100, merge_threshold=1.0, radius_factor=1.0, m=2.0):
        self.min_fmics = min_fmics
        self.max_fmics = max_fmics
        self.merge_threshold = merge_threshold
        self.radius_factor = radius_factor
        self.m = m
        self.__fmics = []

    def summarize(self, values, timestamp):
        if len(self.__fmics) < self.min_fmics:
            self.__fmics.append(FMiC(values, timestamp))
            return
        
        distance_from_fmics = [self.__euclidean_distance(fmic.center, values) for fmic in self.__fmics]
        is_outlier = True

        for idx, fmic in enumerate(self.__fmics):
            if fmic.radius == 0.0:
                # Minimum distance from another FMiC
                radius = min([
                    self.__euclidean_distance(fmic.center, another_fmic.center)
                    for another_idx, another_fmic in enumerate(self.__fmics)
                    if another_idx != idx
                ])
            else:
                radius = fmic.radius * self.radius_factor
            
            if distance_from_fmics[idx] <= radius:
                is_outlier = False
                fmic.timestamp = timestamp
        
        if is_outlier:
            if len(self.__fmics) >= self.max_fmics:
                oldest = min(self.__fmics, key=lambda f: f.timestamp)
                self.__fmics.remove(oldest)
            self.__fmics.append(FMiC(values, timestamp))
        else:
            memberships = self.__memberships(distance_from_fmics)
            for idx, fmic in enumerate(self.__fmics):
                fmic.assign(values, memberships[idx], distance_from_fmics[idx])

        self.__fmics = self.__merge()

    def summary(self):
        return self.__fmics.copy()

    def __merge(self):
        fmics_to_merge = []

        for i in range(0, len(self.__fmics) - 1):
            for j in range(i + 1, len(self.__fmics)):
                dissimilarity = self.__euclidean_distance(self.__fmics[i].center, self.__fmics[j].center)
                sum_of_radius = self.__fmics[i].radius + self.__fmics[j].radius

                if dissimilarity != 0:
                    similarity = sum_of_radius / dissimilarity
                else:
                    # Highest value possible
                    similarity = 1.7976931348623157e+308

                if similarity >= self.merge_threshold:
                    fmics_to_merge.append([i, j, similarity])

        # Sort by most similar
        fmics_to_merge.sort(reverse=True, key=lambda k: k[2])
        merged_fmics_idx = []
        merged_fmics = []

        for (i, j, _) in fmics_to_merge:
            if i not in merged_fmics_idx and j not in merged_fmics_idx:
                merged_fmics.append(FMiC.merge(self.__fmics[i], self.__fmics[j]))
                merged_fmics_idx.append(i)
                merged_fmics_idx.append(j)

        merged_fmics_idx.sort(reverse=True)
        for idx in merged_fmics_idx:
            self.__fmics.pop(idx)
        
        return self.__fmics + merged_fmics

    def __euclidean_distance(self, value_a, value_b):
        sum_of_distances = 0
        for idx, value in enumerate(value_a):
            sum_of_distances += pow(value - value_b[idx], 2)
        return sqrt(sum_of_distances)

    def __memberships(self, distances):
        memberships = []
        for distance_j in distances:
            # To avoid division by 0
            sum_of_distances = 2.2250738585072014e-308
            for distance_k in distances:
                if distance_k != 0:
                    sum_of_distances += pow((distance_j / distance_k), 2. / (self.m - 1.))
            memberships.append(1.0 / sum_of_distances)
        return memberships
