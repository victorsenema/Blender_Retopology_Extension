bl_info = {
    "name": "Retopo Template",
    "author": "Victor",
    "version": (0, 0, 1),
    "blender": (4, 0, 0),
    "category": "Mesh",
}

import bpy

from .ui.panel import RETOPO_PT_panel

from .operators.create_test_mesh import (
    RETOPO_OT_create_test_mesh
)

from .operators.create_control import (
    RETOPO_OT_create_control
)

from .core.import_template import (
    RETOPO_OT_import_template
)

from .handlers.depsgraph_handler import (
    anchor_handler
)

classes = (
    RETOPO_PT_panel,
    RETOPO_OT_create_test_mesh,
    RETOPO_OT_create_control,
    RETOPO_OT_import_template,
)

def register():

    for cls in classes:
        bpy.utils.register_class(cls)

    if anchor_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(
            anchor_handler
        )

def unregister():

    if anchor_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(
            anchor_handler
        )

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()