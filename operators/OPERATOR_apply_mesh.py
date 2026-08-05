import bpy

from ..core import session
from ..core.fitting.fitting import Fitting


class OPERATOR_apply_mesh(bpy.types.Operator):

    bl_idname = "retopo.apply_mesh"
    bl_label = "Apply Mesh"
    bl_description = "Import the topology template"

    def execute(self, context):

        #
        # A malha alvo é a que o usuário escolheu no dropper do
        # painel (Scene.retopo_target) -- não é mais detectada
        # por ray cast durante o Landmarking.
        #

        if context.scene.retopo_target is None:

            self.report(
                {'ERROR'},
                "Selecione a malha alvo (Target Mesh) no painel antes."
            )

            return {'CANCELLED'}

        session.target_mesh = context.scene.retopo_target

        fitting = Fitting(session)
        fitting.execute()

        self.report({'INFO'}, "Template Imported")

        return {'FINISHED'}
