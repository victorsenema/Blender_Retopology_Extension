from mathutils import Matrix


class Scale:

    def __init__(self, template_points, user_points):

        self.template_points = template_points
        self.user_points = user_points

    def distance(self, points, a, b):

        return (
            points[a].matrix_world.translation -
            points[b].matrix_world.translation
        ).length

    def calculate_matrix(self):

        #
        # Width (JawLeft -> JawRight)
        #

        template_width = self.distance(
            self.template_points,
            "JawLeft",
            "JawRight"
        )

        user_width = self.distance(
            self.user_points,
            "JawLeft",
            "JawRight"
        )

        scale_x = user_width / template_width

        #
        # Height (ForeheadTop -> Chin)
        #

        template_height = self.distance(
            self.template_points,
            "ForeheadTop",
            "Chin"
        )

        user_height = self.distance(
            self.user_points,
            "ForeheadTop",
            "Chin"
        )

        scale_z = user_height / template_height

        #
        # Depth
        #

        scale_y = 1.0

        print("\n========== SCALE ==========")
        print(f"Scale X : {scale_x:.4f}")
        print(f"Scale Y : {scale_y:.4f}")
        print(f"Scale Z : {scale_z:.4f}")

        scale = Matrix.Identity(4)

        scale[0][0] = scale_x
        scale[1][1] = scale_y
        scale[2][2] = scale_z

        return scale