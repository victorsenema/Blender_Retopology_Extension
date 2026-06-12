import bpy

class RETOPO_OT_create_control(bpy.types.Operator):
    bl_idname = "retopo.create_control"
    bl_label = "Create Control"

    def execute(self, context):

        bpy.ops.object.empty_add(
            type='SPHERE',
            location=(0, 0, 0)
        )

        empty = context.active_object
        empty.name = "RetopoControl"

        return {'FINISHED'}