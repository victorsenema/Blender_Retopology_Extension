from .modifier_stack import RELAX_MODIFIER_NAME, enforce_order


def add_or_get(mesh_obj):

    #
    # Relaxamento como modifier nativo (Corrective Smooth), não
    # como código nosso mexendo em bmesh -- assim a intensidade
    # é literalmente uma property do modifier, e arrastar o
    # slider no painel atualiza a malha ao vivo na viewport (é o
    # próprio Blender fazendo isso, de graça).
    #
    # Corrective Smooth em vez de Smooth simples: Corrective
    # Smooth preserva muito melhor o volume/detalhe do rosto
    # (Smooth simples "derretia" a malha, ficava ruim). A
    # ressalva é que Corrective Smooth calcula uma correção
    # comparando o estado atual com o ORCO (mesh-base, sem
    # modifiers) -- se ele fosse o PRIMEIRO modifier do stack,
    # "atual" e ORCO seriam idênticos e a correção cancelaria a
    # suavização inteira (não faria nada, não importa o factor).
    # Por isso a ordem importa: ele SEMPRE vem depois do
    # Shrinkwrap (ver modifier_stack.CANONICAL_ORDER) -- e como
    # o Relax só pode ser adicionado depois de "Apply Mesh" já
    # ter rodado (que é quem cria o Shrinkwrap), isso é garantido
    # na prática.
    #

    modifier = mesh_obj.modifiers.get(RELAX_MODIFIER_NAME)

    if modifier is not None:
        return modifier

    modifier = mesh_obj.modifiers.new(
        name=RELAX_MODIFIER_NAME,
        type='CORRECTIVE_SMOOTH'
    )

    #
    # Começa em 0 (sem efeito nenhum) -- o usuário é quem decide
    # subir o slider.
    #

    modifier.factor = 0.0
    modifier.iterations = 5

    enforce_order(mesh_obj)

    return modifier
