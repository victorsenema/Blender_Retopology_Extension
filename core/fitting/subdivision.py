from .modifier_stack import SUBDIVISION_MODIFIER_NAME, enforce_order
from .projection import add_post_subdivision


def add_or_get(mesh_obj, target=None):

    #
    # Subdivision Surface como modifier nativo, entre os dois
    # Shrinkwraps (ver modifier_stack.CANONICAL_ORDER): a malha
    # chega aqui já colada no alvo, é subdividida, e o Shrinkwrap
    # de baixo recola o resultado.
    #
    # Esse segundo Shrinkwrap é criado AQUI, junto com a
    # Subdivision, porque é exatamente quando ele passa a ser
    # necessário: sem Subdivision no stack não há o que recolar.
    # Se `target` não vier, só a Subdivision é criada -- e aí a
    # malha vai descolar nas regiões convexas.
    #
    # "levels" é o nível usado na viewport -- é o que
    # bpy.context.evaluated_depsgraph_get() respeita, e é o que
    # aparece como campo numérico no painel (1, 2, 3...).
    # render_levels é mantido igual só pra consistência caso
    # alguém renderize com F12 antes de rodar "Apply Modifiers".
    #

    modifier = mesh_obj.modifiers.get(SUBDIVISION_MODIFIER_NAME)

    if modifier is not None:

        #
        # Já existe -- mas o Shrinkwrap de baixo pode ter sido
        # apagado à mão, ou vir de um arquivo salvo antes desta
        # mudança. Garante que ele está lá.
        #

        if target is not None:
            add_post_subdivision(mesh_obj, target)
            enforce_order(mesh_obj)

        return modifier

    modifier = mesh_obj.modifiers.new(
        name=SUBDIVISION_MODIFIER_NAME,
        type='SUBSURF'
    )

    modifier.levels = 1
    modifier.render_levels = modifier.levels

    if target is not None:
        add_post_subdivision(mesh_obj, target)

    enforce_order(mesh_obj)

    return modifier
