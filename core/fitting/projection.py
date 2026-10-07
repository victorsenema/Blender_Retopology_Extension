from .modifier_stack import (
    SHRINKWRAP_MODIFIER_NAME,
    SHRINKWRAP_POST_MODIFIER_NAME,
    enforce_order,
)


def configure_shrinkwrap(mesh_obj, target, name):

    #
    # Cria (ou substitui) UM modifier Shrinkwrap configurado do
    # jeito do addon. Extraído da classe abaixo porque agora
    # existem dois -- um de cada lado da Subdivision, ver
    # modifier_stack.CANONICAL_ORDER -- e os dois têm que ser
    # configurados igual.
    #

    if mesh_obj is None or target is None:
        return None

    #
    # Rodar de novo em cima de um resultado anterior (ex.: "Apply
    # Mesh" clicado duas vezes) não deve empilhar modifiers --
    # substitui o anterior.
    #

    existing = mesh_obj.modifiers.get(name)

    if existing is not None:
        mesh_obj.modifiers.remove(existing)

    modifier = mesh_obj.modifiers.new(name=name, type='SHRINKWRAP')

    modifier.target = target
    modifier.wrap_method = 'PROJECT'

    #
    # Projeta pra dentro e pra fora ao longo da normal -- depois
    # do warp TPS, o vértice pode estar tanto "afundado" quanto
    # "saltando" em relação à superfície real.
    #

    modifier.use_negative_direction = True
    modifier.use_positive_direction = True

    #
    # Limite de distância de busca, proporcional ao tamanho da
    # própria cabeça (evita colar num pedaço de superfície muito
    # distante / do lado errado).
    #

    head_size = max(mesh_obj.dimensions)

    modifier.project_limit = head_size * 0.08

    enforce_order(mesh_obj)

    return modifier


def add_post_subdivision(mesh_obj, target):

    #
    # O Shrinkwrap que fica DEPOIS da Subdivision. Sem ele, a
    # superfície limite do Catmull-Clark descola do alvo nas
    # regiões convexas -- ver o comentário no topo de
    # modifier_stack.py. Criado junto com a Subdivision, que é
    # exatamente quando passa a ser necessário.
    #

    return configure_shrinkwrap(
        mesh_obj,
        target,
        SHRINKWRAP_POST_MODIFIER_NAME
    )


class SurfaceProjection:

    #
    # Cola o template sobre a superfície esculpida (target_mesh)
    # usando o modifier Shrinkwrap nativo do Blender, no modo
    # PROJECT: cada vértice é projetado ao longo da própria
    # normal (não pelo ponto mais próximo em linha reta).
    #
    # Por que não nearest-point puro: nearest-point ignora
    # direção -- um vértice na bochecha esquerda pode grudar num
    # pedaço de superfície da bochecha direita, ou dentro da
    # boca, sempre que essas partes estiverem mais perto em
    # distância reta do que a pele "certa" na frente dele.
    # Projetar ao longo da normal, com um limite de distância de
    # busca, evita isso.
    #
    # O modifier fica só ADICIONADO/configurado, sem ser
    # aplicado -- assim o resultado é sempre uma preview ao
    # vivo, editável. A finalização (bake de TODOS os modifiers,
    # incluindo a Subdivision) é feita à parte em
    # core/fitting/finalize.py, usada por
    # operators/OPERATOR_apply_modifiers.py.
    #

    MODIFIER_NAME = SHRINKWRAP_MODIFIER_NAME

    def __init__(self, session):

        self.session = session

        self.template = session.template.mesh
        self.target = session.target_mesh

    # -------------------------------------------------------------

    def add_modifier(self):

        modifier = configure_shrinkwrap(
            self.template,
            self.target,
            self.MODIFIER_NAME
        )

        if modifier is None:
            return None

        print(
            f"[SurfaceProjection] modifier Shrinkwrap adicionado "
            f"(project_limit={modifier.project_limit:.4f}) -- "
            f"ainda NÃO aplicado, use 'Apply Modifiers' pra finalizar."
        )

        return modifier
