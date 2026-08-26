import math

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from ..core import session
from ..core.blender_utils import is_valid
from ..core.fitting.vertex_control import (
    get_control_vertex_indices_by_group,
    get_display_positions,
)


#
# Destaque visual (draw_handler na viewport, POST_VIEW) dos
# vértices de controle (Nose_VG/Face_VG/Eyes_VG/Mouth_VG) depois
# do Apply Mesh, pra ficar claro quais vértices dá pra arrastar
# com o Nudge Vertex (ver operators/OPERATOR_nudge_vertex.py).
# Usa o módulo `gpu` moderno -- NÃO `bgl`, que está removido no
# Blender 5.0.
#
# Cada grupo é desenhado com uma cor diferente -- além de ficar
# mais fácil identificar qual ponto é de qual grupo, ajuda a
# enxergar rápido se algum grupo está com cobertura incompleta na
# malha (ex.: um lado espelhado sem os pesos do vertex group
# copiados).
#
# CACHE: o desenho acontece a cada frame, em cada viewport aberta
# -- inclusive enquanto o usuário só orbita a câmera. Descobrir
# quais vértices são de controle custa varrer a malha inteira
# (vértice x vertex group), e montar o batch da GPU custa
# converter todas as posições. Fazer isso por frame derrubava o
# FPS à toa, já que nada disso muda quando a câmera se move. Então
# o resultado fica em cache e só é refeito quando alguém avisa que
# a malha mudou -- via mark_dirty() (chamado pelo Nudge Vertex a
# cada deslocamento) ou pelo handler de depsgraph (que cobre
# undo, sculpt na malha alvo, mudar o nível de Subdivision, etc.).
#

GROUP_COLORS = {
    "Nose_VG": (1.0, 0.05, 0.55, 1.0),   # rosa
    "Face_VG": (0.1, 0.65, 1.0, 1.0),    # azul claro
    "Eyes_VG": (0.15, 1.0, 0.25, 1.0),   # verde
    "Mouth_VG": (1.0, 0.75, 0.0, 1.0),   # amarelo/laranja
}

DEFAULT_COLOR = (1.0, 0.05, 0.55, 1.0)

OCCLUDED_ALPHA = 0.3
POINT_SIZE = 8.0

FALLOFF_COLOR = (1.0, 1.0, 1.0, 0.85)
FALLOFF_SEGMENTS = 64

_handle = None
_shader = None

#
# Dois caches com tempos de vida diferentes, de propósito:
#
#   _groups  -- quais vértices pertencem a cada vertex group.
#               Descobrir isso custa varrer a malha inteira, e
#               não muda enquanto a malha for a mesma, nem
#               durante um arraste. Só é refeito quando a malha
#               troca ou muda de contagem de vértices.
#
#   _batches -- as POSIÇÕES desenhadas. Essas mudam a cada
#               deslocamento do Nudge, então mark_dirty()
#               invalida só este.
#

_groups = None
_groups_key = None

_batches = None
_batch_key = None

_falloff_center = None
_falloff_radius = 0.0


def _get_shader():

    global _shader

    if _shader is None:
        _shader = gpu.shader.from_builtin('UNIFORM_COLOR')

    return _shader


def mark_dirty():

    #
    # Invalida o cache do destaque. Barato de propósito: só
    # marca: a reconstrução acontece no próximo desenho, então
    # chamar isso várias vezes seguidas (ex.: a cada MOUSEMOVE de
    # um arraste) não custa nada.
    #

    global _batches

    _batches = None


def mark_groups_dirty():

    #
    # Invalida também a lista de quais vértices são de controle.
    # Só faz sentido quando a própria malha muda (Apply Mesh,
    # Apply Modifiers) -- num arraste comum, mark_dirty() basta.
    #

    global _groups

    _groups = None


def set_falloff_preview(center, radius):

    #
    # Círculo do raio de influência mostrado durante um arraste
    # do Nudge Vertex, no espírito do Proportional Editing.
    # center=None apaga.
    #

    global _falloff_center, _falloff_radius

    _falloff_center = center
    _falloff_radius = radius


# -------------------------------------------------------------

def _ensure_groups(mesh_obj):

    global _groups, _groups_key

    key = (mesh_obj.name, len(mesh_obj.data.vertices))

    if _groups is not None and _groups_key == key:
        return _groups

    _groups = get_control_vertex_indices_by_group(mesh_obj)
    _groups_key = key

    return _groups


