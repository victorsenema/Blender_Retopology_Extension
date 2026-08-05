import bpy


RELAX_MODIFIER_NAME = "RetopoRelax"


def add_or_get(mesh_obj):

    #
    # Relaxamento como modifier nativo (Corrective Smooth), não
    # como código nosso mexendo em bmesh -- assim a intensidade
    # é literalmente uma property do modifier, e arrastar o
    # slider no painel atualiza a malha ao vivo na viewport (é o
    # próprio Blender fazendo isso, de graça).
    #
    # Corrective Smooth em vez de Laplacian Smooth: "factor" já
    # vem limitado a 0..1 (0 = sem efeito, 1 = suavização
    # máxima), o que bate certinho com "um slide pra escolher o
    # quanto quero relaxar". rest_source fica no padrão ('ORCO'),
    # que não precisa de bind manual pra funcionar.
    #
    # Esse botão/modifier é exclusivo pra relaxamento -- não
    # mexe na configuração do Shrinkwrap (core/fitting/
    # projection.py), só na ORDEM dele no stack (ver
    # _move_before_shrinkwrap).
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

    _move_before_shrinkwrap(mesh_obj, modifier)

    return modifier


# -------------------------------------------------------------

def _move_before_shrinkwrap(mesh_obj, modifier):

    #
    # Ordem do stack importa: se o Relax vier DEPOIS do
    # Shrinkwrap, ele suaviza a malha já colada na superfície e
    # pode descolar vértice da superfície esculpida (flutuando
    # acima/abaixo dela). Relaxando ANTES, o Shrinkwrap projeta
    # de novo por cima do resultado relaxado -- os vértices se
    # reacomodam (desfazendo entrelaçamento) e voltam a ficar
    # perfeitamente colados na malha alvo, porque a projeção
    # sempre roda por último no stack.
    #
    # modifiers.new() sempre adiciona no fim do stack, então
    # isso só precisa mover na primeira vez que o Relax é criado
    # (quando o Shrinkwrap já existe na frente dele). Rodar
    # "Apply Mesh" de novo depois não bagunça a ordem: ele só
    # troca o Shrinkwrap existente, que continua sendo recriado
    # no fim do stack -- ou seja, sempre depois do Relax.
    #

    modifiers = mesh_obj.modifiers

    current_index = modifiers.find(modifier.name)

    if current_index <= 0:
        return

    #
    # modifiers.move() é a forma direta (Blender 2.90+), mas por
    # segurança -- caso não exista em alguma build específica --
    # cai pro operator nativo via context override.
    #

    try:

        modifiers.move(current_index, 0)

        return

    except AttributeError:
        pass

    view_layer = bpy.context.view_layer

    previous_active = view_layer.objects.active

    view_layer.objects.active = mesh_obj

    try:

        with bpy.context.temp_override(object=mesh_obj):

            bpy.ops.object.modifier_move_to_index(
                modifier=modifier.name,
                index=0,
            )

    finally:

        view_layer.objects.active = previous_active
