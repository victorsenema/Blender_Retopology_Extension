class Targets:

    def __init__(self, session, template_points=None, user_points=None):

        self.session = session

        self.template_points = (
            template_points
            if template_points is not None
            else session.template.critical_points
        )

        self.user_points_source = (
            user_points
            if user_points is not None
            else session.critical_points
        )

    # ---------------------------------------------------------

    def assign(self):

        user_points = {}

        #
        # Cria um dicionário dos pontos do usuário
        #

        for point in self.user_points_source:

            name = point.name

            user_points[name] = point

        #
        # Associa cada ponto da template ao usuário
        #

        for critical_point in self.template_points:

            name = critical_point.name.replace(
                "CriticalPoint_",
                ""
            ).replace(
                "RefinementPoint_",
                ""
            )

            user_point = user_points.get(name)

            if user_point is None:

                print(
                    f"[ERROR] User Point '{name}' not found."
                )

                continue

            critical_point.target_position = (
                user_point.empty.matrix_world.translation.copy()
            )

            critical_point.offset = (

                critical_point.target_position -

                critical_point.empty.matrix_world.translation

            )

            print(
                f"{critical_point.name} -> "
                f"{critical_point.offset}"
            )