import bpy

from ..template_manager import import_template
from ..blender_utils import is_valid

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

    def __init__(self, session, exclude_points=None):

        self.session = session

        #
        # Repassado pro StructureWarp -- nomes normalizados de
        # critical points a IGNORAR na correspondência do TPS.
        # Usado pelos botões de teste (ver
        # operators/OPERATOR_test_inside_nose*.py); None/vazio =
        # usa todos os pontos posicionados, comportamento normal.
        #

        self.exclude_points = exclude_points

    def execute(self):

        print("\n========== FITTING ==========")

        #
        # Importa a Template
        #

        self.session.template = import_template()

        print("Template imported successfully.")

        try:

            #
            # 1
            # Alinha aproximadamente a template (rígido: escala,
            # rotação, translação). Isso move a malha E os
            # critical points juntos, já que ambos estão em
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
            # minimizando energia de dobra e batendo exato em
            # cada landmark. Ver core/fitting/tps.py.
            #

            structure_warp = StructureWarp(
                self.session,
                exclude_points=self.exclude_points
            )

            structure_warp.execute()

            #
            # 3
            # Adiciona o modifier Shrinkwrap apontando pra malha
            # alvo (Scene.retopo_target). Fica como modifier
            # vivo -- não é aplicado aqui.
            #

            if ENABLE_SURFACE_PROJECTION:

                self.add_surface_projection()

            else:

                print(
                    "\n[INFO] Projeção de superfície desativada "
                    "(ENABLE_SURFACE_PROJECTION = False)."
                )

        except Exception:

            #
            # Se qualquer passo acima falhar (ex.: referência
            # inválida, ver Alignment.validate_required_points),
            # o template já foi importado e linkado na cena --
            # sem isso aqui ele ficava largado, e cada tentativa
            # nova empilhava mais um conjunto de objetos órfãos
            # (com sufixo .001, .002...) na cena. Desfaz a
            # importação e relança o erro original pra quem
            # chamou (o operator) decidir como reportar.
            #

            self.cleanup_failed_import()

            raise

        print("\n========== FITTING FINISHED ==========")

    # ---------------------------------------------------------

    def cleanup_failed_import(self):

        template = self.session.template

        if template is None:
            return

        removed = 0

        for obj in list(template.objects):

            if is_valid(obj):

                bpy.data.objects.remove(obj, do_unlink=True)

                removed += 1

        self.session.template = None

        print(
            f"[Fitting] Falha no meio do processo -- {removed} "
            f"objetos do template importado foram removidos da "
            f"cena pra não deixar lixo."
        )

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
