import bpy
from ..core.template_manager import load_template


class OPERATOR_load_template(bpy.types.Operator):
    # Import the template and initialize all its data

    bl_idname = "retopo.load_template"
    bl_label = "Load Template"

    def execute(self, context):

        anchors = load_template()

        return {'FINISHED'}