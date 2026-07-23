from mathutils import Vector


class CriticalPoint:

    def __init__(self, empty):

        self.name = empty.name

        self.empty = empty

        self.template_position = empty.matrix_world.translation.copy()

        self.target_position = empty.matrix_world.translation.copy()

        self.offset = Vector((0.0, 0.0, 0.0))

        #
        # Vértice inicial da BFS/Dijkstra
        #

        self.seed_vertex = None

        #
        # Raio de influência (sigma) usado no falloff Gaussiano,
        # calculado a partir da distância ao Critical Point
        # vizinho mais próximo (ver weights.py)
        #

        self.influence_radius = 0.0

        #
        # Distâncias geodésicas (Dijkstra, comprimento real de
        # aresta) a partir do seed_vertex, cobrindo a malha toda
        #

        self.geodesic_distance = {}

        #
        # Pesos finais usados na deformação, já normalizados
        # entre todos os Critical Points para cada vértice
        # {vertex_index : weight}
        #

        self.vertex_weights = {}

        #
        # Controle de validade
        #

        self.is_valid = False