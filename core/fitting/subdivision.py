from .modifier_stack import SUBDIVISION_MODIFIER_NAME, enforce_order


def add_or_get(mesh_obj):

    #
    # Subdivision Surface como modifier nativo, sempre primeiro
    # no stack (Subdivide -> Shrinkwrap -> Relax, ver
    # modifier_stack.CANONICAL_ORDER): subdivide a malha ANTES
    # de projetar, então o Shrinkwrap trabalha com mais
    # resolução (fica mais fiel aos detalhes da malha esculpida)
    # e o Relax suaviza o resultado já mais denso.
    #
    # "levels" é o nível usado na viewport -- é o que
    # bpy.context.evaluated_depsgraph_get() respeita, e é o que
    # aparece como campo numérico no painel (1, 2, 3...).
    # render_levels é mantido igual só pra consistência caso
    # alguém renderize com F12 antes de rodar "Apply Modifiers".
    #

    modifier = mesh_obj.modifiers.get(SUBDIVISION_MODIFIER_NAME)

    if modifier is not None:
        return modifier

    modifier = mesh_obj.modifiers.new(
        name=SUBDIVISION_MODIFIER_NAME,
        type='SUBSURF'
    )

    modifier.levels = 1
    modifier.render_levels = modifier.levels

    enforce_order(mesh_obj)

    return modifier
