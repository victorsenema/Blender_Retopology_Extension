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

        fitting.execute()

        self.report(
            {'INFO'},
            "Template Imported (teste: Inside Nose + Nostrils)"
        )

        return {'FINISHED'}
