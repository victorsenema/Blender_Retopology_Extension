import bpy

class RETOPO_OT_create_test_mesh(bpy.types.Operator):
    bl_idname = "retopo.create_test_mesh"
    bl_label = "Create Test Mesh"

    def execute(self, context):

        bpy.ops.mesh.primitive_circle_add(
            vertices=32,
            radius=1,
            fill_type='NGON'
        )

        obj = context.active_object
        obj.name = "RetopoTest"

        return {'FINISHED'}