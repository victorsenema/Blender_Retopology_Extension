import heapq
import math


#
# Ajuste fino pós Apply Mesh: em vez dos antigos critical points
# (Empties), agora usamos vértices reais da malha marcados nos 4
# Vertex Groups criados no template (Nose_VG, Face_VG, Eyes_VG,
# Mouth_VG) como pontos de controle. Ver operators/
# OPERATOR_nudge_vertex.py (arrastar) e ui/vertex_highlight.py
# (destaque visual).
#
# O objetivo é reproduzir, em Object Mode e partindo só dos
# vértices de controle, o que o Proportional Editing (tecla O)
# faz no Edit Mode: arrastar um vértice e puxar junto, com
# decaimento suave, toda a vizinhança dentro de um raio
# ajustável ao vivo. As três peças disso moram aqui:
#
#   build_adjacency()            -- topologia, calculada UMA vez
#   compute_geodesic_distances() -- distância ao longo da malha
#   falloff_weights()            -- curva de decaimento
#
# A separação entre distância e peso é o que permite mudar o
# raio no meio de um arraste (roda do mouse) sem refazer o
# Dijkstra: a distância de cada vértice até o que está sendo
# arrastado não muda, só a curva aplicada em cima dela.
#

CONTROL_VERTEX_GROUPS = (
    "Nose_VG",
    "Face_VG",
    "Eyes_VG",
    "Mouth_VG",
)


def get_control_vertex_indices(mesh_obj, verbose=False):

    #
    # Índices (na malha atual, já com Apply Mesh feito) de todo
    # vértice que pertence a qualquer um dos 4 vertex groups de
    # controle.
    #

    existing_names = {group.name for group in mesh_obj.vertex_groups}

    group_indices = {
        group.index
        for group in mesh_obj.vertex_groups
        if group.name in CONTROL_VERTEX_GROUPS
    }

    if verbose:

        print(
            f"[vertex_control] '{mesh_obj.name}' tem "
            f"{len(mesh_obj.vertex_groups)} vertex group(s): "
            f"{sorted(existing_names) if existing_names else '(nenhum)'}"
        )

        missing = [
            name for name in CONTROL_VERTEX_GROUPS
            if name not in existing_names
        ]

        if missing:

            print(
                f"[vertex_control] Grupos de controle NÃO encontrados "
                f"nessa malha: {missing}"
            )

    if not group_indices:
        return set()

    indices = set()

    for vertex in mesh_obj.data.vertices:

        for group_element in vertex.groups:

            if group_element.group in group_indices:

                indices.add(vertex.index)

                break

    if verbose:

        for group in mesh_obj.vertex_groups:

            if group.index in group_indices:

                count = sum(
                    1
                    for vertex in mesh_obj.data.vertices
                    if any(
                        ge.group == group.index for ge in vertex.groups
                    )
                )

                print(
                    f"[vertex_control] '{group.name}' -- {count} "
                    f"vértice(s) atribuído(s)."
                )

    return indices


def get_control_vertex_indices_by_group(mesh_obj):

    #
    # Igual get_control_vertex_indices(), mas separado por grupo
    # -- {nome_do_grupo: {índices...}} -- usado só pra pintar cada
    # grupo com uma cor diferente no destaque visual (ver
    # ui/vertex_highlight.py), o que ajuda a enxergar visualmente
    # se algum grupo está com cobertura incompleta na malha (ex.:
    # um lado espelhado sem os pesos copiados).
    #

    result = {name: set() for name in CONTROL_VERTEX_GROUPS}

    group_index_to_name = {
        group.index: group.name
        for group in mesh_obj.vertex_groups
        if group.name in CONTROL_VERTEX_GROUPS
    }

    if not group_index_to_name:
        return result

    for vertex in mesh_obj.data.vertices:

        for group_element in vertex.groups:

            name = group_index_to_name.get(group_element.group)

            if name is not None:

                result[name].add(vertex.index)

    return result


