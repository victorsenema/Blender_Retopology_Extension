import bpy


class RETOPOLOGY_PT_panel(bpy.types.Panel):
    bl_label = "Retopology"
    bl_idname = "RETOPOLOGY_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Retopology"

    def draw(self, context):

        layout = self.layout

        layout.label(text="Target")

        layout.prop(
            context.scene,
            "retopo_target",
            text=""
        )

        layout.separator()

        layout.label(text="Landmarking")

        layout.operator(
            "retopo.create_critical_points",
            text="Create Critical Points",
            icon='EMPTY_AXIS'
        )

        layout.separator()

        layout.label(text="Template")

        layout.operator(
            "retopo.apply_mesh",
            text="Apply Mesh",
            icon='MESH_GRID'
        )

        layout.operator(
            "retopo.apply_modifiers",
            text="Apply Modifiers",
            icon='CHECKMARK'
        )
