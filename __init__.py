import bpy

#panel
from .ui.panel import RETOPO_PT_panel

#operators
from .operators.OPERATOR_load_template import OPERATOR_load_template

#handlers
from .handlers.HANDLER_anchor import anchor_handler

bl_info = {
    "name": "Retopo Template",
    "author": "Gava",
    "version": (0, 0, 1),
    "blender": (4, 0, 0),
    "category": "Mesh",
}

classes = (
    RETOPO_PT_panel,
    OPERATOR_load_template,
)

def register():

    #classes
    for cls in classes:
        bpy.utils.register_class(cls)

    #handlers
    if anchor_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(
            anchor_handler
        )

def unregister():
    #classes
    if anchor_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(
            anchor_handler
        )
        
    #handlers
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)