def _ensure_batches(mesh_obj):

    global _batches, _batch_key

    key = (mesh_obj.name, len(mesh_obj.data.vertices))

    if _batches is not None and _batch_key == key:
        return _batches

    groups = _ensure_groups(mesh_obj)

    wanted = set()

    for indices in groups.values():
        wanted |= indices

    positions = get_display_positions(mesh_obj, wanted)

    shader = _get_shader()

    batches = []

    for name, indices in groups.items():

        if not indices:
            continue

        coordinates = [
            positions[index]
            for index in indices
            if index in positions
        ]

        if not coordinates:
            continue

        batches.append(
            (
                GROUP_COLORS.get(name, DEFAULT_COLOR),
                batch_for_shader(shader, 'POINTS', {"pos": coordinates}),
            )
        )

    _batches = batches
    _batch_key = key

    return _batches


def _draw_falloff(shader):

    if _falloff_center is None or _falloff_radius <= 0.0:
        return

    region_data = getattr(bpy.context, "region_data", None)

    if region_data is None:
        return

    #
    # Círculo desenhado no plano da tela (mesma orientação da
    # câmera), como o do Proportional Editing -- um círculo
    # colado na superfície da malha ficaria escondido pela
    # própria malha na maior parte dos ângulos.
    #

    rotation = region_data.view_rotation

    points = []

    for step in range(FALLOFF_SEGMENTS + 1):

        angle = 2.0 * math.pi * step / FALLOFF_SEGMENTS

        offset = Vector((
            math.cos(angle) * _falloff_radius,
            math.sin(angle) * _falloff_radius,
            0.0,
        ))

        points.append(_falloff_center + (rotation @ offset))

    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": points})

    gpu.state.depth_test_set('NONE')

    shader.bind()
    shader.uniform_float("color", FALLOFF_COLOR)

    batch.draw(shader)


def _draw():

    mesh_obj = session.resolve_template_mesh()

    if not is_valid(mesh_obj):
        return

    batches = _ensure_batches(mesh_obj)

    if not batches:
        return

    shader = _get_shader()

    gpu.state.point_size_set(POINT_SIZE)
    gpu.state.blend_set('ALPHA')
    gpu.state.line_width_set(1.5)

    for color, batch in batches:

        occluded_color = (color[0], color[1], color[2], OCCLUDED_ALPHA)

        #
        # Dois passes -- a malha "engolia" os pontos que caem do
        # lado de dentro/atrás dela (ex.: pontos de dentro do
        # nariz). 1º pass com depth test normal desenha os pontos
        # visíveis, opacos; 2º pass com depth test invertido
        # (GREATER, só onde tem algo NA FRENTE do ponto) desenha
        # os mesmos pontos ocultos, bem mais transparentes -- dá
        # pra ver que eles existem por baixo sem confundir com os
        # visíveis.
        #

        gpu.state.depth_test_set('LESS_EQUAL')

        shader.bind()
        shader.uniform_float("color", color)

        batch.draw(shader)

        gpu.state.depth_test_set('GREATER')

        shader.uniform_float("color", occluded_color)

        batch.draw(shader)

    _draw_falloff(shader)

    gpu.state.blend_set('NONE')
    gpu.state.depth_test_set('NONE')
    gpu.state.line_width_set(1.0)


# -------------------------------------------------------------

@bpy.app.handlers.persistent
def _on_depsgraph_update(scene, depsgraph):

    #
    # Qualquer coisa que mexa na cena invalida o cache das
    # posições desenhadas: undo, mudar o nível da Subdivision,
    # esculpir a malha alvo (que o Shrinkwrap segue), mover o
    # template. Só marca -- a reconstrução é preguiçosa, no
    # próximo desenho.
    #

    mark_dirty()


def register():

    global _handle

    if _handle is None:

        _handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw, (), 'WINDOW', 'POST_VIEW'
        )

    if _on_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:

        bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph_update)


def unregister():

    global _handle

    if _on_depsgraph_update in bpy.app.handlers.depsgraph_update_post:

        bpy.app.handlers.depsgraph_update_post.remove(_on_depsgraph_update)

    if _handle is not None:

        bpy.types.SpaceView3D.draw_handler_remove(_handle, 'WINDOW')

        _handle = None

    set_falloff_preview(None, 0.0)

    mark_dirty()
    mark_groups_dirty()
