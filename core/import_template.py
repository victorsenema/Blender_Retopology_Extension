from pathlib import Path
import bpy
import bmesh
from ..core.utils import find_nearest_vertex
from ..core.anchor import Anchor, anchors
from ..core.graph import bfs_distances
from ..core.weights import calculate_weight

class RETOPO_OT_import_template(bpy.types.Operator):
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

            bm = bmesh.new()
            bm.from_mesh(mesh_obj.data)

            bm.verts.ensure_lookup_table()

            anchor_vertex = bm.verts[vertex_index]

            distances = bfs_distances(anchor_vertex)

            weights = {}

            for v_index, distance in distances.items():

                weights[v_index] = calculate_weight(
                    distance
                )

            anchors.append(
                Anchor(
                    empty_obj,
                    mesh_obj,
                    vertex_index,
                    weights
                )
            )

        return {'FINISHED'}