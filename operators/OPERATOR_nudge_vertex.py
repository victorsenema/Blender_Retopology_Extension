import bpy
from bpy_extras import view3d_utils
from mathutils import Vector

from ..core import session
from ..core.blender_utils import is_valid
from ..core.fitting.vertex_control import (
    build_adjacency,
    compute_geodesic_distances,
    default_influence_radius,
    falloff_weights,
    get_control_vertex_indices,
    get_display_positions,
)
from ..ui import vertex_highlight


#
# Ajuste fino pós Apply Mesh: um Proportional Editing (tecla O
# do Edit Mode) que roda em Object Mode e só nos vértices de
# controle -- os que estão nos vertex groups Nose_VG/Face_VG/
# Eyes_VG/Mouth_VG do template, destacados na viewport por
# ui/vertex_highlight.py.
#
# A intenção da ferramenta: deixar o rosto no ponto ANTES de
# cravar os modifiers, pra que a malha finalizada já saia pronta
# pra rig/animação. Por isso o retoque acontece com Shrinkwrap
# (e Subdivision, se houver) ainda vivos no stack -- o que se vê
# arrastando já é o resultado final.
#
# Controles, iguais aos do Blender onde dá:
#
#   clique esquerdo perto de um ponto  -- pega e começa a arrastar
#   arrastar                           -- move no plano da tela (Grab)
#   roda do mouse durante o arraste    -- aumenta/diminui o raio
#   soltar                             -- confirma (empurra um undo)
#   ESC/direito durante o arraste      -- cancela só aquele arraste
#   ESC/direito fora do arraste        -- sai da ferramenta
#
# MOVIMENTO: livre no plano da tela, na profundidade original do
# vértice, exatamente como o Grab (G). Uma primeira versão
# travava o movimento na normal do vértice pra "ajudar" o
# Shrinkwrap, mas ficou pouco intuitivo e quebrava sempre que a
# normal apontava quase direto pra câmera. Como o Shrinkwrap
# (modo PROJECT, ver core/fitting/projection.py) reprojeta ao
# longo da normal recalculada depois de cada mudança, mover livre
# e deixar ele resolver o resultado final é mais simples e mais
# parecido com o Grab de verdade.
#

PICK_RADIUS_PIXELS = 20

#
# Fator multiplicativo por "clique" da roda do mouse -- passo
# proporcional, não fixo, senão o ajuste fica grosso demais em
# raio pequeno e fino demais em raio grande.
#

RADIUS_STEP = 1.15

#
# O Dijkstra roda até um limite MAIOR que o raio atual, e o
# resultado é guardado durante o arraste inteiro. Assim aumentar
# o raio no meio do arraste só reaplica a curva de decaimento em
# cima das distâncias que já temos, sem recalcular nada. Só passa
# a fronteira desse limite é que obriga a refazer as contas.
#

DISTANCE_HEADROOM = 3.0


