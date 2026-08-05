import bpy

from ..core import session
from ..core.blender_utils import is_valid
from ..core.fitting.finalize import apply_all_modifiers


class OPERATOR_apply_modifiers(bpy.types.Operator):

    #
    # Passo final: finaliza TODOS os modifiers na malha (o
    # Shrinkwrap de "Apply Mesh" e o Relax de "Relax Mesh", se
    # estiver ativo -- ver core/fitting/finalize.py) e remove da
    # cena os Empties de critical point (tanto os do template
    # quanto os que o usuário posicionou no Landmarking), já que
    # não servem mais depois que a malha está finalizada.
    #

    bl_idname = "retopo.apply_modifiers"
    bl_label = "Apply Modifiers"
    bl_description = (
        "Finaliza todos os modifiers na malha e remove os critical "
        "points da cena"
    )

    def execute(self, context):

        if session.template is None or not is_valid(session.template.mesh):

            self.report(
                {'ERROR'},
                "Rode 'Apply Mesh' antes de aplicar os modifiers."
            )

            return {'CANCELLED'}

        mesh = session.template.mesh

        applied = apply_all_modifiers(mesh)

        if not applied:

            self.report(
                {'WARNING'},
                "Nenhum modifier encontrado pra aplicar."
            )

        removed = 0

        all_points = (
            list(session.template.critical_points) +
            list(session.critical_points)
        )

        for critical_point in all_points:

            if is_valid(critical_point.empty):

                bpy.data.objects.remove(
                    critical_point.empty,
                    do_unlink=True
                )

                removed += 1

        session.template.critical_points.clear()
        session.critical_points.clear()

        self.report(
            {'INFO'},
            f"Modifiers aplicados, {removed} critical points removidos."
        )

        return {'FINISHED'}
