import bmesh

class VertexWeight:
    # This class will be used to assign the weight a vertex have to an specific anchor
    # Inside the anchor class there's a array for that
    # So whenever the anchor moves all the vertex assigned to that anchor moves
    def __init__(self, vertex, weight):
        self.vertex = vertex
        self.weight = weight
        self.initial_vertex_position = vertex.co.copy()

def calculate_weight(distance, decay=0.05):
    #calculate the weight of the vertex (not the vertex_main_anchored, but the other ones)
    return decay ** distance

def multi_source_BFS_weight_assign(template_mesh, anchors, decay=0.5):
    # BFS that assigns the weight to a vertex
    # Codition:
        # Expand all anchors one step at a time.
        # Assign weight = decay ^ distance.
        # A vertex can only belong to one anchor.
        # Already assigned vertices are skipped.
        # Continue until every vertex has been assigned.

    bm = bmesh.new() # Need the bmesh beacuse of current_vertex.link_edges
    bm.from_mesh(template_mesh.data)
    bm.verts.ensure_lookup_table()

    for anchor in anchors:
        anchor.vertex_weights.clear()

    visited = set()
    frontier = []

    # Initialize frontier with anchor vertices
    for anchor in anchors:
        bm_vertex = bm.verts[anchor.vertex.index]
        frontier.append((anchor, bm_vertex, 0))
        visited.add(bm_vertex.index)
    
    while frontier:

        next_frontier = []

        for anchor, current_vertex, distance in frontier:

            weight = calculate_weight(distance, decay)

            mesh_vertex = template_mesh.data.vertices[current_vertex.index]

            anchor.vertex_weights.append(
                VertexWeight(mesh_vertex, weight)
            )

            for edge in current_vertex.link_edges:

                neighbor = edge.other_vert(current_vertex)

                if neighbor.index not in visited:
                    visited.add(neighbor.index)

                    next_frontier.append(
                        (anchor, neighbor, distance + 1)
                    )

        frontier = next_frontier
    bm.free()