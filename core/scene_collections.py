import bpy


#
# Todas as coleções que o addon cria ou importa ficam debaixo de
# uma raiz só, "Retopology". Antes cada rodada despejava as
# coleções do template (Template_Mesh, Strcuture_Critical_Points)
# e os Empties do usuário direto na coleção ativa da cena, o que
# dava dois problemas:
#
#   1. Lixo acumulado. Depois do Apply Mesh os Empties eram
#      apagados mas a coleção vazia ficava; rodar o addon de novo
#      no mesmo arquivo empilhava Strcuture_Critical_Points.001,
#      .002, e assim por diante.
#
#   2. Referência morta. Os critical points do usuário só viviam
#      como referências Python em core/session.py. Um Ctrl+Z
#      apagava os Empties da cena e a lista continuava apontando
#      pra eles -- daí o erro "Faltam pontos obrigatórios no lado
#      do usuário". Com os pontos numa coleção conhecida, dá pra
#      RECONSTRUIR a lista a partir da cena a qualquer momento,
#      que é o que operators/OPERATOR_test_inside_nose_and_
#      nostrils.py faz antes de rodar o Fitting.
#
# Estrutura montada aqui:
#
#   Scene Collection
#   └── Retopology
#       ├── Retopo_Critical_Points   (Empties do usuário)
#       ├── Template_Mesh            (vinda do VG_Template.blend)
#       └── Strcuture_Critical_Points (idem)
#

ROOT_NAME = "Retopology"

USER_POINTS_NAME = "Retopo_Critical_Points"


def _is_in_scene(scene, collection):

    if collection is scene.collection:
        return True

    return collection in set(scene.collection.children_recursive)


def get_root(context=None, create=True):

    #
    # A coleção raiz do addon, criada e linkada na cena se ainda
    # não existir. Reaproveita uma raiz já existente pelo nome --
    # rodar o addon duas vezes no mesmo arquivo não deve criar
    # "Retopology.001".
    #

    context = context or bpy.context

    scene = context.scene

    collection = bpy.data.collections.get(ROOT_NAME)

    if collection is None:

        if not create:
            return None

        collection = bpy.data.collections.new(ROOT_NAME)

    if not _is_in_scene(scene, collection):

        scene.collection.children.link(collection)

    return collection


def get_user_points(context=None, create=True):

    #
    # Coleção dos Empties que o usuário posiciona no Landmarking.
    #

    collection = bpy.data.collections.get(USER_POINTS_NAME)

    if collection is None:

        if not create:
            return None

        collection = bpy.data.collections.new(USER_POINTS_NAME)

    if not create:

        #
        # Consulta somente-leitura (ex.: a limpeza depois do Apply
        # Mesh, o handler de simetria) -- devolve o que existe sem
        # criar raiz nem mexer em hierarquia.
        #

        return collection

    root = get_root(context, create=True)

    if collection.name not in root.children:

        #
        # Pode estar linkada em outro lugar (usuário arrastou na
        # Outliner, arquivo antigo, etc.) -- desliga de onde
        # estiver antes de pendurar na raiz, senão a coleção
        # apareceria em dois lugares.
        #

        for parent in bpy.data.collections:

            if collection.name in parent.children:
                parent.children.unlink(collection)

        scene_collection = (context or bpy.context).scene.collection

        if collection.name in scene_collection.children:
            scene_collection.children.unlink(collection)

        root.children.link(collection)

    return collection


def clear_objects(collection):

    #
    # Remove da cena (e do arquivo) todo objeto da coleção.
    # Usado no começo de um novo Landmarking: os critical points
    # da rodada anterior não servem mais, e deixá-los faria o
    # Blender renomear os novos pra "NoseTip.001".
    #

    if collection is None:
        return 0

    removed = 0

    for obj in list(collection.objects):

        bpy.data.objects.remove(obj, do_unlink=True)

        removed += 1

    return removed


def purge_if_empty(collection):

    #
    # Apaga a coleção se ela não tiver mais nada dentro. Nunca
    # apaga coleção com objeto ou subcoleção -- é o que garante
    # que a malha finalizada de uma rodada anterior (que mora em
    # Template_Mesh) nunca seja levada junto na limpeza.
    #

    if collection is None:
        return False

    try:

        if collection.objects or collection.children:
            return False

    except ReferenceError:

        #
        # Já removida por outro caminho (Undo, o usuário apagou na
        # Outliner) -- nada a fazer.
        #

        return False

    bpy.data.collections.remove(collection)

    return True
