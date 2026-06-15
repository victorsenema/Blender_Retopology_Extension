from pathlib import Path
import math
from .critical_point import CriticalPoint
from .graph_weights import multi_source_BFS_weight_assign
from .anchor import Anchor


#teste
from .session import anchors

import bpy
import bmesh
def get_template_asset():
    addon_dir = Path(__file__).parent.parent
    template_path = addon_dir / "assets" / "Template_02.fbx"

    bpy.ops.import_scene.fbx(filepath=str(template_path))
    template_asset = bpy.context.selected_objects

    return template_asset

def get_template_mesh(template_asset):
    # Get the mesh object from the template
    for obj in template_asset:
        if obj.type == 'MESH':
            return obj

def find_nearest_vertex(template_mesh, point):
    # Find the nearest vertex to a point (the point its the representation of the position of the critical point)
    nearest_vertex = None
    nearest_distance = math.inf

    for vertex in template_mesh.data.vertices:

        world_position = (template_mesh.matrix_world@ vertex.co)

        distance = (world_position - point).length

        if distance < nearest_distance:
            nearest_distance = distance
            nearest_vertex = vertex

    return nearest_vertex

def create_critical_points(template_asset):
    # Create the CriticalPoints
    critical_points = []

    # Getting the emptys to assigns as
    for obj in template_asset:
        if obj.type == 'EMPTY':
            critical_points.append(CriticalPoint(obj))
    return critical_points


def create_anchors(template_mesh, critical_points):
    # Create the Anchors
    anchors = []
    for critical_point in critical_points:
        vertex = find_nearest_vertex(template_mesh,critical_point.empty.location)
        anchors.append(Anchor(critical_point,vertex))
    return anchors


def assign_weights(template_mesh, anchors):
    # Run the Multi-Source BFS and assign weights
    multi_source_BFS_weight_assign(template_mesh,anchors)

def load_template():
    # Pipeline:
        # Get asset
        # Create CriticalPoints
        # Create Anchors
        # Assign weights
        # Instantiate template
        # Return anchors

    # Asset (All objects)
    template_asset = get_template_asset()
    # Mesh 
    template_mesh = get_template_mesh(template_asset)
    # Critical Points
    critical_points = create_critical_points(template_asset)
    # Anchors
    anchors.clear()
    anchors.extend(create_anchors(template_mesh,critical_points))
    # Weights
    assign_weights(template_mesh,anchors)

    return anchors
