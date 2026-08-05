import bpy

from ..core import session
from ..core.blender_utils import is_valid
from ..core.fitting import relax


class OPERATOR_relax_mesh(bpy.types.Operator):

    #
    # Exclusivamente isso: garante que o modifier de relaxamento
    # (Corrective Smooth) existe na malha do template. Não toca
    # no Shrinkwrap, não aplica nada, não remove critical
    # points. A intensidade é ajustada depois direto no slider
    # do painel (ligado no modifier.factor).
    #

    bl_idname = "retopo.relax_mesh"
    bl_label = "Relax Mesh"
    bl_description = (
        "Ativa o relaxamento (Corrective Smooth) na malha -- ajuste "
        "a intensidade no slider abaixo do botão"
    )

    def execute(self, context):

        if session.template is None or not is_valid(session.template.mesh):

            self.report(
                {'ERROR'},
                "Rode 'Apply Mesh' antes de relaxar."
            )

            return {'CANCELLED'}

        relax.add_or_get(session.template.mesh)

        self.report(
            {'INFO'},
            "Relaxamento ativado -- ajuste o slider 'Relax Amount'."
        )

        return {'FINISHED'}
