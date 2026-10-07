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

        #
        # O alvo vem do dropper do painel, que é a fonte oficial
        # (session.target_mesh pode estar vazio depois de um
        # reload). É ele que o Shrinkwrap pós-Subdivision precisa.
        #

        subdivision.add_or_get(mesh, target=context.scene.retopo_target)

        self.report(
            {'INFO'},
            "Subdivision ativada -- ajuste 'Subdivision Level'."
        )

        if context.scene.retopo_target is None:

            self.report(
                {'WARNING'},
                "Sem Target: a malha vai descolar nas partes convexas. "
                "Escolha o Target e clique em Add Subdivision de novo."
            )

        return {'FINISHED'}
