from ..core.anchor import Anchor, anchors
from pathlib import Path
import bpy

from ..core.anchor import Anchor

class RETOPO_OT_import_template(
    bpy.types.Operator
):
    bl_idname = "retopo.import_template"
    bl_label = "Import Template"

    def execute(self, context):

        addon_dir = Path(__file__).parent.parent

        fbx_path = addon_dir / "assets" / "Test_Template.fbx"

        bpy.ops.import_scene.fbx(
            filepath=str(fbx_path)
        )

        mesh_obj = None
        empty_obj = None

        for obj in context.selected_objects:

            if obj.type == 'MESH':
                mesh_obj = obj

            elif obj.type == 'EMPTY':
                empty_obj = obj

        if mesh_obj and empty_obj:

            vertex_index = find_nearest_vertex(
                mesh_obj,
                empty_obj.location
            )

            anchors.append(
                Anchor(
                    empty_obj,
                    mesh_obj,
                    vertex_index
                )
            )

        return {'FINISHED'}