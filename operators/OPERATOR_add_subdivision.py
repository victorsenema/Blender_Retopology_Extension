import bpy

from ..core import session
from ..core.blender_utils import is_valid
from ..core.fitting import subdivision


class OPERATOR_add_subdivision(bpy.types.Operator):

    #
    # Exclusivamente isso: garante que o modifier Subdivision
    # Surface existe na malha do template, sempre posicionado
    # antes do Shrinkwrap. O nível é ajustado depois direto no
    # campo do painel (ligado no modifier.levels).
    #

    bl_idname = "retopo.add_subdivision"
    bl_label = "Add Subdivision"
    bl_description = (
        "Ativa a Subdivision Surface na malha -- ajuste o nível no "
        "campo abaixo do botão"
    )

    def execute(self, context):

        #
        # resolve_template_mesh() em vez de session.template.mesh:
        # a referência morre num Ctrl+Z e o botão passaria a
        # recusar rodar com a malha visivelmente na cena.
        #

        mesh = session.resolve_template_mesh()

        if not is_valid(mesh):

            self.report(
                {'ERROR'},
                "Rode 'Apply Mesh' antes de adicionar Subdivision."
            )

            return {'CANCELLED'}

        subdivision.add_or_get(mesh)

        self.report(
            {'INFO'},
            "Subdivision ativada -- ajuste 'Subdivision Level'."
        )

        return {'FINISHED'}
