#
# Grudar vértices na superfície da malha alvo, por PONTO MAIS
# PRÓXIMO. Usado pelo ajuste fino (ver
# operators/OPERATOR_nudge_vertex.py).
#
# POR QUE PONTO MAIS PRÓXIMO E NÃO RAIO:
#
# O modifier Shrinkwrap do addon está em modo PROJECT -- lança um
# raio ao longo da normal do vértice (ver
# core/fitting/projection.py). Isso é o certo pro encaixe INICIAL,
# quando a malha ainda pode estar longe e a direção importa pra
# não grudar no lado errado do rosto. Mas projeção por raio é
# DESCONTÍNUA, e no ajuste fino isso vira o problema principal:
#
#   - com as duas direções ligadas, o hit escolhido troca de lado
#     no instante em que o vértice cruza a superfície;
#   - se o raio não acha nada dentro do project_limit, o vértice
#     fica na posição da gaiola -- entrar e sair desse limite dá
#     um salto do tamanho da distância gaiola-superfície;
#   - a direção do raio é a normal da GAIOLA, então arrastar um
#     vértice gira a normal dos vizinhos e desloca o ponto de
#     impacto deles lá longe (efeito alavanca, proporcional à
#     distância).
#
# Ponto mais próximo não tem nenhum desses: é contínuo (mover a
# origem por d move o resultado no máximo ~d), não tem direção pra
# escolher errado, e não tem como "passar reto". É o mesmo
# princípio do Snap to Face do Blender, e é o que toda ferramenta
# de retopologia usa pra editar em cima de uma superfície.
#
# A ressalva do nearest-point -- grudar no lado errado, ex.: um
# vértice de dentro do nariz pulando pra pele de fora -- só vale
# quando a origem está LONGE da superfície. Aqui ela nunca está: o
# Nudge crava o resultado do Shrinkwrap na malha antes de começar
# (bake_evaluated_positions), então todo vértice já nasce em cima
# do alvo e só desliza a partir dali.
#

class SurfaceSnapper:

    #
    # Consulta de ponto mais próximo na malha alvo, com as
    # matrizes já pré-calculadas -- durante um arraste isso roda
    # centenas de vezes por frame.
    #

    def __init__(self, target_obj, depsgraph, limit):

        self.target_obj = target_obj

        self.matrix = target_obj.matrix_world.copy()
        self.matrix_inv = target_obj.matrix_world.inverted()

        self.limit = limit

        self.evaluated = target_obj.evaluated_get(depsgraph)

    def refresh(self, depsgraph):

        #
        # O objeto avaliado é uma cópia dentro do depsgraph, e o
        # depsgraph é reconstruído sempre que a cena muda -- e o
        # próprio Nudge muda a cena a cada movimento do mouse.
        # Reobter a referência uma vez por aplicação é barato e
        # evita trabalhar em cima de uma cópia velha.
        #

        self.evaluated = self.target_obj.evaluated_get(depsgraph)

    def snap(self, world_co):

        #
        # Recebe e devolve posição de MUNDO. Devolve None se não
        # achou superfície dentro do limite -- aí o chamador
        # mantém a posição livre, que é melhor que arrastar o
        # vértice pra um lugar arbitrário.
        #

        local = self.matrix_inv @ world_co

        result, location, normal, index = (
            self.evaluated.closest_point_on_mesh(local, distance=self.limit)
        )

        if not result:
            return None

        return self.matrix @ location


def bake_evaluated_positions(mesh_obj, depsgraph):

    #
    # Copia as posições AVALIADAS (o que se vê na viewport, com os
    # modifiers aplicados) pra dentro da malha base.
    #
    # É o que permite o Nudge desligar o Shrinkwrap sem que nada
    # se mexa na tela: depois disso, a malha base JÁ ESTÁ onde o
    # Shrinkwrap a colocou. O usuário entra na ferramenta e não vê
    # diferença nenhuma -- só que agora ele controla os vértices
    # de verdade, em vez de empurrar uma gaiola cujo resultado é
    # recalculado por trás.
    #
    # Só funciona com modifiers que preservam a contagem de
    # vértices (Shrinkwrap, Corrective Smooth). Com Subdivision no
    # stack a topologia muda e não existe correspondência de
    # índice: devolve False e o chamador decide o que fazer.
    #

    base_mesh = mesh_obj.data

    evaluated_mesh = mesh_obj.evaluated_get(depsgraph).data

    vertex_count = len(base_mesh.vertices)

    if len(evaluated_mesh.vertices) != vertex_count:
        return False

    coordinates = [0.0] * (vertex_count * 3)

    evaluated_mesh.vertices.foreach_get("co", coordinates)

    base_mesh.vertices.foreach_set("co", coordinates)

    base_mesh.update()

    return True
