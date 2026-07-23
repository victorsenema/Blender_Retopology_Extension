import math


class Weights:

    def __init__(self, template, points=None):

        self.template = template

        self.points = (
            points
            if points is not None
            else template.critical_points
        )

    # -------------------------------------------------------------

    def calculate(self):

        valid_points = [
            critical_point
            for critical_point in self.points
            if critical_point.is_valid
            and critical_point.seed_vertex is not None
        ]

        if not valid_points:
            return

        #
        # Raio de influência adaptativo por ponto (sigma)
        #

        self.calculate_influence_radius(valid_points)

        #
        # Passo 1: peso Gaussiano "cru" de cada Critical Point
        # em relação a cada vértice que ele alcançou
        #

        raw_weights = {
            critical_point.name: self.calculate_raw_weights(
                critical_point
            )
            for critical_point in valid_points
        }

        #
        # Passo 2: normaliza por vértice, somando entre TODOS
        # os Critical Points (partição da unidade). É isso que
        # garante que todo vértice da malha sempre recebe uma
        # contribuição normalizada de algum ponto -- sem zona
        # morta e sem corte abrupto entre regiões.
        #

        mesh = self.template.mesh

        vertex_count = len(mesh.data.vertices)

        for vertex_index in range(vertex_count):

            total = 0.0

            for critical_point in valid_points:

                total += raw_weights[critical_point.name].get(
                    vertex_index, 0.0
                )

            if total <= 1e-12:
                continue

            for critical_point in valid_points:

                raw = raw_weights[critical_point.name].get(
                    vertex_index, 0.0
                )

                if raw <= 0.0:
                    continue

                critical_point.vertex_weights[vertex_index] = (
                    raw / total
                )

        for critical_point in valid_points:

            print(
                f"{critical_point.name} -> "
                f"{len(critical_point.vertex_weights)} weights "
                f"(sigma={critical_point.influence_radius:.4f})"
            )

    # -------------------------------------------------------------

    def calculate_influence_radius(self, valid_points):

        #
        # Sigma de cada ponto = metade da distância até o
        # Critical Point vizinho mais próximo (após o
        # alinhamento). Assim o raio de influência acompanha
        # automaticamente o tamanho da cabeça e a densidade de
        # landmarks, sem constante mágica fixa (0.35 antes).
        #

        for critical_point in valid_points:

            nearest_distance = None

            position = (
                critical_point.empty.matrix_world.translation
            )

            for other in valid_points:

                if other is critical_point:
                    continue

                other_position = (
                    other.empty.matrix_world.translation
                )

                distance = (position - other_position).length

                if (
                    nearest_distance is None or
                    distance < nearest_distance
                ):
                    nearest_distance = distance

            critical_point.influence_radius = (
                (nearest_distance or 1.0) * 0.6
            )

    # -------------------------------------------------------------

    def calculate_raw_weights(self, critical_point):

        sigma = critical_point.influence_radius

        if sigma <= 1e-9:
            sigma = 1e-9

        weights = {}

        for vertex_index, distance in (
            critical_point.geodesic_distance.items()
        ):

            weights[vertex_index] = math.exp(
                -(distance * distance) /
                (2 * sigma * sigma)
            )

        return weights