# -------------------------------------------------------------

def get_display_positions(mesh_obj, indices=None):

    #
    # Posição de MUNDO de cada vértice como ele aparece na
    # viewport -- isto é, DEPOIS dos modifiers, e não a posição
    # crua guardada em mesh.data.
    #
    # Isso importa muito aqui: o Shrinkwrap fica vivo no stack
    # (ver core/fitting/projection.py), então o vértice que o
    # usuário vê grudado na superfície do rosto quase nunca está
    # onde mesh.data.vertices[i].co diz que está. Desenhar o
    # destaque (ui/vertex_highlight.py) ou medir o raio de clique
    # (OPERATOR_nudge_vertex.pick_vertex) na posição crua faz os
    # pontos parecerem flutuando fora da malha e o clique errar
    # o alvo.
    #
    # RESSALVA -- Subdivision: modifier que muda topologia não
    # preserva correspondência de índice (a malha avaliada tem
    # muito mais vértices que a original), então nesse caso não
    # existe "o vértice i avaliado" pra consultar, e caímos na
    # posição crua. Não dá pra contornar com "ponto mais próximo
    # na malha avaliada": é exatamente o problema que faz
    # projection.py rejeitar nearest-point -- um vértice de dentro
    # do nariz grudaria na pele de fora. O painel avisa quando
    # essa situação está ativa (ver has_topology_changing_modifier).
    #

    import bpy

    base_mesh = mesh_obj.data

    source = base_mesh

    try:

        depsgraph = bpy.context.evaluated_depsgraph_get()

        evaluated_mesh = mesh_obj.evaluated_get(depsgraph).data

        if len(evaluated_mesh.vertices) == len(base_mesh.vertices):
            source = evaluated_mesh

    except (AttributeError, RuntimeError):

        #
        # Sem depsgraph utilizável (contexto restrito) -- cai na
        # malha crua em vez de derrubar o draw handler.
        #

        source = base_mesh

    world = mesh_obj.matrix_world

    vertices = source.vertices

    if indices is None:
        return [world @ vertex.co for vertex in vertices]

    #
    # Só os índices pedidos, devolvidos como {índice: posição}.
    # Durante um arraste isso roda a cada frame: converter a
    # malha inteira (milhares de vértices) pra desenhar algumas
    # centenas de pontos de controle seria desperdício puro.
    #

    count = len(vertices)

    return {
        index: world @ vertices[index].co
        for index in indices
        if index < count
    }


def has_topology_changing_modifier(mesh_obj):

    #
    # Existe algum modifier ativo que muda a contagem de
    # vértices? (na prática: Subdivision). É a condição em que
    # get_display_positions() não consegue usar a malha avaliada
    # -- ver a ressalva logo acima. O painel usa isso pra avisar
    # o usuário de que os pontos estão sendo mostrados na posição
    # da malha base.
    #

    for modifier in mesh_obj.modifiers:

        if not modifier.show_viewport:
            continue

        if modifier.type in {'SUBSURF', 'MULTIRES', 'REMESH', 'DECIMATE'}:
            return True

    return False


# -------------------------------------------------------------

def default_influence_radius(mesh_obj):

    #
    # Raio de influência inicial proporcional ao tamanho da
    # cabeça, NUNCA um número fixo em unidades de mundo: uma
    # cabeça modelada com 0.2 de altura e outra com 20 são
    # igualmente comuns, e um raio fixo viraria "mexe um vértice
    # só" numa e "arrasta o rosto inteiro" na outra.
    #
    # 8% da maior dimensão é a mesma proporção que
    # projection.py usa pro project_limit do Shrinkwrap.
    #

    size = max(mesh_obj.dimensions)

    if size <= 0.0:
        return 0.1

    return size * 0.08


