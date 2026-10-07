import bpy


#
# Nomes dos modifiers que este addon gerencia, e a ordem final
# desejada entre eles no stack:
#
#     Shrinkwrap -> Subdivision -> Shrinkwrap (pós)
#
# SÃO DOIS SHRINKWRAPS, um de cada lado da Subdivision, e o de
# baixo não é redundante:
#
#   - o primeiro cola a gaiola na superfície esculpida;
#   - a Subdivision (Catmull-Clark) suaviza a gaiola, e a
#     superfície limite que ela produz fica DENTRO dela nas
#     regiões convexas -- ou seja, a malha descola do alvo
#     justamente onde ele é mais curvo (nariz, queixo, maçã do
#     rosto);
#   - o segundo Shrinkwrap recola o resultado já subdividido.
#
# Uma passada só não resolve: o Shrinkwrap está em modo PROJECT
# (raio ao longo da normal, ver projection.py), e raio erra. A
# segunda passada parte de uma malha muito mais perto do alvo,
# então acerta onde a primeira passou reto. É a mesma ideia de
# iterar que ferramentas de wrap usam, com duas iterações.
#
# Fonte única de verdade -- subdivision.py e projection.py
# importam os nomes daqui em vez de cada um definir o próprio, e
# chamam enforce_order() depois de criar/alterar seu modifier.
# Assim a ordem nunca desalinha, não importa a sequência de
# cliques do usuário (ex.: adicionar Subdivision DEPOIS de já ter
# os Shrinkwraps, ou rodar "Apply Mesh" de novo em cima de um
# resultado que já tem os outros).
#
# HISTÓRICO: existiu um quarto modifier aqui, um Corrective
# Smooth chamado "RetopoRelax", removido em 07/10. Ele nunca
# chegou a ser usado -- o botão saiu do painel em 11/08 e o
# modifier nascia com factor 0, então era adicionado e cravado
# sem efeito nenhum a cada rodada.
#

SUBDIVISION_MODIFIER_NAME = "RetopoSubdivision"
SHRINKWRAP_MODIFIER_NAME = "RetopoSurfaceProjection"
SHRINKWRAP_POST_MODIFIER_NAME = "RetopoSurfaceProjectionPost"

CANONICAL_ORDER = (
    SHRINKWRAP_MODIFIER_NAME,
    SUBDIVISION_MODIFIER_NAME,
    SHRINKWRAP_POST_MODIFIER_NAME,
)

#
# Os dois Shrinkwraps juntos -- quem precisa mexer em "a
# projeção" (ligar/desligar, cravar) tem que tratar os dois, e
# não só o primeiro. Ver OPERATOR_nudge_vertex e ui/panel.py.
#

SHRINKWRAP_MODIFIER_NAMES = (
    SHRINKWRAP_MODIFIER_NAME,
    SHRINKWRAP_POST_MODIFIER_NAME,
)


def enforce_order(mesh_obj):

    modifiers = mesh_obj.modifiers

    target_index = 0

    for name in CANONICAL_ORDER:

        current_index = modifiers.find(name)

        if current_index == -1:
            continue

        if current_index != target_index:
            _move(mesh_obj, current_index, target_index)

        target_index += 1


# -------------------------------------------------------------

def _move(mesh_obj, from_index, to_index):

    modifiers = mesh_obj.modifiers

    #
    # modifiers.move() é a forma direta (Blender 2.90+), mas por
    # segurança -- caso não exista em alguma build específica --
    # cai pro operator nativo via context override.
    #

    try:

        modifiers.move(from_index, to_index)

        return

    except AttributeError:
        pass

    modifier = modifiers[from_index]

    view_layer = bpy.context.view_layer

    previous_active = view_layer.objects.active

    view_layer.objects.active = mesh_obj

    try:

        with bpy.context.temp_override(object=mesh_obj):

            bpy.ops.object.modifier_move_to_index(
                modifier=modifier.name,
                index=to_index,
            )

    finally:

        view_layer.objects.active = previous_active