class OPERATOR_nudge_vertex(bpy.types.Operator):

    bl_idname = "retopo.nudge_vertex"
    bl_label = "Nudge Vertex"
    bl_description = (
        "Arraste os vértices em destaque pra ajustar a malha antes de "
        "aplicar os modifiers. Roda do mouse muda o raio de influência. "
        "ESC/botão direito pra sair"
    )

    # -----------------------------------------------------------

    def invoke(self, context, event):

        if context.area is None or context.area.type != 'VIEW_3D':

            self.report({'ERROR'}, "Execute na View 3D")

            return {'CANCELLED'}

        if session.template is None or not is_valid(session.template.mesh):

            self.report(
                {'ERROR'},
                "Rode 'Apply Mesh' antes de usar o Nudge Vertex."
            )

            return {'CANCELLED'}

        self.mesh_obj = session.template.mesh

        #
        # Em Edit Mode o Blender trabalha num bmesh próprio e
        # ignora silenciosamente qualquer escrita em
        # mesh.data.vertices -- a ferramenta pareceria quebrada
        # sem dar erro nenhum. Melhor barrar na entrada.
        #
        # A checagem é no modo do OBJETO DO TEMPLATE, não em
        # context.mode: esculpir a malha alvo em Sculpt Mode e
        # ajustar o template ao mesmo tempo é inofensivo.
        #

        if self.mesh_obj.mode != 'OBJECT':

            self.report(
                {'ERROR'},
                f"Saia do {self.mesh_obj.mode.title()} Mode do "
                f"'{self.mesh_obj.name}' antes de usar o Nudge Vertex."
            )

            return {'CANCELLED'}

        self.control_indices = get_control_vertex_indices(
            self.mesh_obj,
            verbose=True
        )

        if not self.control_indices:

            self.report(
                {'ERROR'},
                "Nenhum vértice de controle encontrado (vertex groups "
                "Nose_VG/Face_VG/Eyes_VG/Mouth_VG vazios ou ausentes). "
                "Veja o System Console pra detalhes."
            )

            return {'CANCELLED'}

        #
        # Topologia não muda durante a ferramenta -- calcula uma
        # vez só e reaproveita em todos os arrastes.
        #

        self.adjacency = build_adjacency(self.mesh_obj)

        self.radius = context.scene.retopo_nudge_radius

        if self.radius <= 0.0:

            #
            # Primeira vez nessa cena: chuta um raio proporcional
            # ao tamanho da cabeça e escreve de volta na property
            # pra o slider do painel já aparecer preenchido.
            #

            self.radius = default_influence_radius(self.mesh_obj)

            context.scene.retopo_nudge_radius = self.radius

        self.is_dragging = False

        self.seed_index = None
        self.distances = {}
        self.distance_limit = 0.0
        self.weights = {}
        self.original_positions = {}
        self.touched = set()

        self.offset_local = Vector((0.0, 0.0, 0.0))
        self.world_delta = Vector((0.0, 0.0, 0.0))

        self.drag_plane_origin = None
        self.start_mouse_world = None

        self.affect_control_points = (
            context.scene.retopo_nudge_affect_control
        )

        self.display_positions = None

        context.area.header_text_set(
            "Nudge Vertex: arraste os pontos destacados  |  "
            "Roda do mouse: raio  |  ESC/direito: sair"
        )

        vertex_highlight.mark_dirty()
        vertex_highlight.mark_groups_dirty()

        context.area.tag_redraw()

        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    # -----------------------------------------------------------

    def modal(self, context, event):

        if not is_valid(self.mesh_obj):

            self.report({'ERROR'}, "A malha foi removida da cena.")

            return self.finish(context, {'CANCELLED'})

        if self.is_dragging:

            if event.type == 'MOUSEMOVE':

                self.update_drag(context, event)

                context.area.tag_redraw()

                return {'RUNNING_MODAL'}

            #
            # Roda do mouse só é capturada DURANTE o arraste --
            # com a ferramenta parada ela continua fazendo zoom
            # normal, como o usuário espera.
            #

            if event.type == 'WHEELUPMOUSE':

                self.change_radius(context, RADIUS_STEP)

                context.area.tag_redraw()

                return {'RUNNING_MODAL'}

            if event.type == 'WHEELDOWNMOUSE':

                self.change_radius(context, 1.0 / RADIUS_STEP)

                context.area.tag_redraw()

                return {'RUNNING_MODAL'}

            if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':

                self.end_drag(context)

                context.area.tag_redraw()

                return {'RUNNING_MODAL'}

            if event.type in {'RIGHTMOUSE', 'ESC'}:

                self.cancel_drag(context)

                context.area.tag_redraw()

                return {'RUNNING_MODAL'}

            return {'RUNNING_MODAL'}

        #
        # Ocioso -- esperando o próximo clique.
        #

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':

            picked = self.pick_vertex(context, event)

            if picked is not None:

                self.start_drag(context, event, picked)

                context.area.tag_redraw()

            return {'RUNNING_MODAL'}

        if event.type in {'RIGHTMOUSE', 'ESC'}:

            return self.finish(context, {'CANCELLED'})

        return {'PASS_THROUGH'}

    # -----------------------------------------------------------

    def finish(self, context, result):

        #
        # Saída única da ferramenta: limpa o texto do cabeçalho e
        # o círculo de influência, que são estado de UI global e
        # ficariam grudados na tela se a gente só devolvesse
        # CANCELLED.
        #

        if context.area is not None:

            context.area.header_text_set(None)

            context.area.tag_redraw()

        vertex_highlight.set_falloff_preview(None, 0.0)

        return result

    # -----------------------------------------------------------

    def pick_vertex(self, context, event):

        #
        # Mede a distância em pixels usando a posição VISÍVEL do
        # vértice (depois dos modifiers, ver
        # vertex_control.get_display_positions) -- é onde o
        # usuário está enxergando o ponto e, portanto, onde ele
        # vai clicar.
        #

        region = context.region
        rv3d = context.space_data.region_3d

        mouse = Vector((event.mouse_region_x, event.mouse_region_y))

        self.display_positions = get_display_positions(
            self.mesh_obj,
            self.control_indices
        )

        best_index = None
        best_distance = PICK_RADIUS_PIXELS

        for index in self.control_indices:

            world_co = self.display_positions.get(index)

            if world_co is None:
                continue

            screen_co = view3d_utils.location_3d_to_region_2d(
                region,
                rv3d,
                world_co
            )

            if screen_co is None:
                continue

            distance = (screen_co - mouse).length

            if distance < best_distance:

                best_distance = distance
                best_index = index

        return best_index

    # -----------------------------------------------------------

    def start_drag(self, context, event, seed_index):

        self.seed_index = seed_index

        self.affect_control_points = (
            context.scene.retopo_nudge_affect_control
        )

        self.original_positions = {}
        self.touched = set()

        self.rebuild_distances()

        self.rebuild_weights()

        self.offset_local = Vector((0.0, 0.0, 0.0))
        self.world_delta = Vector((0.0, 0.0, 0.0))

        #
        # Âncora do "plano de arraste": a profundidade (em espaço
        # de mundo) do ponto onde o usuário clicou. O mouse é
        # reconvertido pra 3D nessa mesma profundidade a cada
        # MOUSEMOVE -- é assim que o Grab nativo funciona
        # (translada no plano perpendicular à câmera).
        #

        self.drag_plane_origin = self.display_positions[seed_index]

        region = context.region
        rv3d = context.space_data.region_3d

        self.start_mouse_world = view3d_utils.region_2d_to_location_3d(
            region,
            rv3d,
            (event.mouse_region_x, event.mouse_region_y),
            self.drag_plane_origin
        )

        self.is_dragging = True

        self.update_falloff_preview()

    # -----------------------------------------------------------

    def rebuild_distances(self):

        #
        # Distâncias geodésicas a partir do vértice pego, com
        # folga (DISTANCE_HEADROOM) pra aguentar o usuário
        # aumentar o raio no meio do arraste sem refazer conta.
        #
        # Roda sempre com a malha nas posições ORIGINAIS (quem
        # chama no meio de um arraste restaura antes) -- medir
        # distância na malha já deformada faria o raio "respirar"
        # conforme o arraste, o que o Proportional Editing do
        # Blender também não faz.
        #

        self.distance_limit = max(
            self.radius * DISTANCE_HEADROOM,
            self.radius
        )

        self.distances = compute_geodesic_distances(
            self.mesh_obj,
            self.adjacency,
            self.seed_index,
            self.distance_limit
        )

        vertices = self.mesh_obj.data.vertices

        for index in self.distances:

            if index not in self.original_positions:

                self.original_positions[index] = (
                    vertices[index].co.copy()
                )

    # -----------------------------------------------------------

    def rebuild_weights(self):

        self.weights = falloff_weights(
            self.distances,
            self.radius,
            self.control_indices,
            self.seed_index,
            affect_control_points=self.affect_control_points
        )

    # -----------------------------------------------------------

    def change_radius(self, context, factor):

        self.radius = max(self.radius * factor, 1e-6)

        #
        # Mantém o slider do painel em sincronia com o que a roda
        # do mouse fez, e faz o valor sobreviver pro próximo
        # arraste.
        #

        context.scene.retopo_nudge_radius = self.radius

        if self.radius > self.distance_limit:

            #
            # Estourou a folga do Dijkstra: volta a malha ao
            # estado original, recalcula as distâncias com o
            # limite novo, e reaplica o mesmo deslocamento por
            # cima.
            #

            self.restore_originals()

            self.rebuild_distances()

        self.rebuild_weights()

        self.apply_offset()

        self.update_falloff_preview()

    # -----------------------------------------------------------

    def update_drag(self, context, event):

        region = context.region
        rv3d = context.space_data.region_3d

        current_mouse_world = view3d_utils.region_2d_to_location_3d(
            region,
            rv3d,
            (event.mouse_region_x, event.mouse_region_y),
            self.drag_plane_origin
        )

        self.world_delta = current_mouse_world - self.start_mouse_world

        #
        # O deslocamento é medido em mundo (é onde o mouse vive) e
        # convertido pra local só na hora de escrever no vértice
        # -- o template carrega uma escala não uniforme na
        # matrix_world vinda do Alignment.
        #

        self.offset_local = (
            self.mesh_obj.matrix_world.to_3x3().inverted() @
            self.world_delta
        )

        self.apply_offset()

        self.update_falloff_preview()

    # -----------------------------------------------------------

    def apply_offset(self):

        #
        # Reescreve só o que precisa: os vértices que TÊM peso
        # agora, mais os que TINHAM peso na última aplicação
        # (self.touched). Sem essa diferença, diminuir o raio
        # deixaria pra trás os vértices que saíram da zona de
        # influência, congelados no último deslocamento que
        # receberam.
        #

        vertices = self.mesh_obj.data.vertices

        active = set(self.weights)
        active.add(self.seed_index)

        for index in active | self.touched:

            original = self.original_positions.get(index)

            if original is None:
                continue

            if index == self.seed_index:
                weight = 1.0

            else:
                weight = self.weights.get(index, 0.0)

            vertices[index].co = original + self.offset_local * weight

        self.touched = active

        self.mesh_obj.data.update()

        vertex_highlight.mark_dirty()

    # -----------------------------------------------------------

    def restore_originals(self):

        vertices = self.mesh_obj.data.vertices

        for index, original in self.original_positions.items():

            vertices[index].co = original

        self.touched = set()

        self.mesh_obj.data.update()

        vertex_highlight.mark_dirty()

    # -----------------------------------------------------------

    def update_falloff_preview(self):

        #
        # Círculo do raio de influência, igual ao do Proportional
        # Editing: acompanha o mouse no plano de arraste, pra dar
        # noção de quanta malha está sendo puxada junto.
        #

        if self.drag_plane_origin is None:
            return

        vertex_highlight.set_falloff_preview(
            self.drag_plane_origin + self.world_delta,
            self.radius
        )

    # -----------------------------------------------------------

    def end_drag(self, context):

        #
        # Operator modal não registra passo de undo sozinho: sem
        # este push, Ctrl+Z depois de arrastar pularia direto pro
        # estado anterior (o Apply Mesh), jogando fora todos os
        # ajustes de uma vez. Um push por arraste confirmado
        # deixa o Ctrl+Z desfazendo arraste a arraste.
        #

        self.clear_drag()

        bpy.ops.ed.undo_push(message="Nudge Vertex")

        vertex_highlight.mark_dirty()

    # -----------------------------------------------------------

    def cancel_drag(self, context):

        self.restore_originals()

        self.clear_drag()

    # -----------------------------------------------------------

    def clear_drag(self):

        self.is_dragging = False

        self.seed_index = None
        self.distances = {}
        self.distance_limit = 0.0
        self.weights = {}
        self.original_positions = {}
        self.touched = set()

        self.offset_local = Vector((0.0, 0.0, 0.0))
        self.world_delta = Vector((0.0, 0.0, 0.0))

        self.drag_plane_origin = None
        self.start_mouse_world = None

        vertex_highlight.set_falloff_preview(None, 0.0)