def build_adjacency(mesh_obj):

    #
    # Lista de vizinhos por vértice, montada a partir das
    # ARESTAS da malha -- calculada uma vez quando a ferramenta
    # abre e reaproveitada em todos os arrastes da sessão.
    #
    # Antes isso era um bmesh.new()/from_mesh() reconstruído a
    # cada clique, o que é caro à toa: a topologia não muda
    # enquanto o usuário só arrasta vértice. Só as POSIÇÕES
    # mudam, e essas são lidas na hora do Dijkstra.
    #
    # foreach_get() puxa o array inteiro de uma vez do lado C em
    # vez de iterar RNA vértice a vértice em Python.
    #

    mesh = mesh_obj.data

    edge_count = len(mesh.edges)

    edge_vertices = [0] * (edge_count * 2)

    mesh.edges.foreach_get("vertices", edge_vertices)

    adjacency = [[] for _ in range(len(mesh.vertices))]

    for edge_index in range(edge_count):

        a = edge_vertices[edge_index * 2]
        b = edge_vertices[edge_index * 2 + 1]

        adjacency[a].append(b)
        adjacency[b].append(a)

    return adjacency


def world_coordinates(mesh_obj):

    #
    # Posições de MUNDO de todos os vértices da malha base, num
    # array plano [x0, y0, z0, x1, y1, z1, ...].
    #
    # Mundo, e não local: o template carrega escala não uniforme
    # na matrix_world vinda do Alignment, então 1 unidade local
    # não vale 1 unidade de cena nem vale a mesma coisa nos 3
    # eixos -- distância e tolerância medidas em local sairiam
    # deformadas.
    #
    # foreach_get() puxa o array de uma vez do lado C; a
    # multiplicação pela matriz é feita na mão, componente a
    # componente, pra não criar milhares de objetos Vector.
    #

    mesh = mesh_obj.data

    vertex_count = len(mesh.vertices)

    local = [0.0] * (vertex_count * 3)

    mesh.vertices.foreach_get("co", local)

    world = mesh_obj.matrix_world

    coordinates = [0.0] * (vertex_count * 3)

    for index in range(vertex_count):

        offset = index * 3

        x = local[offset]
        y = local[offset + 1]
        z = local[offset + 2]

        coordinates[offset] = (
            world[0][0] * x + world[0][1] * y +
            world[0][2] * z + world[0][3]
        )

        coordinates[offset + 1] = (
            world[1][0] * x + world[1][1] * y +
            world[1][2] * z + world[1][3]
        )

        coordinates[offset + 2] = (
            world[2][0] * x + world[2][1] * y +
            world[2][2] * z + world[2][3]
        )

    return coordinates


