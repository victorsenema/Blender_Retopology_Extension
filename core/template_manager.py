import bpy
import os

from .template import Template
from .fitting.critical_points import CriticalPoint

#
# Nomes das coleções raiz dentro do .blend do template.
# OBS.: "Strcuture_Critical_Points" está com esse typo no
# arquivo do asset (VG_Template.blend) -- mantido aqui de
# propósito pra bater com o nome real. Se um dia corrigirem o
# nome da coleção no .blend, é só ajustar esta constante.
#

MESH_COLLECTION_NAME = "Template_Mesh"
STRUCTURE_COLLECTION_NAME = "Strcuture_Critical_Points"


def get_template_path():

    addon_path = os.path.dirname(os.path.dirname(__file__))

    return os.path.join(
        addon_path,
        "assets",
        "VG_Template.blend"
    )


def import_template():

    template_path = get_template_path()

    #
    # Carrega só as 2 coleções raiz que interessam (malha e
    # critical points). Carregar por coleção -- em vez de
    # despejar todos os objetos numa lista só -- é o que permite
    # saber depois de onde cada Empty veio.
    #

    with bpy.data.libraries.load(template_path, link=False) as (data_from, data_to):

        wanted = {
            MESH_COLLECTION_NAME,
            STRUCTURE_COLLECTION_NAME,
        }

        data_to.collections = [
            name for name in data_from.collections
            if name in wanted
        ]

    imported_collections = {
        collection.name: collection
        for collection in data_to.collections
        if collection is not None
    }

    #
    # Linka as coleções raiz na cena. Isso traz junto, de forma
    # automática, toda a hierarquia de subcoleções
    # (Left/Neutral/Right) e os objetos dentro delas.
    #

    for collection in imported_collections.values():

        bpy.context.collection.children.link(collection)

    template = Template()

    template.objects = []

    #
    # Malha
    #

    mesh_collection = imported_collections.get(MESH_COLLECTION_NAME)

    if mesh_collection is not None:

        for obj in mesh_collection.all_objects:

            if obj.type == 'MESH':

                template.mesh = obj

                template.objects.append(obj)

    if template.mesh is None:

        raise RuntimeError("Template mesh not found.")

    #
    # Critical Points
    #

    structure_collection = imported_collections.get(STRUCTURE_COLLECTION_NAME)

    if structure_collection is not None:

        for obj in structure_collection.all_objects:

            if obj.type == 'EMPTY':

                template.critical_points.append(CriticalPoint(obj))

                template.objects.append(obj)

    print(
        f"Template importado: "
        f"{len(template.critical_points)} critical points."
    )

    return template
