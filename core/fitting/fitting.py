from ..template_manager import import_template

from .alignment import Alignment
from .structure_warp import StructureWarp
from .projection import SurfaceProjection


ENABLE_SURFACE_PROJECTION = True


class Fitting:

    #
    # Pipeline de instanciação da malha: importa o template,
    # alinha rígido, aplica o warp não-rígido (TPS) usando os
    # critical points, e deixa um modifier Shrinkwrap
    # configurado (NÃO aplicado) apontando pra malha alvo --
    # a finalização (bake do Shrinkwrap + remoção dos critical
    # points) é um passo manual separado, ver
    # operators/OPERATOR_apply_modifiers.py.
    #

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
        # rotação, translação). Isso move a malha E os critical
        # points juntos, já que ambos estão em
        # session.template.objects.
        #

        alignment = Alignment(
            self.session
        )

        alignment.execute()

        #
        # 2
        # Warp não-rígido global (TPS) usando os Critical
        # Points: resolve o warp da malha inteira de uma vez,
        # minimizando energia de dobra e batendo exato em cada
        # landmark. Ver core/fitting/tps.py.
        #

        structure_warp = StructureWarp(
            self.session
        )

        structure_warp.execute()

        #
        # 3
        # Adiciona o modifier Shrinkwrap apontando pra malha
        # alvo (Scene.retopo_target). Fica como modifier vivo --
        # não é aplicado aqui.
        #

        if ENABLE_SURFACE_PROJECTION:

            self.add_surface_projection()

        else:

            print(
                "\n[INFO] Projeção de superfície desativada "
                "(ENABLE_SURFACE_PROJECTION = False)."
            )

        print("\n========== FITTING FINISHED ==========")

    # ---------------------------------------------------------

    def add_surface_projection(self):

        projection = SurfaceProjection(
            self.session
        )

        if projection.target is None:

            print(
                "[WARN] Nenhuma malha alvo (Target Mesh) selecionada "
                "no painel; pulando o Shrinkwrap."
            )

        else:

            projection.add_modifier()
