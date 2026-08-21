#
# Simetria do Landmarking: quando a cabeça alvo é espelhada, o
# usuário só precisa clicar um lado -- o ponto do outro lado
# aparece junto, em tempo real, enquanto ele move o mouse. E os
# pontos do meio da face ficam TRAVADOS no plano de simetria, em
# vez de dependerem da pontaria do clique.
#
# Ver operators/OPERATOR_create_critical_points.py (quem usa) e
# ui/panel.py (a caixa "Objeto Espelhado" + o eixo).
#
# O plano de espelhamento é o plano LOCAL do objeto alvo
# (X=0 ou Y=0 no espaço local dele), não do mundo. É a mesma
# referência que o sculpt simétrico e o modifier Mirror do
# Blender usam, então uma cabeça esculpida com simetria ligada já
# está simétrica em relação a esse plano, esteja o objeto onde
# estiver na cena.
#
# ESTE MÓDULO NÃO IMPORTA bpy NEM mathutils de propósito: recebe
# a matriz do objeto (qualquer coisa indexável [linha][coluna],
# o que inclui um mathutils.Matrix) e devolve tuplas. Assim toda
# a lógica dá pra testar fora do Blender -- ver
# tools/test_symmetry.py.
#


#
# Pares esquerda/direita, escritos na mão em vez de deduzidos por
# regra: os nomes do template não seguem um padrão único (prefixo
# em "LeftEye_Top", prefixo com underscore em "Left_Nostril",
# sufixo em "MouthLeft"), e um deles tem typo -- "Rigth_Ear_Anchor"
# está assim dentro do VG_Template.blend e é mantido de propósito
# (ver POINT_NAMES em OPERATOR_create_critical_points.py).
#
# Uma regra "esperta" ia calar quando o nome não batesse; a tabela
# explícita, junto com validate_point_names(), faz o addon
# reclamar alto se algum ponto ficar sem classificação.
#

MIRROR_PAIRS = (
    ("LeftEye_Top", "RightEye_Top"),
    ("LeftEye_Bottom", "RightEye_Bottom"),
    ("LeftEye_Inner_Side", "RightEye_Inner_Side"),
    ("LeftEye_Outer_Side", "RightEye_Outer_Side"),
    ("Left_Nostril", "Right_Nostril"),
    ("Left_Nose_Inside", "Right_Nose_Inside"),
    ("MouthLeft", "MouthRight"),
    ("JawLeft", "JawRight"),
    ("Left_Ear_Anchor", "Rigth_Ear_Anchor"),
)


#
# Pontos que vivem no meio da face (plano sagital). Com a simetria
# ligada eles são grudados no plano de espelhamento -- é o
# "travar" pedido: o usuário clica por cima do nariz e o ponto cai
# exatamente no meio, sem depender de acertar o pixel.
#

NEUTRAL_POINTS = (
    "ForeheadTop",
    "NoseRoot",
    "NoseTip",
    "UpperLip_Inner_Side",
    "UpperLip_Outer_Side",
    "LowerLip_Inner_Side",
    "LowerLip_Outer_Side",
    "Chin",
    "Neck_Chin_Connection",
)


AXIS_INDEX = {
    "X": 0,
    "Y": 1,
    "Z": 2,
}


_MIRROR_LOOKUP = {
    name: partner
    for left, right in MIRROR_PAIRS
    for name, partner in ((left, right), (right, left))
}


# -------------------------------------------------------------

def get_mirror_name(name):

    #
    # Nome do ponto do outro lado, ou None se este ponto for do
    # meio da face (ou desconhecido).
    #

    return _MIRROR_LOOKUP.get(name)


def is_neutral(name):

    return name in NEUTRAL_POINTS


def points_to_place():

    #
    # Quantos pontos o usuário realmente clica com a simetria
    # ligada: os do meio + um lado de cada par. O outro lado sai
    # de graça.
    #

    return len(NEUTRAL_POINTS) + len(MIRROR_PAIRS)


def total_points():

    #
    # Quantos pontos o template espera no total. Serve pro painel
    # mostrar "18 de 27" sem precisar importar POINT_NAMES lá de
    # dentro do operator.
    #

    return len(NEUTRAL_POINTS) + 2 * len(MIRROR_PAIRS)


def validate_point_names(point_names):

    #
    # Devolve (nao_classificados, faltando_no_template).
    #
    # O primeiro pega um ponto novo em POINT_NAMES que ninguém
    # lembrou de classificar aqui; o segundo pega o contrário --
    # uma tabela daqui citando um nome que não existe mais em
    # POINT_NAMES (ex.: alguém corrigiu o typo "Rigth_Ear_Anchor"
    # no .blend e esqueceu deste arquivo).
    #

    known = set(NEUTRAL_POINTS) | set(_MIRROR_LOOKUP)

    names = set(point_names)

    unclassified = sorted(names - known)

    missing = sorted(known - names)

    return unclassified, missing


# -------------------------------------------------------------

def transform(matrix, point):

    #
    # Multiplica um ponto (x, y, z) por uma matriz 4x4, tratando
    # o ponto como posição (w=1). Aceita qualquer matriz
    # indexável [linha][coluna] -- inclusive um mathutils.Matrix
    # -- e devolve uma tupla, sem depender de mathutils.
    #

    x, y, z = point

    return (
        matrix[0][0] * x + matrix[0][1] * y +
        matrix[0][2] * z + matrix[0][3],

        matrix[1][0] * x + matrix[1][1] * y +
        matrix[1][2] * z + matrix[1][3],

        matrix[2][0] * x + matrix[2][1] * y +
        matrix[2][2] * z + matrix[2][3],
    )


def mirror_world_position(matrix_world, matrix_world_inv, world_co, axis):

    #
    # Reflete uma posição de mundo em torno do plano local do
    # objeto: leva pro espaço local, inverte o sinal do eixo
    # escolhido, e volta pro mundo.
    #

    local = list(transform(matrix_world_inv, world_co))

    index = AXIS_INDEX[axis]

    local[index] = -local[index]

    return transform(matrix_world, local)


def snap_world_position(matrix_world, matrix_world_inv, world_co, axis):

    #
    # Gruda uma posição de mundo no plano de simetria: leva pro
    # espaço local, zera o eixo escolhido, e volta pro mundo.
    # Usado nos pontos do meio da face.
    #

    local = list(transform(matrix_world_inv, world_co))

    index = AXIS_INDEX[axis]

    local[index] = 0.0

    return transform(matrix_world, local)
