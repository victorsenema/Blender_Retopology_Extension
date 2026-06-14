from pathlib import Path
import math
from .critical_point import CriticalPoint
import bpy

def get_template_asset():
    addon_dir = Path(__file__).parent.parent
    template_path = addon_dir / "assets" / "Template_02.fbx"
    return template_path

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


def create_anchors(template_asset, critical_points):
    # Create the Anchors
    anchors = []
    for critical_point in critical_points:
        vertex = find_nearest_vertex(template_asset,critical_point.empty.location)
        anchors.append(Anchor(critical_point,vertex))
    return anchors


def assign_weights(template_mesh, anchors):
    # Run the Multi-Source BFS and assign weights
    pass


def instantiate_template(template_asset):
    # Put the template in the scene
    pass


def load_template():
    # Pipeline:
        # Get asset
        # Create CriticalPoints
        # Create Anchors
        # Assign weights
        # Instantiate template
        # Return anchors
    pass