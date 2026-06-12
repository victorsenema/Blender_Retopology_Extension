import bpy

class RETOPO_PT_panel(bpy.types.Panel):
    bl_label = "Retopo Template"
    bl_idname = "RETOPO_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Retopo"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            "retopo.create_test_mesh",
            text="Create Test Mesh"
        )

        layout.operator(
            "retopo.create_control",
            text="Create Control Point"
        )
        
        layout.operator(
        "retopo.import_template",
        text="Import Template"
        )