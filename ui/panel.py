import bpy

class RETOPO_PT_panel(bpy.types.Panel):

    bl_label = "Retopology"
    bl_idname = "RETOPOLOGY_PANEL"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Retopology"

    def draw(self, context):
        layout = self.layout

        # All operators are in the operators folder
        layout.operator("retopo.load_template", text="Load Template")