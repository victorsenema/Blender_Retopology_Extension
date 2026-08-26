import bpy
from bpy_extras import view3d_utils
from mathutils import Vector

from ..core import session
from ..core.blender_utils import is_valid, normalize_point_name
from ..core.fitting.modifier_stack import SHRINKWRAP_MODIFIER_NAME
from ..core.fitting.surface_snap import (
    SurfaceSnapper,
    bake_evaluated_positions,
)
from ..core.fitting.symmetry import (
    build_mirror_map,
    mirror_world_direction,
)
from ..core.fitting.vertex_control import (
    build_adjacency,
    compute_geodesic_distances,
    default_influence_radius,
    falloff_weights,
    get_control_vertex_indices,
    get_display_positions,
    has_topology_changing_modifier,
    mean_edge_length,
    world_positions,
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

#
# Tolerância do pareamento de vértices espelhados, como fração do
# comprimento médio de aresta. Tem que ser bem menor que o
# espaçamento da malha (senão um vértice pareia com o vizinho do
# vizinho) e maior que a assimetria residual que o warp TPS deixa
# (senão metade da malha fica sem par).
#

MIRROR_TOLERANCE_FACTOR = 0.25

#
# Distância máxima de busca do snap na superfície, como fração do
# tamanho do alvo. Generoso: o vértice já nasce em cima da malha,
# então esse limite só existe pra não grudar em nada absurdo caso
# alguma coisa dê muito errado.
#

SNAP_LIMIT_FACTOR = 0.1

#
# Quantos arrastes o desfazer da própria ferramenta guarda. Cada
# entrada é um dicionário com as posições anteriores dos vértices
# que aquele arraste mexeu, então o custo é proporcional ao raio
# usado, não à malha inteira.
#

HISTORY_LIMIT = 64


class OPERATOR_nudge_vertex(bpy.types.Operator):

    bl_idname = "retopo.nudge_vertex"
    bl_label = "Nudge Vertex"
    bl_description = (
        "Arraste os vértices em destaque pra ajustar a malha antes de "
        "aplicar os modifiers. Roda do mouse muda o raio de influência. "
        "ESC/botão direito pra sair"
    )

    #
    # Ver o comentário equivalente em
    # OPERATOR_create_critical_points: chamar ed.undo_push() de
    # dentro de um modal em execução derrubou o Blender (crash em
    # collection_parents_rebuild_recursive ao decodificar o undo).
    # Quem empurra o passo agora é o Blender, no fim da
    # ferramenta.
    #
    # Custo: Ctrl+Z desfaz a sessão inteira de Nudge, não arraste
    # a arraste. Dentro da ferramenta, ESC/botão direito durante
    # um arraste continua cancelando aquele arraste.
    #

    bl_options = {'REGISTER', 'UNDO'}

    # -----------------------------------------------------------

    def invoke(self, context, event):

        if context.area is None or context.area.type != 'VIEW_3D':

            self.report({'ERROR'}, "Execute na View 3D")

            return {'CANCELLED'}

        self.mesh_obj = session.resolve_template_mesh()

        if not is_valid(self.mesh_obj):

            self.report(
                {'ERROR'},
                "Rode 'Apply Mesh' antes de usar o Nudge Vertex."
            )

            return {'CANCELLED'}

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

        self.report_context()

        #
        # Topologia não muda durante a ferramenta -- calcula uma
        # vez só e reaproveita em todos os arrastes.
        #

        self.adjacency = build_adjacency(self.mesh_obj)

        self.snapper = None
        self.shrinkwrap = None
        self.shrinkwrap_was_visible = False

        self.setup_surface_snap(context)

        self.mirror_map = None
        self.mirror_matrix = None
        self.mirror_matrix_inv = None
        self.mirror_axis = None

        #
        # DEPOIS do snap, nunca antes: setup_surface_snap() crava o
        # resultado do Shrinkwrap na malha base, ou seja, move
        # todos os vértices. O pareamento espelhado é geométrico
        # (ver symmetry.build_mirror_map), então tem que ser feito
        # sobre as posições que o usuário vai realmente editar --
        # a malha já grudada no alvo -- e não sobre a gaiola de
        # antes, que pode ser bem menos simétrica.
        #

        if context.scene.retopo_symmetric:
            self.setup_mirror(context)

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

        #
        # O diagnóstico do primeiro arraste (ver
        # report_drag_result) roda uma vez por sessão da
        # ferramenta -- o suficiente pra explicar "não estou
        # conseguindo mexer", sem virar spam no console.
        #

        self.debug_reported = False
        self.evaluated_before = None

        #
        # Desfazer PRÓPRIO da ferramenta: uma pilha de fotos das
        # posições anteriores, uma por arraste confirmado.
        #
        # Por que não usar o undo do Blender: empurrar passo de
        # undo de dentro de um modal derrubou o Blender antes (ver
        # o comentário em bl_options). E deixar o Ctrl+Z passar
        # direto pro Blender era pior ainda -- o undo global
        # recarrega o arquivo da memória, mata a referência da
        # malha que este operator guarda, e os marcadores somem.
        # Era exatamente esse o sintoma relatado.
        #

        self.history = []

        header = (
            "Nudge Vertex: arraste os pontos destacados  |  "
            "Roda do mouse: raio  |  Ctrl+Z: desfazer arraste  |  "
            "ESC/direito: sair"
        )

        if self.mirror_map is not None:

            header = (
                f"Nudge Vertex [simetria {self.mirror_axis}]: arraste "
                f"os pontos destacados  |  Roda do mouse: raio  |  "
                f"Ctrl+Z: desfazer arraste  |  ESC/direito: sair"
            )

        context.area.header_text_set(header)

        vertex_highlight.mark_dirty()
        vertex_highlight.mark_groups_dirty()

        context.area.tag_redraw()

        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    # -----------------------------------------------------------

    def modal(self, context, event):

        if not is_valid(self.mesh_obj):

            #
            # Chegar aqui ficou raro: o Ctrl+Z dentro da viewport é
            # interceptado logo abaixo e nunca vira undo global.
            # Ainda dá pra acontecer se o undo for disparado de
            # outra área do Blender -- aí o arquivo é recarregado
            # da memória e TODAS as referências desta sessão
            # (malha, alvo avaliado, modifier) morrem de uma vez.
            #
            # Curar só a malha deixaria o snapper e o shrinkwrap
            # apontando pra lixo. Melhor sair limpo e pedir pra
            # reabrir do que seguir com meio estado consertado.
            #

            self.report(
                {'WARNING'},
                "A malha foi recarregada (Undo em outra área?). Reabra "
                "o Nudge Vertex."
            )

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

        if event.value == 'PRESS' and (
            event.type == 'BACK_SPACE' or
            (event.type == 'Z' and event.ctrl)
        ):

            #
            # CONSUMIR este evento é metade da correção: sem isso
            # ele cai no PASS_THROUGH lá embaixo, o undo do Blender
            # roda no meio da ferramenta e leva embora a sessão de
            # ajuste inteira.
            #

            if event.type == 'Z' and event.shift:

                self.report(
                    {'INFO'},
                    "Refazer não está disponível dentro do Nudge."
                )

            else:
                self.undo_last_drag()

            context.area.tag_redraw()

            return {'RUNNING_MODAL'}

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

        self.restore_shrinkwrap()

        vertex_highlight.set_falloff_preview(None, 0.0)

        return result

    # -----------------------------------------------------------

    def setup_surface_snap(self, context):

        #
        # Troca o "empurrar a gaiola e deixar o Shrinkwrap
        # recalcular" por "mover o vértice de verdade e grudar na
        # superfície", que é como ferramenta de retopologia
        # funciona -- e é o que acaba com os saltos (ver o
        # comentário no topo de core/fitting/surface_snap.py).
        #
        # Três passos, todos aqui:
        #   1. crava na malha base o resultado que o Shrinkwrap já
        #      está mostrando -- assim entrar na ferramenta não
        #      muda NADA na tela;
        #   2. desliga o Shrinkwrap enquanto a ferramenta roda,
        #      pra ele não brigar com o arraste (restaurado no
        #      finish);
        #   3. monta o snapper que vai regrudar cada vértice
        #      movido, por ponto mais próximo.
        #

        target = context.scene.retopo_target

        if target is None or not is_valid(target) or target.type != 'MESH':

            self.report(
                {'WARNING'},
                "Sem Target: o Nudge vai mover livre, sem grudar na "
                "superfície."
            )

            return

        if has_topology_changing_modifier(self.mesh_obj):

            #
            # Com Subdivision no stack não existe correspondência
            # de índice entre a malha base e a avaliada, então não
            # dá pra cravar o resultado nem saber onde cada
            # vértice de controle foi parar. O pipeline já
            # recomenda ajustar ANTES de subdividir.
            #

            self.report(
                {'WARNING'},
                "Subdivision ativa: desligue-a pra ajustar. O ajuste "
                "fino vem antes de subdividir."
            )

            return

        modifier = self.mesh_obj.modifiers.get(SHRINKWRAP_MODIFIER_NAME)

        if modifier is not None and modifier.show_viewport:

            if not bake_evaluated_positions(
                self.mesh_obj,
                context.evaluated_depsgraph_get()
            ):

                self.report(
                    {'WARNING'},
                    "Não foi possível cravar o resultado dos modifiers "
                    "na malha -- Nudge sem snap."
                )

                return

            self.shrinkwrap = modifier
            self.shrinkwrap_was_visible = True

            modifier.show_viewport = False

            print(
                "[Nudge] resultado do Shrinkwrap cravado na malha base; "
                "modifier desligado durante o ajuste."
            )

        size = max(target.dimensions)

        self.snapper = SurfaceSnapper(
            target,
            context.evaluated_depsgraph_get(),
            size * SNAP_LIMIT_FACTOR if size > 0.0 else 0.1
        )

    # -----------------------------------------------------------

    def restore_shrinkwrap(self):

        #
        # Devolve o modifier ao estado em que estava. Como a malha
        # base agora está exatamente em cima da superfície, religar
        # o Shrinkwrap é praticamente inócuo -- mas mexer no stack
        # do usuário e não desfazer seria surpresa desnecessária.
        #

        if self.shrinkwrap is None:
            return

        try:
            self.shrinkwrap.show_viewport = self.shrinkwrap_was_visible

        except ReferenceError:
            pass

        self.shrinkwrap = None

    # -----------------------------------------------------------

    def setup_mirror(self, context):

        #
        # Pareia cada vértice com o do outro lado, pra que arrastar
        # um mova os dois -- inclusive os vizinhos, cada um com o
        # mesmo peso do seu correspondente. É a mesma simetria dos
        # critical points, mas os vértices não têm nome: o par sai
        # da geometria (ver symmetry.build_mirror_map).
        #
        # Mesmo plano do resto do addon: o plano LOCAL do objeto
        # alvo, no eixo escolhido no painel.
        #

        target = context.scene.retopo_target

        if target is None or not is_valid(target):

            self.report(
                {'WARNING'},
                "'Objeto Espelhado' está ligado mas não há Target: o "
                "Nudge não vai espelhar."
            )

            return

        spacing = mean_edge_length(self.mesh_obj)

        if spacing <= 0.0:
            return

        matrix = target.matrix_world.copy()
        matrix_inv = target.matrix_world.inverted()
        axis = context.scene.retopo_mirror_axis

        positions = world_positions(self.mesh_obj)

        mapping = build_mirror_map(
            positions,
            matrix,
            matrix_inv,
            axis,
            spacing * MIRROR_TOLERANCE_FACTOR
        )

        coverage = len(mapping) / len(positions) if positions else 0.0

        print(
            f"[Nudge] simetria: eixo {axis} de '{target.name}', "
            f"{len(mapping)}/{len(positions)} vértices pareados "
            f"({coverage * 100:.0f}%), tolerância "
            f"{spacing * MIRROR_TOLERANCE_FACTOR:.5f}."
        )

        if not mapping:

            self.report(
                {'WARNING'},
                "Nenhum vértice espelhado encontrado -- a malha não "
                "está simétrica em relação ao Target. Nudge sem "
                "simetria."
            )

            return

        if coverage < 0.5:

            #
            # Cobertura baixa quase sempre significa que os
            # landmarks foram colocados assimétricos, e o warp TPS
            # levou a malha junto. Vale avisar em vez de espelhar
            # metade do rosto em silêncio.
            #

            self.report(
                {'WARNING'},
                f"Só {coverage * 100:.0f}% dos vértices têm par "
                f"espelhado. A malha está torta em relação ao plano "
                f"de simetria."
            )

        self.mirror_map = mapping
        self.mirror_matrix = matrix
        self.mirror_matrix_inv = matrix_inv
        self.mirror_axis = axis

    # -----------------------------------------------------------

    def report_context(self):

        #
        # Diz no console EM QUE objeto a ferramenta vai mexer, e
        # avisa se existe mais de uma malha com o mesmo nome-base
        # na cena.
        #
        # Motivo: rodar o addon duas vezes no mesmo arquivo deixa
        # uma "Template_Mesh" e uma "Template_Mesh.001"
        # sobrepostas, no mesmo lugar. A ferramenta mexe na do
        # session (a nova), mas o que se enxerga na viewport pode
        # ser a antiga -- e o sintoma é exatamente "os vértices
        # não estão se movendo mais". Sem esta mensagem, isso não
        # tem como ser diagnosticado olhando a tela. Use o botão
        # "Reset (limpar cena)" do painel pra resolver.
        #

        base_name = normalize_point_name(self.mesh_obj.name)

        twins = [
            obj.name
            for obj in bpy.data.objects
            if obj.type == 'MESH'
            and normalize_point_name(obj.name) == base_name
        ]

        print(
            f"[Nudge] editando '{self.mesh_obj.name}' -- "
            f"{len(self.mesh_obj.data.vertices)} vértices, "
            f"{len(self.control_indices)} de controle."
        )

        if len(twins) > 1:

            print(
                f"[Nudge] ATENÇÃO: {len(twins)} malhas com o mesmo "
                f"nome-base na cena: {sorted(twins)}. Provavelmente "
                f"sobrou de uma rodada anterior do addon, e elas estão "
                f"sobrepostas -- o que você vê pode não ser o que a "
                f"ferramenta está movendo."
            )

            self.report(
                {'WARNING'},
                f"{len(twins)} malhas '{base_name}' na cena (resquício "
                f"de outra rodada?). Editando '{self.mesh_obj.name}'. "
                f"Use 'Reset (limpar cena)' no painel."
            )

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

        #
        # O ponto mais próximo do clique INDEPENDENTE do raio --
        # serve só pra mensagem de erro lá embaixo.
        #

        nearest_distance = None

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

            if nearest_distance is None or distance < nearest_distance:
                nearest_distance = distance

            if distance < best_distance:

                best_distance = distance
                best_index = index

        if best_index is None:

            #
            # Clique que não pega nada não pode ser silencioso: da
            # tela, "não peguei o ponto" e "peguei mas não mexe"
            # são idênticos. A distância do ponto mais próximo
            # separa os dois casos na hora -- se ela for grande,
            # os marcadores não estão onde você está clicando
            # (malha duplicada de outra rodada, ou Subdivision
            # ativa jogando os pontos pra posição da malha base).
            #

            if nearest_distance is None:

                self.report(
                    {'WARNING'},
                    "Nenhum ponto de controle visível nesta vista."
                )

            else:

                self.report(
                    {'INFO'},
                    f"Nenhum ponto a menos de {PICK_RADIUS_PIXELS}px "
                    f"(o mais próximo está a {nearest_distance:.0f}px, "
                    f"de {len(self.control_indices)} pontos)."
                )

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
        self.mirrored_offset_local = Vector((0.0, 0.0, 0.0))
        self.world_delta = Vector((0.0, 0.0, 0.0))

        #
        # Âncora do "plano de arraste": a profundidade (em espaço
        # de mundo) do ponto onde o usuário clicou. O mouse é
        # reconvertido pra 3D nessa mesma profundidade a cada
        # MOUSEMOVE -- é assim que o Grab nativo funciona
        # (translada no plano perpendicular à câmera).
        #

        self.drag_plane_origin = self.display_positions[seed_index]

        self.evaluated_before = self.drag_plane_origin.copy()

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

        #
        # Os vértices do outro lado também vão se mover, então
        # precisam da posição original guardada -- sem isso o
        # cancelamento do arraste (ESC) deixaria metade do rosto
        # deslocada.
        #

        if self.mirror_map is None:
            return

        for index in list(self.distances):

            mirror_index = self.mirror_map.get(index)

            if mirror_index is None:
                continue

            if mirror_index not in self.original_positions:

                self.original_positions[mirror_index] = (
                    vertices[mirror_index].co.copy()
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

        self.apply_offset(context)

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

        world_to_local = self.mesh_obj.matrix_world.to_3x3().inverted()

        self.offset_local = world_to_local @ self.world_delta

        if self.mirror_map is not None:

            #
            # O lado espelhado recebe o deslocamento REFLETIDO --
            # se o de cá vai pra direita, o de lá vai pra
            # esquerda. Reflexão de DIREÇÃO, não de posição: um
            # deslocamento não tem lugar no espaço, então a
            # translação da matriz não entra (ver
            # symmetry.mirror_world_direction).
            #

            self.mirrored_offset_local = world_to_local @ Vector(
                mirror_world_direction(
                    self.mirror_matrix,
                    self.mirror_matrix_inv,
                    tuple(self.world_delta),
                    self.mirror_axis
                )
            )

        self.apply_offset(context)

        self.update_falloff_preview()

    # -----------------------------------------------------------

    def compute_displacements(self):

        #
        # Deslocamento de cada vértice afetado, ACUMULADO: o
        # arraste direto mais, quando a simetria está ligada, o
        # arraste espelhado.
        #
        # Acumular em vez de atribuir não é detalhe -- é o que faz
        # os casos do meio da face funcionarem sem nenhum código
        # especial. Um vértice em cima do plano de simetria é o
        # próprio espelho, então recebe D (direto) + R·D
        # (espelhado); as componentes perpendiculares ao plano têm
        # sinais opostos e se cancelam, e o vértice desliza NO
        # plano em vez de sair dele. O mesmo vale pra um vizinho
        # que caia no plano, e pro caso do raio atravessar a linha
        # do meio e pegar os dois lados de um par.
        #

        displacement = {}

        def add(index, offset):

            current = displacement.get(index)

            displacement[index] = (
                offset.copy() if current is None else current + offset
            )

        add(self.seed_index, self.offset_local)

        for index, weight in self.weights.items():
            add(index, self.offset_local * weight)

        if self.mirror_map is None:
            return displacement

        mirror_seed = self.mirror_map.get(self.seed_index)

        if mirror_seed is not None:
            add(mirror_seed, self.mirrored_offset_local)

        #
        # O vizinho espelhado recebe o MESMO peso do vizinho
        # correspondente deste lado -- é o "com o peso ao redor
        # também": o campo de influência inteiro é espelhado, não
        # só o vértice arrastado.
        #

        for index, weight in self.weights.items():

            mirror_index = self.mirror_map.get(index)

            if mirror_index is not None:
                add(mirror_index, self.mirrored_offset_local * weight)

        return displacement

    # -----------------------------------------------------------

    def apply_offset(self, context):

        #
        # Reescreve só o que precisa: os vértices deslocados
        # AGORA, mais os que estavam deslocados na aplicação
        # anterior (self.touched). Sem essa diferença, diminuir o
        # raio deixaria pra trás os vértices que saíram da zona de
        # influência, congelados no último deslocamento que
        # receberam.
        #
        # Cada vértice deslocado é regrudado na superfície do alvo
        # por ponto mais próximo. É isso que dá controle: o
        # vértice desliza pela superfície acompanhando o mouse, em
        # vez de empurrar uma gaiola cujo resultado o Shrinkwrap
        # recalcula por trás (e recalcula com saltos, ver
        # core/fitting/surface_snap.py).
        #

        displacement = self.compute_displacements()

        vertices = self.mesh_obj.data.vertices

        world = self.mesh_obj.matrix_world
        world_inv = world.inverted()

        if self.snapper is not None:
            self.snapper.refresh(context.evaluated_depsgraph_get())

        active = set(displacement)

        for index in active | self.touched:

            original = self.original_positions.get(index)

            if original is None:
                continue

            offset = displacement.get(index)

            if offset is None:

                #
                # Saiu da zona de influência: volta exatamente pra
                # posição original, sem passar pelo snap (ela já
                # estava na superfície).
                #

                vertices[index].co = original

                continue

            position = original + offset

            if self.snapper is not None:

                snapped = self.snapper.snap(world @ position)

                if snapped is not None:
                    position = world_inv @ snapped

            vertices[index].co = position

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
        # Confirma o arraste. Sem undo_push aqui -- ver o
        # comentário em bl_options no topo da classe.
        #

        self.report_drag_result()

        self.push_history()

        self.clear_drag()

        vertex_highlight.mark_dirty()

    # -----------------------------------------------------------

    def report_drag_result(self):

        #
        # Mede o que o arraste REALMENTE fez, separando duas
        # coisas que da tela são idênticas:
        #
        #   - a malha BASE não se moveu  -> a escrita no vértice
        #     não pegou (objeto errado, referência velha);
        #   - a malha base moveu mas a VISÍVEL não -> o Shrinkwrap
        #     reprojetou o vértice de volta no alvo, que é o
        #     motivo mais comum de "arrasto e não acontece nada".
        #
        # Sem essa medição, as duas dão o mesmo sintoma e não tem
        # como distinguir olhando a viewport.
        #

        if self.debug_reported or self.seed_index is None:
            return

        self.debug_reported = True

        index = self.seed_index

        original = self.original_positions.get(index)

        if original is None or self.evaluated_before is None:
            return

        world = self.mesh_obj.matrix_world

        base_delta = (
            world @ self.mesh_obj.data.vertices[index].co -
            world @ original
        ).length

        evaluated_now = get_display_positions(
            self.mesh_obj,
            {index}
        ).get(index)

        if evaluated_now is None:
            return

        evaluated_delta = (evaluated_now - self.evaluated_before).length

        modifiers = " ".join(
            f"{modifier.name}"
            f"({'on' if modifier.show_viewport else 'off'})"
            for modifier in self.mesh_obj.modifiers
        ) or "(nenhum)"

        print(
            f"\n[Nudge] ===== diagnóstico do primeiro arraste =====\n"
            f"[Nudge] objeto      : {self.mesh_obj.name}\n"
            f"[Nudge] vértice     : {index}\n"
            f"[Nudge] malha base  : moveu {base_delta:.5f}\n"
            f"[Nudge] malha visível: moveu {evaluated_delta:.5f}\n"
            f"[Nudge] modifiers   : {modifiers}"
        )

        if base_delta < 1e-6:

            message = (
                "O vértice não se moveu nem na malha base -- a escrita "
                "não pegou. Veja o System Console."
            )

        elif evaluated_delta < base_delta * 0.1:

            message = (
                "A malha base moveu, mas a visível não: o Shrinkwrap "
                "está reprojetando o vértice de volta no alvo. "
                "Desligue 'Shrinkwrap ativo' no painel pra editar "
                "direto."
            )

        else:

            message = None

        if message is not None:

            print(f"[Nudge] >>> {message}")

            self.report({'WARNING'}, message)

    # -----------------------------------------------------------

    def push_history(self):

        #
        # Guarda só os vértices que ESTE arraste realmente mexeu
        # (self.touched), com a posição que eles tinham antes.
        #

        snapshot = {}

        for index in self.touched:

            original = self.original_positions.get(index)

            if original is not None:
                snapshot[index] = original.copy()

        if not snapshot:
            return

        self.history.append(snapshot)

        if len(self.history) > HISTORY_LIMIT:
            self.history.pop(0)

    # -----------------------------------------------------------

    def undo_last_drag(self):

        #
        # Desfaz um arraste, sem envolver o sistema de undo do
        # Blender -- só reescreve as posições guardadas.
        #

        if not self.history:

            self.report(
                {'INFO'},
                "Nada pra desfazer nesta sessão do Nudge."
            )

            return

        snapshot = self.history.pop()

        vertices = self.mesh_obj.data.vertices

        for index, position in snapshot.items():

            if index < len(vertices):
                vertices[index].co = position

        self.mesh_obj.data.update()

        vertex_highlight.mark_dirty()

        self.report(
            {'INFO'},
            f"Arraste desfeito ({len(self.history)} restante(s) no "
            f"histórico)."
        )

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
        self.mirrored_offset_local = Vector((0.0, 0.0, 0.0))
        self.world_delta = Vector((0.0, 0.0, 0.0))

        self.drag_plane_origin = None
        self.start_mouse_world = None

        vertex_highlight.set_falloff_preview(None, 0.0)
