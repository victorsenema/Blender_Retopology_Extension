import bpy

from ..core import session
from ..core.fitting.fitting import Fitting


class OPERATOR_apply_mesh(bpy.types.Operator):

    bl_idname = "retopo.apply_mesh"
    bl_label = "Apply Mesh"
    bl_description = "Import the topology template"

    def execute(self, context):

        fitting = Fitting(session)
        fitting.execute()

        self.report({'INFO'}, "Template Imported")

        return {'FINISHED'}