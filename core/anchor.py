anchors = []

class Anchor:
    def __init__(self, empty_obj, mesh_obj, vertex_index, weights):
        self.empty = empty_obj
        self.mesh = mesh_obj
        self.vertex_index = vertex_index

        self.initial_empty_pos = empty_obj.location.copy()
        self.initial_vertex_pos = (mesh_obj.data.vertices[vertex_index].co.copy())

        self.weights = weights

        self.base_positions = {}
        for v in mesh_obj.data.vertices:
            self.base_positions[v.index] = v.co.copy()

    def update(self):

        offset = (self.empty.location - self.initial_empty_pos)

        for vertex_index, weight in self.weights.items():

            vertex = self.mesh.data.vertices[vertex_index]

            vertex.co = (self.base_positions[vertex_index] + offset * weight)
