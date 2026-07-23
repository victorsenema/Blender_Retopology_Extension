import bmesh


class Deformation:

    def __init__(self, session, points=None):

        self.session = session

        self.points = (
            points
            if points is not None
            else session.template.critical_points
        )

    # ---------------------------------------------------------

    def execute(self):

        mesh = self.session.template.mesh

        bm = bmesh.new()

        bm.from_mesh(mesh.data)

        bm.verts.ensure_lookup_table()

        #
        # critical_point.offset é calculado em espaço MUNDO
        # (target_position - empty.matrix_world.translation),
        # mas vertex.co é em espaço LOCAL do Template_Mesh. O
        # Alignment sempre bota escala/rotação em
        # mesh.matrix_world (nunca edita a geometria), então
        # sem essa conversão estávamos somando um vetor de
        # mundo direto numa coordenada local -- errado sempre
        # que o objeto tiver qualquer escala/rotação, o que é
        # o caso desde o primeiro Alignment.
        #

        world_to_local = (
            mesh.matrix_world.inverted().to_3x3()
        )

        #
        # Deforma TODOS os pontos válidos
        #

        for critical_point in self.points:

            if not critical_point.is_valid:
                continue

            self.deform(
                bm,
                critical_point,
                world_to_local
            )

        bm.to_mesh(mesh.data)

        mesh.data.update()

        bm.free()

    # ---------------------------------------------------------

    def deform(
        self,
        bm,
        critical_point,
        world_to_local
    ):

        offset_local = (
            world_to_local @ critical_point.offset
        )

        moved_vertices = 0

        for vertex_index, weight in (

            critical_point.vertex_weights.items()

        ):

            vertex = bm.verts[
                vertex_index
            ]

            vertex.co += offset_local * weight

            moved_vertices += 1

        print(

            f"{critical_point.name} -> "

            f"{moved_vertices} vertices moved"

        )