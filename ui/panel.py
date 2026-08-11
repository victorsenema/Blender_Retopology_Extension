import bpy

from ..core import session
from ..core.blender_utils import is_valid
from ..core.fitting.modifier_stack import SUBDIVISION_MODIFIER_NAME


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
            "retopo.test_inside_nose_and_nostrils",
            text="Apply Mesh",
            icon='MESH_GRID'
        )

        layout.separator()

        #
        # Ordem no painel espelha a ordem no modifier stack:
        # Subdivision -> Shrinkwrap (acima) -> Relax.
        #
        # OBS.: o botão/slider de Relax foi escondido do painel a
        # pedido (só visualmente -- core/fitting/relax.py e
        # operators/OPERATOR_relax_mesh.py continuam intactos,
        # registrados, e utilizáveis via busca de operator/F3).
        # Perguntar ao usuário o que fazer com o relaxamento
        # (trazer de volta pro painel, mudar de abordagem, ou
        # remover de vez) numa próxima sessão.
        #

        layout.label(text="Subdivision")

        layout.operator(
            "retopo.add_subdivision",
            text="Add Subdivision",
            icon='MOD_SUBSURF'
        )

        subdivision_modifier = self.get_modifier(SUBDIVISION_MODIFIER_NAME)

        if subdivision_modifier is not None:

            layout.prop(
                subdivision_modifier,
                "levels",
                text="Subdivision Level"
            )

        layout.separator()

        layout.operator(
            "retopo.apply_modifiers",
            text="Apply Modifiers",
            icon='CHECKMARK'
        )

    # -----------------------------------------------------------

    def get_modifier(self, modifier_name):

        if session.template is None:
            return None

        mesh = session.template.mesh

        if not is_valid(mesh):
            return None

        return mesh.modifiers.get(modifier_name)
