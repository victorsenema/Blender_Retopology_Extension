import traceback

import bpy

from ..core import session
from ..core.fitting.fitting import Fitting


class OPERATOR_test_inside_nose_and_nostrils(bpy.types.Operator):

    #
    # Único botão de instanciação de malha do addon (era um de 3
    # variantes de teste -- "Apply Mesh" sem os pontos de dentro
    # do nariz, e "Test Inside Nose" sem os de narina, foram
    # removidos depois que este deu o melhor resultado nos
    # testes). Usa os 27 critical points inteiros, narina E
    # dentro do nariz juntos, sem excluir nada da correspondência
    # do TPS (ver Fitting.__init__ -- ainda aceita exclude_points
    # se algum teste desse tipo precisar voltar no futuro).
    #

    bl_idname = "retopo.test_inside_nose_and_nostrils"
    bl_label = "Test Inside Nose + Nostrils"
    bl_description = (
        "Teste: Apply Mesh usando TODOS os pontos, narina e dentro "
        "do nariz juntos"
    )

    def execute(self, context):

        if context.scene.retopo_target is None:

            self.report(
                {'ERROR'},
                "Selecione a malha alvo (Target Mesh) no painel antes."
            )

            return {'CANCELLED'}

        session.target_mesh = context.scene.retopo_target

        fitting = Fitting(session)

        try:

            fitting.execute()

        except RuntimeError as error:

            #
            # Erros "esperados" (ex.: referência de critical
            # point ficou inválida por Undo/troca de modo entre
            # Landmarking e Apply Mesh -- ver
            # Alignment.validate_required_points) já vêm com
            # mensagem clara o bastante pra mostrar direto pro
            # usuário, sem traceback.
            #

            self.report({'ERROR'}, str(error))

            return {'CANCELLED'}

        except Exception as error:

            #
            # Qualquer outra coisa inesperada: ainda reporta
            # limpo na UI, mas manda o traceback completo pro
            # console/System Console pra dar pra debugar.
            #

            traceback.print_exc()

            self.report(
                {'ERROR'},
                f"Apply Mesh falhou ({error}). Veja o System Console "
                f"pra detalhes."
            )

            return {'CANCELLED'}

        self.report(
            {'INFO'},
            "Template Imported (teste: Inside Nose + Nostrils)"
        )

        return {'FINISHED'}
