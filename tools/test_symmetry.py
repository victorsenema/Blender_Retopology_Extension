"""
Verificacao offline do symmetry.py.

Nao precisa de Blender: o modulo nao importa bpy nem mathutils --
recebe a matriz do objeto como algo indexavel [linha][coluna] e
devolve tuplas, exatamente pra poder ser testado aqui.

O teste mais util deste arquivo e o primeiro: le POINT_NAMES
direto do source do operator (via AST, sem importar bpy) e confere
contra as tabelas de symmetry.py. Se alguem adicionar um landmark
no template e esquecer de classifica-lo, isso quebra aqui em vez
de espelhar metade dos pontos em silencio dentro do Blender.
"""

import ast
import importlib.util
import io
import os
import sys

PROJECT = sys.argv[1]

sys.dont_write_bytecode = True

spec = importlib.util.spec_from_file_location(
    "symmetry",
    os.path.join(PROJECT, "core", "fitting", "symmetry.py"),
)
sym = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sym)


failures = []


def check(label, condition, detail=""):
    if condition:
        print(f"  ok   {label}")
    else:
        print(f"  FALHA {label} {detail}")
        failures.append(label)


def read_point_names():
    """POINT_NAMES do operator, lido do source sem importar bpy."""
    path = os.path.join(
        PROJECT, "operators", "OPERATOR_create_critical_points.py"
    )
    tree = ast.parse(io.open(path, encoding="utf-8").read(), path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "POINT_NAMES":
                    return ast.literal_eval(node.value)
    raise AssertionError("POINT_NAMES nao encontrado no operator")


# ---------------------------------------------------------------
print("tabelas x POINT_NAMES do operator")

POINT_NAMES = read_point_names()

unclassified, missing = sym.validate_point_names(POINT_NAMES)

check(
    "todo ponto de POINT_NAMES esta classificado",
    not unclassified,
    unclassified,
)
check(
    "toda entrada das tabelas existe em POINT_NAMES",
    not missing,
    missing,
)
check(
    f"total bate ({sym.total_points()} pontos)",
    sym.total_points() == len(POINT_NAMES),
    (sym.total_points(), len(POINT_NAMES)),
)
check(
    f"com simetria o usuario clica {sym.points_to_place()} de "
    f"{len(POINT_NAMES)}",
    sym.points_to_place() == len(POINT_NAMES) - len(sym.MIRROR_PAIRS),
)

neutral = set(sym.NEUTRAL_POINTS)
paired = {name for pair in sym.MIRROR_PAIRS for name in pair}

check(
    "nenhum ponto e neutro E espelhado ao mesmo tempo",
    not (neutral & paired),
    neutral & paired,
)
check(
    "nenhum par repetido",
    len(paired) == 2 * len(sym.MIRROR_PAIRS),
)

# ---------------------------------------------------------------
print("get_mirror_name")

check(
    "espelhar duas vezes volta ao original",
    all(
        sym.get_mirror_name(sym.get_mirror_name(name)) == name
        for name in paired
    ),
)
check(
    "ponto neutro nao tem espelho",
    all(sym.get_mirror_name(name) is None for name in sym.NEUTRAL_POINTS),
)
check(
    "nome desconhecido devolve None",
    sym.get_mirror_name("NaoExiste") is None,
)
check(
    "o typo do template esta coberto",
    sym.get_mirror_name("Left_Ear_Anchor") == "Rigth_Ear_Anchor",
    sym.get_mirror_name("Left_Ear_Anchor"),
)
check(
    "is_neutral concorda com a tabela",
    sym.is_neutral("NoseTip") and not sym.is_neutral("JawLeft"),
)


# ---------------------------------------------------------------
def identity():
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


#
# Objeto girado 90 graus em Z e transladado -- o caso que importa:
# se o espelhamento fosse feito nos eixos do MUNDO em vez dos eixos
# LOCAIS do alvo, este teste falharia.
#
# world = R @ local + t, com R = rotacao de 90 graus em Z e
# t = (5, 2, 0). A inversa de um rigido e (R^T, -R^T t), escrita na
# mao aqui pra nao precisar de numpy.
#

def rotated():
    return [
        [0.0, -1.0, 0.0, 5.0],
        [1.0, 0.0, 0.0, 2.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def rotated_inverse():
    return [
        [0.0, 1.0, 0.0, -2.0],
        [-1.0, 0.0, 0.0, 5.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def close(a, b, tolerance=1e-9):
    return all(abs(x - y) < tolerance for x, y in zip(a, b))


print("transform")

check(
    "identidade nao muda o ponto",
    close(sym.transform(identity(), (1.0, 2.0, 3.0)), (1.0, 2.0, 3.0)),
)
check(
    "origem local vira a translacao do objeto",
    close(sym.transform(rotated(), (0.0, 0.0, 0.0)), (5.0, 2.0, 0.0)),
    sym.transform(rotated(), (0.0, 0.0, 0.0)),
)
check(
    "matriz inversa desfaz a direta",
    close(
        sym.transform(rotated_inverse(), sym.transform(rotated(), (3.0, -1.0, 7.0))),
        (3.0, -1.0, 7.0),
    ),
)

print("mirror_world_position")

check(
    "com identidade, espelhar em X so troca o sinal de x",
    close(
        sym.mirror_world_position(
            identity(), identity(), (2.0, 3.0, 4.0), "X"
        ),
        (-2.0, 3.0, 4.0),
    ),
)
check(
    "com identidade, espelhar em Y so troca o sinal de y",
    close(
        sym.mirror_world_position(
            identity(), identity(), (2.0, 3.0, 4.0), "Y"
        ),
        (2.0, -3.0, 4.0),
    ),
)

#
# Local (3, 0, 0) -> mundo (5, 5, 0). Espelhado em X local vira
# local (-3, 0, 0) -> mundo (5, -1, 0). Contas feitas na mao.
#
check(
    "objeto girado: espelha no eixo LOCAL, nao no do mundo",
    close(
        sym.mirror_world_position(
            rotated(), rotated_inverse(), (5.0, 5.0, 0.0), "X"
        ),
        (5.0, -1.0, 0.0),
    ),
    sym.mirror_world_position(
        rotated(), rotated_inverse(), (5.0, 5.0, 0.0), "X"
    ),
)
check(
    "espelhar duas vezes volta ao original",
    close(
        sym.mirror_world_position(
            rotated(),
            rotated_inverse(),
            sym.mirror_world_position(
                rotated(), rotated_inverse(), (5.0, 5.0, 3.0), "X"
            ),
            "X",
        ),
        (5.0, 5.0, 3.0),
    ),
)
check(
    "ponto no plano nao se move ao ser espelhado",
    close(
        sym.mirror_world_position(
            rotated(), rotated_inverse(), (5.0, 2.0, 1.0), "X"
        ),
        (5.0, 2.0, 1.0),
    ),
)

print("snap_world_position")

snapped = sym.snap_world_position(
    rotated(), rotated_inverse(), (5.0, 5.0, 3.0), "X"
)

check(
    "ponto travado cai no plano (x local = 0)",
    abs(sym.transform(rotated_inverse(), snapped)[0]) < 1e-9,
    sym.transform(rotated_inverse(), snapped),
)
check(
    "travar de novo nao muda nada (idempotente)",
    close(
        sym.snap_world_position(
            rotated(), rotated_inverse(), snapped, "X"
        ),
        snapped,
    ),
)
check(
    "travar preserva as outras coordenadas locais",
    close(
        sym.transform(rotated_inverse(), snapped)[1:],
        sym.transform(rotated_inverse(), (5.0, 5.0, 3.0))[1:],
    ),
)
check(
    "o ponto medio entre um par espelhado cai no plano",
    close(
        sym.snap_world_position(
            rotated(), rotated_inverse(), (5.0, 5.0, 0.0), "X"
        ),
        tuple(
            (a + b) / 2.0
            for a, b in zip(
                (5.0, 5.0, 0.0),
                sym.mirror_world_position(
                    rotated(), rotated_inverse(), (5.0, 5.0, 0.0), "X"
                ),
            )
        ),
    ),
)

print()
if failures:
    print(f"{len(failures)} FALHA(S): {failures}")
    sys.exit(1)

print("todos os testes passaram")
