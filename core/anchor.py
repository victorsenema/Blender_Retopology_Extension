class Anchor:
    # Anchor the Critical Point (a object) with the vetex that it over in the template
    # Wen the anchor moves the Vertex moves

    def __init__(self, critical_point, vertex_main_anchored):
        self.critical_point = critical_point
        self.vertex = vertex_main_anchored
        self.vertex_weights = []

        self.initial_empty_position = (critical_point.empty.location.copy())
        self.initial_vertex_position = (vertex_main_anchored.co.copy())

    #update the base vertex position when the empty chance position
    def update_position(self):

        offset = (self.critical_point.empty.location - self.initial_empty_position)

        for vertex_weight in self.vertex_weights:
            vertex_weight.vertex.co = (vertex_weight.initial_vertex_position + offset * vertex_weight.weight)