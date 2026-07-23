import bpy

from .operators.OPERATOR_create_critical_points import OPERATOR_create_critical_points
from .operators.OPERATOR_create_refinement_points import OPERATOR_create_refinement_points
from .operators.OPERATOR_apply_mesh import OPERATOR_apply_mesh
from .operators.OPERATOR_apply_refinement import OPERATOR_apply_refinement
from .operators.OPERATOR_apply_projection import OPERATOR_apply_projection

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
    OPERATOR_create_refinement_points,
    OPERATOR_apply_mesh,
    OPERATOR_apply_refinement,
    OPERATOR_apply_projection,
    RETOPOLOGY_PT_panel,
)


def register():

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()