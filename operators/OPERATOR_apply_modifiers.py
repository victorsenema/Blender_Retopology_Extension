import bpy

from ..core import session
from ..core.blender_utils import is_valid
from ..core.fitting.projection import SurfaceProjection


class OPERATOR_apply_modifiers(bpy.types.Operator):

    #
    # Passo final: aplica (finaliza) o modifier Shrinkwrap
    # adicionado por "Apply Mesh" -- ver
    # core/fitting/projection.py:apply_modifier() -- e remove
    # da cena os Empties de critical point (tanto os do template
    # quanto os que o usuário posicionou no Landmarking), já que
    # não servem mais depois que a malha está finalizada.
    #

    bl_idname = "retopo.apply_modifiers"
    bl_label = "Apply Modifiers"
    bl_description = (
        "Finaliza o Shrinkwrap na malha e remove os critical points da cena"
    )

    def execute(self, context):

        if session.template is None or not is_valid(session.template.mesh):

            self.report(
                {'ERROR'},
                "Rode 'Apply Mesh' antes de aplicar os modifiers."
            )

            return {'CANCELLED'}

        mesh = session.template.mesh

        applied = SurfaceProjection.apply_modifier(
            mesh,
            SurfaceProjection.MODIFIER_NAME
        )

        if not applied:

            self.report(
                {'WARNING'},
                "Nenhum modifier Shrinkwrap encontrado pra aplicar."
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
