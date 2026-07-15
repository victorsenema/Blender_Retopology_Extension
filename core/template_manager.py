import bpy
import os

from .template import Template


def get_template_path():

    addon_path = os.path.dirname(os.path.dirname(__file__))

    return os.path.join(addon_path, "assets", "Template_Setted_Names.fbx")


def import_template():

    template_path = get_template_path()

    existing_objects = set(bpy.data.objects)

    bpy.ops.import_scene.fbx(filepath=template_path)

    imported_objects = [
        obj for obj in bpy.data.objects
        if obj not in existing_objects
    ]

    template = Template()

    # Guarda todos os objetos pertencentes à template
    template.objects = imported_objects

    for obj in imported_objects:

        if obj.type == 'MESH':

            template.mesh = obj

        elif obj.type == 'EMPTY':

            template.critical_points.append(obj)

    if template.mesh is None:

        raise RuntimeError("Template mesh not found.")

    return template