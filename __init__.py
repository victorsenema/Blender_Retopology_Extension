import bpy

from .operators.OPERATOR_create_critical_points import OPERATOR_create_critical_points
from .operators.OPERATOR_test_inside_nose_and_nostrils import OPERATOR_test_inside_nose_and_nostrils
from .operators.OPERATOR_add_subdivision import OPERATOR_add_subdivision
from .operators.OPERATOR_relax_mesh import OPERATOR_relax_mesh
from .operators.OPERATOR_apply_modifiers import OPERATOR_apply_modifiers

from .ui.panel import RETOPOLOGY_PT_panel


bl_info = {
    "name": "Retopology",
    "author": "Victor Gava",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Retopology",
    "description": "Semi-automatic facial retopology.",
    "category": "Mesh",
}


classes = (
    OPERATOR_create_critical_points,
    OPERATOR_test_inside_nose_and_nostrils,
    OPERATOR_add_subdivision,
    OPERATOR_relax_mesh,
    OPERATOR_apply_modifiers,
    RETOPOLOGY_PT_panel,
)


def register():

    for cls in classes:
        bpy.utils.register_class(cls)

    #
    # Scene.retopo_target: dropper (PointerProperty nativo do
    # Blender, com o ícone de conta-gotas) pra escolher a malha
    # esculpida onde o template vai ser colado via Shrinkwrap.
    # Ver operators/OPERATOR_test_inside_nose_and_nostrils.py.
    #

    bpy.types.Scene.retopo_target = bpy.props.PointerProperty(
        name="Target Mesh",
        description=(
            "Malha esculpida onde o template será colado (Shrinkwrap)"
        ),
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH',
    )


def unregister():

    del bpy.types.Scene.retopo_target

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
