import numpy as np
from projection import project_point_to_triangle
from alpha_shape import alpha_shape_border
from collections import namedtuple

Node = namedtuple("Node", ("center", "radius", "inside_node", "outside_node"))
Leaf = namedtuple("Leaf", ("bucket"))

class PerturbProjTree:
    def __init__(self, x, alpha_std = 0.0, thickness = 0.0):
        self.thickness = thickness

        # construct the bounding triangles of the points
        border_points, border_tri = alpha_shape_border(x, alpha_std = alpha_std)
        triangles = []
        tri_center = []
        tri_radius = []

        for tri in border_tri:
            # get the minimum bounding sphere of each triangle
            tri = border_points[tri]
            center, radius = bounding_sphere(tri)
            triangles.append(tri)
            tri_center.append(center)
            tri_radius.append(radius + self.thickness)

        triangles = np.array(triangles)
        tri_center = np.vstack(tri_center)
        tri_radius = np.array(tri_radius)

        self.root = self.build(triangles, tri_center, tri_radius)

    def build(self, curr_triangles, curr_tri_center, curr_tri_radius):
        if len(curr_triangles) == 0:
            return None

        if len(curr_triangles) == 1:
            return Leaf(curr_triangles)

        # pick random point to partition with
        partition_center = curr_tri_center[np.random.randint(len(curr_tri_center))]

        # get distances from each triangle's bounding circle to the partition point
        distances_center = np.linalg.norm(curr_tri_center - partition_center[np.newaxis, :], axis = 1)
        # get the distance from partition point to farthest point of each bounding circle
        distances = distances_center + curr_tri_radius

        # pick the middle point to for the partition radius
        mid = len(distances) // 2
        # sort by negative distances so all bounding spheres with the same distance
        # as the picked mid distance will be to the right in the partition array
        partition = np.argpartition(-distances, mid)
        partition_radius = distances[partition[mid]]

        # bounding spheres that are completely within the partition sphere are counted as inside
        # bounding spheres that are completely outside the partition sphere are counted as outside
        # bounding spheres that straddle the partiton sphere are counted as both inside and outside
        # if a bounding sphere is tangent to the partition sphere, then it is counted as either
        # inside, or both inside and outside, depending on the position of the bounding sphere

        # if the distance from the partition point to the farthest point in a boundary sphere is less
        # than or equal to the radius of the partition sphere, then the bounding sphere is definitely inside
        # if the aforementioned distance is greater than the partition radius, then the bounding sphere may be
        # either inside, or both inside and outside, and distances must be checked to find the truth
        inside_idx = partition[mid:]
        outside_idx = partition[:mid]
        both_inside_outside = np.nonzero(distances_center[outside_idx] - curr_tri_radius[outside_idx] <= partition_radius)[0]
        inside_idx = np.concatenate((inside_idx, both_inside_outside))

        if len(inside_idx) == len(curr_triangles):
            # if the attempt to partition bounding spheres fails, then a bucket that stores a list of triangles is built
            return Leaf(curr_triangles)

        inside_node = self.build(curr_triangles[inside_idx], curr_tri_center[inside_idx], curr_tri_radius[inside_idx])
        outside_node = self.build(curr_triangles[outside_idx], curr_tri_center[outside_idx], curr_tri_radius[outside_idx])

        return Node(partition_center, partition_radius, inside_node, outside_node)

    def project(self, x_perturb, perturb):
        distances = np.linalg.norm(perturb, axis = 1)
        x_proj = []

        for point, dist in zip(x_perturb, distances):
            nearest_point, nearest_dist = self.query(point, dist, self.root)
            x_proj.append(nearest_point)

        return np.vstack(x_proj)

    def query(self, query_point, query_radius, curr_node):
        # project a point onto its nearest triangles and find the nearest projection location
        nearest = (None, float("inf"))

        if type(curr_node) == Leaf:
            for tri in curr_node.bucket:
                # go through each point in the bucket and project it
                proj_point = project_point_to_triangle(query_point, tri, thickness = self.thickness)
                proj_dist = np.linalg.norm(query_point - proj_point)

                if proj_dist < nearest[1]:
                    nearest = (proj_point, proj_dist)
        elif type(curr_node) == Node:
            dist = np.linalg.norm(query_point - curr_node.center)

            if dist > curr_node.radius + query_radius: # query and partition spheres are completely not overlapping
                nearest = self.query(query_point, query_radius, curr_node.outside_node)
            elif dist <= curr_node.radius - query_radius: # query and partition spheres are completely overlapping
                nearest = self.query(query_point, query_radius, curr_node.inside_node)
            else:
                # must examine both subtrees as the border of the query sphere overlaps the border of the partition sphere
                nearest_inside = self.query(query_point, query_radius, curr_node.inside_node)
                nearest_outside = self.query(query_point, query_radius, curr_node.outside_node)

                if nearest_inside[1] < nearest_outside[1]:
                    nearest = nearest_inside
                else:
                    nearest = nearest_outside

        return nearest

def bounding_sphere(tri):
    # minimum bounding sphere of 3D triangle
    A, B, C = tri
    A_to_B = B - A
    A_to_C = C - A
    B_to_C = C - B

    if np.dot(A_to_B, A_to_C) <= 0 or np.dot(A_to_B, B_to_C) <= 0 or np.dot(A_to_C, B_to_C) <= 0:
        # right or obtuse triangle
        edges = np.array([np.linalg.norm(A_to_B), np.linalg.norm(A_to_C), np.linalg.norm(B_to_C)])
        idx = np.argmax(edges)
        radius = edges[idx]
        center = [np.mean(np.array([A, B]), axis = 0), np.mean(np.array([A, C]), axis = 0), np.mean(np.array([B, C]), axis = 0)][idx]
    else:
        # acute triangle
        normal = np.cross(A_to_B, A_to_C)
        # get the center of the bounding sphere
        center = A + (np.sum(A_to_B ** 2) * np.cross(A_to_C, normal) + np.sum(A_to_C ** 2) * np.cross(normal, A_to_B)) / (np.sum(normal ** 2) * 2.0)
        # get the radius of the bounding sphere
        radius = np.max(np.linalg.norm(tri - center[np.newaxis, :], axis = 1))

    return center, radius
