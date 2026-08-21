import bpy
from bpy.app.handlers import persistent

from ..blender_utils import normalize_point_name
from .. import scene_collections
from .symmetry import (
    get_mirror_name,
    is_neutral,
    mirror_world_position,
    snap_world_position,
)


#
# Mantém os critical points do usuário LINKADOS depois que o
# Landmarking termina: mover JawLeft na viewport move JawRight
# junto, e vice-versa; e um ponto do meio da face não sai do plano
# de simetria por mais que se arraste.
#
# Antes a simetria só existia durante a ferramenta modal -- assim
# que ela fechava, os pontos viravam Empties soltos e qualquer
# ajuste manual quebrava a simetria em silêncio, bem no ponto do
# pipeline em que ela mais importa (o TPS interpola EXATO nos
# landmarks, então um par assimétrico entorta o rosto inteiro).
#
# Funciona por handler de depsgraph_update_post: o Blender avisa
# quais objetos foram transformados, e a gente corrige o par.
#
# POR QUE REFLEXÃO PURA, SEM REPROJETAR NA MALHA:
# o operator do Landmarking reprojeta o gêmeo na superfície
# (ponto mais próximo) na hora de posicionar. Aqui não dá pra
# fazer isso, e o motivo é estabilidade, não preguiça. Reflexão é
# uma involução EXATA -- mirror(mirror(p)) == p -- então depois de
# corrigir o par, o update que isso gera encontra tudo já no lugar
# e o ciclo morre na primeira comparação. Com reprojeção no meio,
# reproject(mirror(reproject(mirror(p)))) != p: cada correção
# geraria uma correção ligeiramente diferente, e os dois pontos
# ficariam se empurrando de frame em frame. O mesmo vale pro snap
# dos pontos neutros, que também é idempotente.
#

EPSILON = 1e-5

_busy = False

_suspended = False


def suspend():

    #
    # Desliga o link enquanto o Landmarking modal está rodando --
    # lá o operator já posiciona os dois lados por conta própria,
    # E reprojeta o gêmeo na malha. Sem isso, o handler puxaria o
    # gêmeo de volta pra reflexão pura, desfazendo a reprojeção a
    # cada movimento do mouse.
    #

    global _suspended

    _suspended = True


def resume():

    global _suspended

    _suspended = False


def _set_location(obj, wanted):

    #
    # Só escreve se a diferença for relevante. Esta comparação é
    # o que impede o vai-e-vem: corrigir B gera um update de B,
    # que faz o handler recalcular A -- e aí A já está no lugar
    # certo, nada é escrito, e a cadeia para.
    #

    current = obj.location

    if (
        abs(current[0] - wanted[0]) < EPSILON and
        abs(current[1] - wanted[1]) < EPSILON and
        abs(current[2] - wanted[2]) < EPSILON
    ):
        return False

    obj.location = wanted

    return True


def _find_by_key(collection, key):

    #
    # Os Empties podem ter sufixo (".001") se sobrou alguma coisa
    # de outra rodada, então a busca é pelo nome normalizado --
    # o mesmo critério que alignment.py e structure_warp.py usam
    # pra casar template com usuário.
    #

    for obj in collection.objects:

        if normalize_point_name(obj.name) == key:
            return obj

    return None


@persistent
def _on_depsgraph_update(scene, depsgraph):

    global _busy

    if _busy or _suspended:
        return

    if not getattr(scene, "retopo_symmetric", False):
        return

    target = scene.retopo_target

    if target is None:
        return

    collection = scene_collections.get_user_points(create=False)

    if collection is None or not collection.objects:
        return

    moved = []

    for update in depsgraph.updates:

        if not update.is_updated_transform:
            continue

        id_data = update.id

        if not isinstance(id_data, bpy.types.Object):
            continue

        original = id_data.original

        if original.name not in collection.objects:
            continue

        moved.append(original)

    if not moved:
        return

    matrix = target.matrix_world
    matrix_inv = matrix.inverted()

    axis = scene.retopo_mirror_axis

    _busy = True

    try:

        handled = set()

        for obj in moved:

            key = normalize_point_name(obj.name)

            if key in handled:
                continue

            if is_neutral(key):

                _set_location(
                    obj,
                    snap_world_position(
                        matrix,
                        matrix_inv,
                        tuple(obj.location),
                        axis
                    )
                )

                handled.add(key)

                continue

            partner_key = get_mirror_name(key)

            if partner_key is None:
                continue

            partner = _find_by_key(collection, partner_key)

            if partner is None:
                continue

            _set_location(
                partner,
                mirror_world_position(
                    matrix,
                    matrix_inv,
                    tuple(obj.location),
                    axis
                )
            )

            #
            # Os dois já foram resolvidos por este movimento. Se o
            # Blender reportar o par inteiro como movido no mesmo
            # update (acontece ao mover os dois selecionados de
            # uma vez), marcar o parceiro evita que ele "responda"
            # e desfaça o que acabou de ser feito.
            #

            handled.add(key)
            handled.add(partner_key)

    finally:

        _busy = False


def register():

    if _on_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:

        bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph_update)


def unregister():

    if _on_depsgraph_update in bpy.app.handlers.depsgraph_update_post:

        bpy.app.handlers.depsgraph_update_post.remove(_on_depsgraph_update)

    resume()
