def deform_mesh(mesh_obj,
                control_location,
                weights,
                base_positions):

    mesh = mesh_obj.data

    for i, vertex in enumerate(mesh.vertices):

        weight = weights[i]

        vertex.co = (
            base_positions[i]
            + control_location * weight
        )