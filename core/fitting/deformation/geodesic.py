import heapq
import bmesh


class Geodesic:

    def __init__(self, template, points=None):

        self.template = template

        self.points = (
            points
            if points is not None
            else template.critical_points
        )

    # -------------------------------------------------------------

    def calculate(self):

        mesh = self.template.mesh

        bm = bmesh.new()

        bm.from_mesh(mesh.data)

        bm.verts.ensure_lookup_table()

        for critical_point in self.points:

            if not critical_point.is_valid:
                continue

            if critical_point.seed_vertex is None:
                continue

            critical_point.geodesic_distance.clear()

            self.calculate_distances(
                bm,
                critical_point
            )

        bm.free()

    # -------------------------------------------------------------

    def calculate_distances(
        self,
        bm,
        critical_point
    ):

        #
        # Dijkstra sobre a malha INTEIRA (sem restrição de
        # "ilha"/Vertex Group), usando o comprimento real de
        # cada aresta como peso -- isso aproxima a distância
        # geodésica de verdade, em vez de contar saltos de
        # aresta (que dependia da densidade de vértices).
        #

        distances = {
            critical_point.seed_vertex: 0.0
        }

        visited = set()

        heap = [(0.0, critical_point.seed_vertex)]

        while heap:

            current_distance, vertex_index = heapq.heappop(heap)

            if vertex_index in visited:
                continue

            visited.add(vertex_index)

            vertex = bm.verts[vertex_index]

            for edge in vertex.link_edges:

                neighbour = edge.other_vert(vertex)

                edge_length = edge.calc_length()

                new_distance = current_distance + edge_length

                if (
                    neighbour.index not in distances or
                    new_distance < distances[neighbour.index]
                ):

                    distances[neighbour.index] = new_distance

                    heapq.heappush(
                        heap,
                        (new_distance, neighbour.index)
                    )

        critical_point.geodesic_distance = distances

        print(
            f"{critical_point.name} -> "
            f"{len(critical_point.geodesic_distance)} distances "
            f"(Dijkstra, malha inteira)"
        )
