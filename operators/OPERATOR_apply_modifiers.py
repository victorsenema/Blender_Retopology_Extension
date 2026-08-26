import bpy

from ..core import session
from ..core.blender_utils import is_valid
from ..core.fitting.finalize import apply_all_modifiers


class OPERATOR_apply_modifiers(bpy.types.Operator):

    #
    # Passo final: finaliza TODOS os modifiers na malha (o
    # Shrinkwrap de "Apply Mesh", a Subdivision de "Add
    # Subdivision" e o Relax de "Relax Mesh" se estiver ativo --
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

            self.report(
                {'INFO'},
                "Modifiers aplicados."
            )

        return {'FINISHED'}
