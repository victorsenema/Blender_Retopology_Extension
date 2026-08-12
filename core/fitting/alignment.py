import bpy
from mathutils import Vector, Matrix
from .rotation import Rotation
from .scale import Scale
from ..blender_utils import normalize_point_name, is_valid

class Alignment:

    #
    # Pontos que o resto do Alignment/Scale/Rotation acessa por
    # nome exato (fora o "LeftEye"/"RightEye" por prefixo, que já
    # tem seu próprio guard em average_position). Se qualquer um
    # destes faltar -- de qualquer lado, template ou usuário --
    # o resto do cálculo quebraria com um erro sem contexto lá no
    # meio de scale.py/rotation.py; validate_required_points()
    # pega isso antes e dá um erro claro.
    #

    REQUIRED_POINTS = (
        "JawLeft",
        "JawRight",
        "ForeheadTop",
        "Chin",
        "NoseRoot",
        "NoseTip",
    )

    def __init__(self, session):

        self.session = session

        self.template_points = {}
        self.user_points = {}

    def execute(self):
        bpy.context.view_layer.update()

        self.collect_template_points()
        self.collect_user_points()

        self.print_matches()

        self.validate_required_points()

        scale = self.calculate_scale()

        rotation = self.calculate_rotation()

        self.apply_alignment(
            scale,
            rotation
        )

    # --------------------------------------------------

    def collect_template_points(self):

        self.template_points.clear()

        print("\n========== TEMPLATE POINTS ==========")

        for critical_point in self.session.template.critical_points:

            #
            # Sem essa checagem, uma referência morta (Undo,
            # troca de modo etc. -- ver core/blender_utils.
            # is_valid) ficava guardada aqui silenciosamente e só
            # estourava um ReferenceError depois, lá dentro de
            # scale.py, sem dizer qual ponto era o problema.
            #

            if not is_valid(critical_point.empty):

                print(
                    f"[Alignment] ERRO: referência do template "
                    f"point '{critical_point.name}' ficou "
                    f"inválida -- pulando."
                )

                continue

            empty = critical_point.empty

            key = normalize_point_name(critical_point.name)

            self.template_points[key] = empty

            print(
                key,
                id(empty),
                empty.location,
                empty.matrix_world.translation
            )

    # --------------------------------------------------

    def collect_user_points(self):

        self.user_points.clear()

        for point in self.session.critical_points:

            if not is_valid(point.empty):

                print(
                    f"[Alignment] ERRO: referência do critical "
                    f"point do usuário '{point.name}' ficou "
                    f"inválida (Undo, troca de modo, etc. entre o "
                    f"Landmarking e o Apply Mesh) -- pulando."
                )

                continue

            self.user_points[
                normalize_point_name(point.name)
            ] = point.empty

    # --------------------------------------------------

    def validate_required_points(self):

        for label, points in (
            ("template", self.template_points),
            ("usuário", self.user_points),
        ):

            missing = [
                name for name in self.REQUIRED_POINTS
                if name not in points
            ]

            if missing:

                raise RuntimeError(
                    f"Faltam pontos obrigatórios no lado do "
                    f"{label}: {', '.join(missing)}. Alguma "
                    f"referência ficou inválida (Undo/troca de "
                    f"modo?) ou o Landmarking não terminou -- "
                    f"rode 'Create Critical Points' de novo e "
                    f"depois 'Apply Mesh'."
                )

    # --------------------------------------------------

    def print_matches(self):

        print("\n========== ALIGNMENT ==========")

        for name in self.template_points:

            print(name)

    # --------------------------------------------------

    def calculate_center(self, points):

        center = Vector((0.0, 0.0, 0.0))

        for point in points.values():

            center += point.matrix_world.translation

        center /= len(points)

        return center

    # --------------------------------------------------

    def get_horizontal_axis(self, points):

        #
        # Não existe mais um único ponto "LeftEye"/"RightEye"
        # no template novo (viraram vários pontos por olho:
        # _Top, _Bottom, _Inner_Side, _Outer_Side) -- usa a
        # média de todos os pontos de cada olho como o "centro"
        # daquele olho pro eixo horizontal.
        #

        left = self.average_position(points, "LeftEye")
        right = self.average_position(points, "RightEye")

        axis = right - left
        axis.normalize()

        return axis

    # --------------------------------------------------

    def average_position(self, points, name_prefix):

        matches = [
            point.matrix_world.translation
            for name, point in points.items()
            if name.startswith(name_prefix)
        ]

        if not matches:
            raise RuntimeError(
                f"Nenhum critical point com prefixo "
                f"'{name_prefix}' encontrado."
            )

        center = Vector((0.0, 0.0, 0.0))

        for position in matches:
            center += position

        center /= len(matches)

        return center

    # --------------------------------------------------

    def get_vertical_axis(self, points):

        top = points["NoseRoot"].matrix_world.translation
        bottom = points["Chin"].matrix_world.translation

        axis = bottom - top
        axis.normalize()

        return axis

    # --------------------------------------------------

    def calculate_rotation(self):

        rotation = Rotation(

            self.get_horizontal_axis(
                self.template_points
            ),

            self.get_vertical_axis(
                self.template_points
            ),

            self.get_horizontal_axis(
                self.user_points
            ),

            self.get_vertical_axis(
                self.user_points
            )

        )

        return rotation.calculate_matrix().to_4x4()

    # --------------------------------------------------

    def apply_alignment(self,scale,rotation):

        template_center = self.calculate_center(
            self.template_points
        )

        user_center = self.calculate_center(
            self.user_points
        )

        #
        # SCALE
        #

        T = Matrix.Translation(template_center)
        T_inv = Matrix.Translation(-template_center)

        scale_transform = T @ scale @ T_inv

        for obj in self.session.template.objects:

            obj.matrix_world = (
                scale_transform @ obj.matrix_world
            )

        bpy.context.view_layer.update()

        #
        # ROTATION
        #

        template_center = self.calculate_center(
            self.template_points
        )

        T = Matrix.Translation(template_center)
        T_inv = Matrix.Translation(-template_center)

        rotation_transform = (
            T @ rotation @ T_inv
        )

        for obj in self.session.template.objects:

            obj.matrix_world = (
                rotation_transform @ obj.matrix_world
            )

        bpy.context.view_layer.update()

        #
        # TRANSLATION
        #

        template_center = self.calculate_center(
            self.template_points
        )

        translation = user_center - template_center

        for obj in self.session.template.objects:

            obj.location += translation

        bpy.context.view_layer.update()

        print("\n========== ALIGNMENT CHECK ==========")
        print("User center:", user_center)
        print(
            "Template center (after alignment):",
            self.calculate_center(self.template_points)
        )

    def calculate_scale(self):

        scale = Scale(

            self.template_points,

            self.user_points

        )

        return scale.calculate_matrix()