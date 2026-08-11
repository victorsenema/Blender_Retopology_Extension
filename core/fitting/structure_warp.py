import bmesh
from mathutils import Vector

from .tps import ThinPlateSpline
from ..blender_utils import normalize_point_name, is_valid


class StructureWarp:

    #
    # Warp global (TPS) da malha do template usando os Critical
    # Points. Roda depois do Alignment (rígido) e antes da
    # Projection (Shrinkwrap) -- ver core/fitting/tps.py pro
    # motivo de ser TPS e não um blend Gaussiano ponto-a-ponto.
    #

    MIN_POINTS = 4  # TPS 3D precisa de pelo menos 4 pontos não-coplanares

    def __init__(self, session, exclude_points=None):

        self.session = session

        #
        # Conjunto de nomes normalizados (sem prefixo
        # "CriticalPoint_") que NÃO devem entrar na
        # correspondência do TPS -- usado pelos botões de teste
        # (ver operators/OPERATOR_test_inside_nose*.py) pra
        # comparar o resultado com/sem certos pontos, sem
        # precisar remover Empty nenhum da cena.
        #

        self.exclude_points = (
            set(exclude_points) if exclude_points else set()
        )

    # -------------------------------------------------------------

    def execute(self):

        template = self.session.template

        source_points, target_points = self.collect_correspondences()

        if len(source_points) < self.MIN_POINTS:

            print(
                f"[StructureWarp] Só {len(source_points)} pontos "
                f"válidos (mínimo {self.MIN_POINTS}) -- pulando "
                f"warp não-rígido."
            )

            return

        tps = ThinPlateSpline(source_points, target_points)

        self.warp_mesh(template.mesh, tps)

        self.follow_warp(template, tps)

        print(
            f"[StructureWarp] TPS aplicado "
            f"({len(source_points)} landmarks)."
        )

    # -------------------------------------------------------------

    def collect_correspondences(self):

        user_points = {
            normalize_point_name(point.name): point
            for point in self.session.critical_points
            if is_valid(point.empty)
        }

        source_points = []
        target_points = []

        for critical_point in self.session.template.critical_points:

            if not is_valid(critical_point.empty):
                continue

            name = normalize_point_name(critical_point.name)

            if name in self.exclude_points:
                continue

            user_point = user_points.get(name)

            if user_point is None:

                print(f"[StructureWarp] User Point '{name}' não encontrado.")

                continue

            source_points.append(
                critical_point.empty.matrix_world.translation.copy()
            )

            target_points.append(
                user_point.empty.matrix_world.translation.copy()
            )

        return source_points, target_points

    # -------------------------------------------------------------

    def warp_mesh(self, mesh, tps):

        bm = bmesh.new()

        bm.from_mesh(mesh.data)

        bm.verts.ensure_lookup_table()

        world = mesh.matrix_world
        world_inv = world.inverted()

        world_positions = [
            world @ vertex.co
            for vertex in bm.verts
        ]

        warped_positions = tps.evaluate(world_positions)

        for vertex, warped in zip(bm.verts, warped_positions):

            vertex.co = world_inv @ Vector(warped)

        bm.to_mesh(mesh.data)

        mesh.data.update()

        bm.free()

    # -------------------------------------------------------------

    def follow_warp(self, template, tps):

        #
        # Os Empties dos critical points não fazem parte da
        # malha, então o warp acima não os move -- arrasta eles
        # junto (interpolação do TPS é exata nos landmarks, então
        # cada um cai exatamente sobre onde o usuário clicou).
        #

        for critical_point in template.critical_points:

            if not is_valid(critical_point.empty):
                continue

            warped = tps.evaluate(
                [critical_point.empty.matrix_world.translation]
            )[0]

            critical_point.empty.matrix_world.translation = Vector(warped)
