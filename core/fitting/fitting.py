from ..template_manager import import_template

from .alignment import Alignment

from .deformation.vertex_groups import VertexGroups
from .deformation.geodesic import Geodesic
from .deformation.weights import Weights
from .deformation.targets import Targets
from .deformation.deformation import Deformation

from .projection import SurfaceProjection


#
# Reativado: agora que Structure+Refinement+bugs de espaço
# local/mundo estão corrigidos, o foco atual é fazer essa
# projeção final funcionar bem. Ver core/fitting/projection.py
# (reescrito pra usar o modifier Shrinkwrap nativo, modo PROJECT).
#

ENABLE_SURFACE_PROJECTION = True


class Fitting:

    def __init__(self, session):

        self.session = session

    def execute(self):

        print("\n========== FITTING ==========")

        #
        # Importa a Template
        #

        self.session.template = import_template()

        print("Template imported successfully.")

        #
        # 1
        # Alinha aproximadamente a template (rígido: escala,
        # rotação, translação). Isso move a malha E os dois
        # grupos de Empties (critical points e refinement
        # points) juntos, já que ambos estão em
        # session.template.objects.
        #

        alignment = Alignment(
            self.session
        )

        alignment.execute()

        #
        # 2 a 6 -- aproximação usando os Base Structure
        # Critical Points
        #

        self.apply_points(
            self.session.template.critical_points,
            self.session.critical_points,
            label="Structure"
        )

        #
        # 7
        # Cola o template sobre a superfície esculpida
        # (desativado por enquanto, ver ENABLE_SURFACE_PROJECTION)
        #

        if ENABLE_SURFACE_PROJECTION:

            self.project_onto_target()

        else:

            print(
                "\n[INFO] Projeção de superfície desativada "
                "(ENABLE_SURFACE_PROJECTION = False)."
            )

        print("\n========== FITTING FINISHED ==========")

    # ---------------------------------------------------------

    def apply_refinement(self):

        #
        # Segunda passada: usa os Refinement Critical Points
        # pra ajustar a malha localmente por cima do resultado
        # da primeira passada (Structure). NÃO refaz o
        # alinhamento rígido -- só refina forma.
        #

        print("\n========== REFINEMENT ==========")

        self.apply_points(
            self.session.template.refinement_points,
            self.session.refinement_points,
            label="Refinement"
        )

        if ENABLE_SURFACE_PROJECTION:

            self.project_onto_target()

        print("\n========== REFINEMENT FINISHED ==========")

    # ---------------------------------------------------------

    def apply_points(self, template_points, user_points, label):

        #
        # 2
        # Acha o vértice-semente de cada ponto
        #

        vertex_groups = VertexGroups(
            self.session.template,
            template_points
        )

        vertex_groups.assign()

        #
        # 3
        # Calcula distâncias geodésicas
        #

        geodesic = Geodesic(
            self.session.template,
            template_points
        )

        geodesic.calculate()

        #
        # 4
        # Calcula pesos finais (normalizados entre todos os
        # pontos dessa passada)
        #

        weights = Weights(
            self.session.template,
            template_points
        )

        weights.calculate()

        #
        # 5
        # Calcula offsets em relação aos pontos do usuário
        #

        targets = Targets(
            self.session,
            template_points,
            user_points
        )

        targets.assign()

        #
        # 6
        # Deforma a malha
        #

        deformation = Deformation(
            self.session,
            template_points
        )

        deformation.execute()

        print(f"[{label}] passada de deformação concluída.")

    # ---------------------------------------------------------

    def project_onto_target(self):

        projection = SurfaceProjection(
            self.session
        )

        if projection.target is None:

            print(
                "[WARN] Nenhuma malha alvo (target_mesh) foi "
                "detectada durante o Landmarking; pulando a projeção."
            )

        else:

            projection.project()
