class VertexGroups:

    #
    # OBS.: o nome da classe/arquivo ficou de uma versão anterior,
    # em que cada Critical Point exigia um Vertex Group nomeado
    # (ex.: "VG_Chin") pra definir sua "ilha" de influência na
    # malha. Isso foi removido: agora o alcance de cada ponto é
    # calculado por distância geodésica (ver geodesic.py/weights.py)
    # sobre a malha inteira, sem depender de Vertex Groups.
    #
    # A única responsabilidade que sobrou aqui é achar o vértice
    # da malha mais próximo de cada Empty (o "seed" de onde a busca
    # de distância geodésica começa). Renomear pra algo como
    # SeedVertices fica de cleanup.
    #

    def __init__(self, template, points=None):

        self.template = template

        #
        # Por padrão opera sobre os critical points de estrutura,
        # mas aceita qualquer lista de CriticalPoint (ex.: os
        # Refinement Points), pra reaproveitar a mesma lógica.
        #

        self.points = (
            points
            if points is not None
            else template.critical_points
        )

    def assign(self):

        for critical_point in self.points:

            self.find_seed_vertex(
                critical_point
            )

    def find_seed_vertex(self, critical_point):

        from ...blender_utils import is_valid

        if not is_valid(critical_point.empty):

            critical_point.is_valid = False

            print(
                f"[ERROR] {critical_point.name}: referência ao "
                f"Empty foi perdida (provavelmente um Undo entre "
                f"'Apply Mesh' e esta etapa). Rode 'Apply Mesh' "
                f"de novo antes de continuar. Pulando este ponto."
            )

            return

        mesh = self.template.mesh

        empty_position = (
            critical_point.empty.matrix_world.translation
        )

        nearest_vertex = None

        nearest_distance = float("inf")

        #
        # Busca em TODA a malha, não mais só dentro
        # de um Vertex Group
        #

        for vertex in mesh.data.vertices:

            vertex_position = (
                mesh.matrix_world @ vertex.co
            )

            distance = (
                vertex_position -
                empty_position
            ).length

            if distance < nearest_distance:

                nearest_distance = distance

                nearest_vertex = vertex.index

        critical_point.seed_vertex = nearest_vertex

        critical_point.is_valid = nearest_vertex is not None

        print(
            f"{critical_point.name} Seed Vertex: {nearest_vertex}"
        )
