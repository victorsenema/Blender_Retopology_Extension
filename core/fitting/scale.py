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
        # Depth -- NoseTip é o ponto mais frontal do rosto;
        # o ponto médio entre JawLeft/JawRight aproxima o
        # "plano dos ouvidos". A distância entre os dois dá
        # uma medida de profundidade da cabeça, do mesmo jeito
        # que largura usa JawLeft/JawRight e altura usa
        # ForeheadTop/Chin. Antes disso, scale_y ficava fixo
        # em 1.0 -- por isso o perfil saía achatado, sem o
        # volume de nariz/queixo do rosto alvo.
        #

        template_depth = self.calculate_depth(
            self.template_points
        )

        user_depth = self.calculate_depth(
            self.user_points
        )

        scale_y = user_depth / template_depth

        print("\n========== SCALE ==========")
        print(f"Scale X : {scale_x:.4f}")
        print(f"Scale Y : {scale_y:.4f}")
        print(f"Scale Z : {scale_z:.4f}")

        scale = Matrix.Identity(4)

        scale[0][0] = scale_x
        scale[1][1] = scale_y
        scale[2][2] = scale_z

        return scale

    # -------------------------------------------------------------

    def calculate_depth(self, points):

        jaw_left = points["JawLeft"].matrix_world.translation
        jaw_right = points["JawRight"].matrix_world.translation

        ear_plane_center = (jaw_left + jaw_right) / 2

        nose_tip = points["NoseTip"].matrix_world.translation

        return (nose_tip - ear_plane_center).length