def world_positions(mesh_obj):

    #
    # O mesmo que world_coordinates(), em tuplas (x, y, z)
    # indexadas por vértice -- formato que
    # symmetry.build_mirror_map() consome.
    #

    coordinates = world_coordinates(mesh_obj)

    return [
        (
            coordinates[index * 3],
            coordinates[index * 3 + 1],
            coordinates[index * 3 + 2],
        )
        for index in range(len(coordinates) // 3)
    ]


def mean_edge_length(mesh_obj):

    #
    # Comprimento médio de aresta, em unidades de mundo. Serve de
    # escala natural pra tolerâncias que dependem do espaçamento
    # da malha -- em especial a do pareamento de vértices
    # espelhados (ver symmetry.build_mirror_map): um número fixo
    # ali seria grosso demais numa malha densa e apertado demais
    # numa esparsa.
    #

    mesh = mesh_obj.data

    edge_count = len(mesh.edges)

    if edge_count == 0:
        return 0.0

    edge_vertices = [0] * (edge_count * 2)

    mesh.edges.foreach_get("vertices", edge_vertices)

    coordinates = world_coordinates(mesh_obj)

    total = 0.0

    for edge_index in range(edge_count):

        a = edge_vertices[edge_index * 2] * 3
        b = edge_vertices[edge_index * 2 + 1] * 3

        dx = coordinates[a] - coordinates[b]
        dy = coordinates[a + 1] - coordinates[b + 1]
        dz = coordinates[a + 2] - coordinates[b + 2]

        total += math.sqrt(dx * dx + dy * dy + dz * dz)

    return total / edge_count


def compute_geodesic_distances(
    mesh_obj,
    adjacency,
    seed_index,
    max_distance
):

    #
    # Dijkstra limitado a partir do vértice arrastado: distância
    # ANDANDO PELA MALHA (soma dos comprimentos de aresta), não
    # distância em linha reta. É o que evita que arrastar a asa
    # do nariz puxe junto a parede de dentro da narina, que está
    # pertinho em linha reta mas longe pela superfície.
    #
    # Distâncias em ESPAÇO DE MUNDO, não local: o Alignment
    # multiplica a matrix_world do template por uma escala não
    # uniforme (ver core/fitting/alignment.apply_alignment), então
    # 1 unidade local não vale 1 unidade de mundo, nem vale a
    # mesma coisa nos 3 eixos. Como o raio é um número que o
    # usuário lê e edita no painel (em metros/unidades de cena),
    # ele precisa significar a mesma coisa em qualquer modelo.
    #

    coordinates = world_coordinates(mesh_obj)

    distances = {seed_index: 0.0}

    visited = set()

    heap = [(0.0, seed_index)]

    while heap:

        current_distance, index = heapq.heappop(heap)

        if index in visited:
            continue

        visited.add(index)

        if current_distance >= max_distance:
            continue

        offset = index * 3

        x = coordinates[offset]
        y = coordinates[offset + 1]
        z = coordinates[offset + 2]

        for neighbour in adjacency[index]:

            if neighbour in visited:
                continue

            neighbour_offset = neighbour * 3

            dx = coordinates[neighbour_offset] - x
            dy = coordinates[neighbour_offset + 1] - y
            dz = coordinates[neighbour_offset + 2] - z

            new_distance = current_distance + math.sqrt(
                dx * dx + dy * dy + dz * dz
            )

            if new_distance > max_distance:
                continue

            previous = distances.get(neighbour)

            if previous is None or new_distance < previous:

                distances[neighbour] = new_distance

                heapq.heappush(heap, (new_distance, neighbour))

    return distances


def falloff_weights(
    distances,
    radius,
    control_indices,
    seed_index,
    affect_control_points=False
):

    #
    # Curva de decaimento "Smooth", a mesma do Proportional
    # Editing do Blender: peso 1 no vértice arrastado, caindo
    # suave até EXATAMENTE 0 na borda do raio.
    #
    # Antes era uma Gaussiana cortada no raio, que chegava na
    # borda ainda valendo ~0.13 -- ou seja, o último anel de
    # vértices de dentro do raio se movia e o primeiro anel de
    # fora não, deixando um degrau visível na malha. O smoothstep
    # resolve isso por construção (derivada zero nas duas pontas).
    #
    # affect_control_points: por padrão FALSE -- um ponto de
    # controle nunca é arrastado junto por outro ponto de
    # controle, só a malha livre em volta reage (pedido
    # explícito). Ligar isso deixa o comportamento idêntico ao
    # Proportional Editing de verdade, que não faz distinção entre
    # vértices; o toggle existe no painel pra dar pra comparar os
    # dois na prática -- excluir os vizinhos de controle pode
    # deixar um "degrau" onde dois pontos de controle são quase
    # colados (ex.: contorno do olho).
    #

    weights = {}

    if radius <= 0.0:
        return weights

    for index, distance in distances.items():

        if index == seed_index:
            continue

        if distance >= radius:
            continue

        if not affect_control_points and index in control_indices:
            continue

        factor = 1.0 - (distance / radius)

        weights[index] = factor * factor * (3.0 - 2.0 * factor)

    return weights
