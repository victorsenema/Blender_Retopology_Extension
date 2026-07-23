import bpy

from ..core import session
from ..core.blender_utils import is_valid
from ..core.fitting.fitting import Fitting


class OPERATOR_apply_projection(bpy.types.Operator):

    bl_idname = "retopo.apply_projection"
    bl_label = "Apply Projection"
    bl_description = (
        "Cola o template sobre a malha esculpida (target_mesh), "
        "por cima do resultado atual da malha"
    )

    def execute(self, context):

        if session.template is None or not is_valid(session.template.mesh):

            self.report(
                {'ERROR'},
                "Rode 'Apply Mesh' antes de aplicar a projeção."
            )

            return {'CANCELLED'}

        if not is_valid(session.target_mesh):

            self.report(
                {'ERROR'},
                "Nenhuma malha alvo (target_mesh) válida foi "
                "detectada. Refaça o Landmarking clicando em "
                "cima da malha esculpida."
            )

            return {'CANCELLED'}

        fitting = Fitting(session)
        fitting.project_onto_target()

        self.report({'INFO'}, "Projeção aplicada")

        return {'FINISHED'}
