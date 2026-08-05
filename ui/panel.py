import bpy

from ..core import session
from ..core.blender_utils import is_valid
from ..core.fitting.relax import RELAX_MODIFIER_NAME


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

        layout.separator()

        layout.label(text="Relax")

        layout.operator(
            "retopo.relax_mesh",
            text="Relax Mesh",
            icon='MOD_SMOOTH'
        )

        #
        # O slider só aparece depois que o modifier existe (ou
        # seja, depois de clicar em "Relax Mesh" pelo menos uma
        # vez). Ele é ligado DIRETO na property do modifier
        # (modifier.factor) -- arrastar atualiza a malha na
        # viewport ao vivo, é o próprio Blender fazendo isso.
        #

        relax_modifier = self.get_relax_modifier()

        if relax_modifier is not None:

            layout.prop(
                relax_modifier,
                "factor",
                text="Relax Amount",
                slider=True
            )

        layout.separator()

        layout.operator(
            "retopo.apply_modifiers",
            text="Apply Modifiers",
            icon='CHECKMARK'
        )

    # -----------------------------------------------------------

    def get_relax_modifier(self):

        if session.template is None:
            return None

        mesh = session.template.mesh

        if not is_valid(mesh):
            return None

        return mesh.modifiers.get(RELAX_MODIFIER_NAME)
