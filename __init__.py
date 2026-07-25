import bpy

from .operators.OPERATOR_create_critical_points import OPERATOR_create_critical_points
from .operators.OPERATOR_apply_mesh import OPERATOR_apply_mesh

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
    OPERATOR_apply_mesh,
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
