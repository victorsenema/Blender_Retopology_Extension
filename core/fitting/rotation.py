from mathutils import Matrix


class Rotation:

    def __init__(self,
                 template_horizontal,
                 template_vertical,
                 user_horizontal,
                 user_vertical):

        self.template_horizontal = template_horizontal
        self.template_vertical = template_vertical

        self.user_horizontal = user_horizontal
        self.user_vertical = user_vertical


    def build_basis(self, horizontal, vertical):

        x = horizontal.normalized()

        y = vertical.normalized()

        z = x.cross(y).normalized()

        # Reortogonaliza Y
        y = z.cross(x).normalized()

        return Matrix((
            x,
            y,
            z
        )).transposed()


    def calculate_matrix(self):

        template_basis = self.build_basis(
            self.template_horizontal,
            self.template_vertical
        )

        user_basis = self.build_basis(
            self.user_horizontal,
            self.user_vertical
        )

        return user_basis @ template_basis.inverted()