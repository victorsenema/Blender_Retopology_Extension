import bpy

from ..core import session
from ..core.blender_utils import is_valid
from ..core.fitting.fitting import Fitting


class OPERATOR_apply_refinement(bpy.types.Operator):

    bl_idname = "retopo.apply_refinement"
    bl_label = "Apply Refinement"
    bl_description = (
        "Refina a malha usando os Refinement Critical Points, "
        "por cima do resultado da aproximação de estrutura"
    )

    def execute(self, context):

        if session.template is None:

            self.report(
                {'ERROR'},
                "Rode 'Apply Mesh' antes de aplicar o refinamento."
            )

            return {'CANCELLED'}

        if not is_valid(session.template.mesh):

            self.report(
                {'ERROR'},
                "A referência ao template ficou inválida "
                "(provavelmente por causa de um Ctrl+Z/Undo depois "
                "de 'Apply Mesh'). Rode 'Apply Mesh' de novo antes "
                "de aplicar o refinamento."
            )

            return {'CANCELLED'}

        if not session.refinement_points:

            self.report(
                {'ERROR'},
                "Nenhum Refinement Point foi posicionado ainda."
            )

            return {'CANCELLED'}

        fitting = Fitting(session)
        fitting.apply_refinement()

        self.report({'INFO'}, "Refinamento aplicado")

        return {'FINISHED'}
