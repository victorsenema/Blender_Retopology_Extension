from collections import deque

def bfs_distances(start_vertex):

    distances = {}

    queue = deque()

    queue.append(start_vertex)

    distances[start_vertex.index] = 0

    while queue:

        current = queue.popleft()

        current_distance = distances[current.index]

        for edge in current.link_edges:

            other = edge.other_vert(current)

            if other.index not in distances:

                distances[other.index] = (
                    current_distance + 1
                )

                queue.append(other)

    return distances