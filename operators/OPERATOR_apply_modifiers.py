import bpy

from ..core import session
from ..core.blender_utils import is_valid
from ..core.fitting.finalize import apply_all_modifiers


class OPERATOR_apply_modifiers(bpy.types.Operator):

    #
    # Passo final: finaliza TODOS os modifiers na malha (o
    # Shrinkwrap de "Apply Mesh" e a Subdivision de "Add
    # Subdivision", com o segundo Shrinkwrap que vem junto dela --
    # ver core/fitting/finalize.py). Os critical points já não
    # existem mais nesse ponto -- Apply Mesh (Fitting.execute) já
    # os removeu da cena assim que terminou o warp TPS, ver
    # Fitting.destroy_critical_points().
    #

    bl_idname = "retopo.apply_modifiers"
    bl_label = "Apply Modifiers"
    bl_description = "Finaliza todos os modifiers na malha"

    def execute(self, context):

        #
        # Ver a nota em OPERATOR_add_subdivision: a referência
        # guardada morre num Ctrl+Z, o nome sobrevive.
        #

        mesh = session.resolve_template_mesh()

        if not is_valid(mesh):

            self.report(
                {'ERROR'},
                "Rode 'Apply Mesh' antes de aplicar os modifiers."
            )

            return {'CANCELLED'}

        applied = apply_all_modifiers(mesh)

        if not applied:

            self.report(
                {'WARNING'},
                "Nenhum modifier encontrado pra aplicar."
            )

        else:

            #
            # Fim do pipeline: os vertex groups de controle
            # sobrevivem ao bake (vivem no objeto, e as pesagens
            # viajam no bmesh), então sem isto os pontos ficariam
            # desenhados pra sempre numa malha que já está pronta.
            #
            # Desliga o toggle em vez de apagar os grupos: é
            # reversível, e não destrói dado que o usuário pode
            # querer pra um rig depois.
            #

            context.scene.retopo_show_control_points = False

            self.report(
                {'INFO'},
                "Modifiers aplicados. Pontos de controle ocultados."
            )

        return {'FINISHED'}
