import math

def find_nearest_vertex(mesh_obj, point):

    vertices = mesh_obj.data.vertices

    closest_index = 0
    closest_distance = math.inf

    for v in vertices:

        world_pos = mesh_obj.matrix_world @ v.co

        dist = (world_pos - point).length

        if dist < closest_distance:
            closest_distance = dist
            closest_index = v.index

    return closest_index