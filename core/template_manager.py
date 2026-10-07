import bpy
import os

from . import scene_collections
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

    requested_names = ()

    with bpy.data.libraries.load(template_path, link=False) as (data_from, data_to):

        wanted = {
            MESH_COLLECTION_NAME,
            STRUCTURE_COLLECTION_NAME,
        }

        #
        # TUPLA, e a atribuição leva uma CÓPIA. Isso não é estilo,
        # é obrigatório.
        #
        # Ao sair deste `with`, o Blender substitui os itens de
        # data_to.collections IN PLACE pelos datablocks
        # carregados -- na mesma lista que foi atribuída aqui.
        # Atribuir `requested_names` direto significaria que
        # `requested_names` para de conter strings e passa a
        # conter Collections, sem aviso nenhum. Foi exatamente
        # isso que aconteceu: o zip lá embaixo casava Collection
        # com Collection, o dict ficava indexado por objeto em vez
        # de nome, e o import morria com "Template mesh not
        # found" mesmo com o .blend intacto.
        #

        requested_names = tuple(
            name for name in data_from.collections
            if name in wanted
        )

        data_to.collections = list(requested_names)

    #
    # As coleções carregadas vêm NA MESMA ORDEM dos nomes pedidos,
    # e é por essa ordem que elas são identificadas aqui.
    #
    # Não dá pra montar este dict com {collection.name: collection}
    # e consultar por MESH_COLLECTION_NAME: na SEGUNDA rodada
    # dentro do mesmo arquivo, com uma "Template_Mesh" já
    # existindo, o Blender nomeia a recém-importada como
    # "Template_Mesh.001" e a busca pelo nome original não acha
    # nada.
    #

    imported_collections = {}

    for original_name, collection in zip(requested_names, data_to.collections):

        if collection is not None:
            imported_collections[original_name] = collection

    print(
        f"[Template] coleções importadas: "
        f"{ {name: collection.name for name, collection in imported_collections.items()} }"
    )

    #
    # Tudo do addon mora debaixo da raiz "Retopology" (ver
    # core/scene_collections.py), não na coleção ativa da cena -- assim
    # o que é do addon fica separado do que é do usuário, e a
    # limpeza depois do Apply Mesh sabe exatamente o que pode
    # apagar.
    #
    # Linkar as coleções raiz traz junto, de forma automática,
    # toda a hierarquia de subcoleções (Left/Neutral/Right) e os
    # objetos dentro delas.
    #

    root = scene_collections.get_root()

    for collection in imported_collections.values():

        root.children.link(collection)

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

        #
        # Mensagem com contexto suficiente pra diagnosticar sem
        # abrir o .blend: qual arquivo, o que foi pedido, e o que
        # de fato veio. A versão anterior dizia só "Template mesh
        # not found", que não distingue ".blend sem a coleção" de
        # "bug no código de import".
        #

        raise RuntimeError(
            f"Template mesh not found. Arquivo: {template_path}. "
            f"Coleções pedidas: {list(requested_names)}. "
            f"Coleções carregadas: {sorted(imported_collections)}. "
            f"Esperado: uma coleção '{MESH_COLLECTION_NAME}' com pelo "
            f"menos um objeto do tipo MESH dentro."
        )

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
