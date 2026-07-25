import bpy
from mathutils import Vector, Matrix
from .rotation import Rotation
from .scale import Scale
from ..blender_utils import normalize_point_name

class Alignment:

    def __init__(self, session):

        self.session = session

        self.template_points = {}
        self.user_points = {}

    def execute(self):
        bpy.context.view_layer.update()

        self.collect_template_points()
        self.collect_user_points()

        self.print_matches()

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

            self.user_points[
                normalize_point_name(point.name)
            ] = point.empty

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