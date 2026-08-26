"""
Verificacao offline da matematica do vertex_control.py.

Nao precisa de Blender: build_adjacency / compute_geodesic_distances /
falloff_weights so tocam mesh_obj atraves de foreach_get e matrix_world,
entao da pra alimentar com uma malha falsa (grade NxN) e conferir os
numeros contra o valor esperado na mao.
"""

import importlib.util
import math
import os
import sys

PROJECT = sys.argv[1]

# nao deixar __pycache__ no projeto do usuario ao importar por caminho
sys.dont_write_bytecode = True

spec = importlib.util.spec_from_file_location(
    "vertex_control",
    os.path.join(PROJECT, "core", "fitting", "vertex_control.py"),
)
vc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vc)


# ---------------------------------------------------------------
# Malha falsa: grade N x N no plano XY, espacamento 1.0.
# Indice do vertice (linha, coluna) = linha * N + coluna.
# ---------------------------------------------------------------

class FakeCollection:
    def __init__(self, values, count):
        self._values = values
        self._count = count

    def __len__(self):
        return self._count

    def foreach_get(self, attr, out):
        out[:] = self._values


class FakeMesh:
    def __init__(self, coords, edges, vertex_count):
        self.vertices = FakeCollection(coords, vertex_count)
        self.edges = FakeCollection(edges, len(edges) // 2)


class FakeObject:
    def __init__(self, mesh, matrix):
        self.data = mesh
        self.matrix_world = matrix


def identity():
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def scaled(factor):
    m = identity()
    m[0][0] = factor
    m[1][1] = factor
    m[2][2] = factor
    return m


def make_grid(n):
    coords = []
    for row in range(n):
        for col in range(n):
            coords.extend([float(col), float(row), 0.0])

    edges = []
    for row in range(n):
        for col in range(n):
            index = row * n + col
            if col + 1 < n:
                edges.extend([index, index + 1])
            if row + 1 < n:
                edges.extend([index, index + n])

    return FakeMesh(coords, edges, n * n), coords


failures = []


def check(label, condition, detail=""):
    if condition:
        print(f"  ok   {label}")
    else:
        print(f"  FALHA {label} {detail}")
        failures.append(label)


N = 9
CENTER = (N // 2) * N + (N // 2)   # vertice do meio da grade

mesh, _ = make_grid(N)
obj = FakeObject(mesh, identity())

print("build_adjacency")
adjacency = vc.build_adjacency(obj)

check(
    "vertice do meio tem 4 vizinhos",
    sorted(adjacency[CENTER]) == sorted(
        [CENTER - 1, CENTER + 1, CENTER - N, CENTER + N]
    ),
    adjacency[CENTER],
)
check("canto tem 2 vizinhos", len(adjacency[0]) == 2, adjacency[0])
check(
    "borda tem 3 vizinhos",
    len(adjacency[N // 2]) == 3,
    adjacency[N // 2],
)

print("compute_geodesic_distances")
distances = vc.compute_geodesic_distances(obj, adjacency, CENTER, 3.5)

check("seed tem distancia 0", distances[CENTER] == 0.0)
check(
    "vizinho direto = 1.0",
    abs(distances[CENTER + 1] - 1.0) < 1e-9,
    distances[CENTER + 1],
)
check(
    "diagonal = 2.0 (anda pela aresta, nao em linha reta)",
    abs(distances[CENTER + N + 1] - 2.0) < 1e-9,
    distances.get(CENTER + N + 1),
)
check(
    "nada alem do limite entrou",
    all(d <= 3.5 + 1e-9 for d in distances.values()),
    max(distances.values()),
)
check(
    "vertice a 4 passos ficou de fora",
    (CENTER + 4) not in distances,
)

print("escala da matrix_world")
scaled_obj = FakeObject(mesh, scaled(2.0))
scaled_distances = vc.compute_geodesic_distances(
    scaled_obj, adjacency, CENTER, 7.0
)
check(
    "objeto com escala 2x dobra as distancias (mundo, nao local)",
    abs(scaled_distances[CENTER + 1] - 2.0) < 1e-9,
    scaled_distances[CENTER + 1],
)

print("falloff_weights")
radius = 3.0
weights = vc.falloff_weights(distances, radius, set(), CENTER)

check("seed nao entra nos pesos", CENTER not in weights)
check(
    "vizinho colado tem peso alto",
    weights[CENTER + 1] > 0.7,
    weights[CENTER + 1],
)
check(
    "peso cai com a distancia",
    weights[CENTER + 1] > weights[CENTER + 2],
)
check(
    "peso vai a zero exatamente na borda do raio (sem degrau)",
    all(w > 0.0 for w in weights.values()) and
    max(d for i, d in distances.items() if i in weights) < radius,
)

on_edge = [
    (i, d) for i, d in distances.items()
    if abs(d - radius) < 1e-9
]
check(
    "vertice exatamente no raio recebe peso 0 (fica de fora)",
    all(i not in weights for i, _ in on_edge),
    on_edge[:3],
)

expected = None
for index, distance in distances.items():
    if abs(distance - 2.0) < 1e-9 and index in weights:
        factor = 1.0 - (2.0 / radius)
        expected = factor * factor * (3.0 - 2.0 * factor)
        check(
            "smoothstep bate com a formula",
            abs(weights[index] - expected) < 1e-12,
            (weights[index], expected),
        )
        break

check("achou vertice pra conferir a formula", expected is not None)

print("exclusao de pontos de controle")
control = {CENTER + 1, CENTER - 1}
weights_excluded = vc.falloff_weights(distances, radius, control, CENTER)
check(
    "pontos de controle vizinhos ficam de fora por padrao",
    (CENTER + 1) not in weights_excluded and
    (CENTER - 1) not in weights_excluded,
)
check(
    "malha livre continua reagindo",
    (CENTER + N) in weights_excluded,
)

weights_included = vc.falloff_weights(
    distances, radius, control, CENTER, affect_control_points=True
)
check(
    "com affect_control_points=True eles voltam",
    (CENTER + 1) in weights_included,
)

print("raio zero / degenerado")
check(
    "raio 0 nao move ninguem",
    vc.falloff_weights(distances, 0.0, set(), CENTER) == {},
)

print("world_positions / mean_edge_length")

positions = vc.world_positions(obj)

check(
    "world_positions devolve uma tupla por vertice",
    len(positions) == N * N and len(positions[0]) == 3,
    (len(positions), positions[0]),
)
check(
    "com identidade, a posicao de mundo e a local",
    positions[CENTER] == (float(N // 2), float(N // 2), 0.0),
    positions[CENTER],
)
check(
    "com escala 2x, a posicao de mundo dobra",
    vc.world_positions(scaled_obj)[CENTER] == (
        float(N // 2) * 2.0,
        float(N // 2) * 2.0,
        0.0,
    ),
    vc.world_positions(scaled_obj)[CENTER],
)

#
# Grade de espacamento 1.0: toda aresta mede exatamente 1, entao a
# media tem que ser 1 -- e 2 com o objeto escalado, porque a
# medida e em espaco de MUNDO.
#

check(
    "espacamento medio da grade = 1.0",
    abs(vc.mean_edge_length(obj) - 1.0) < 1e-9,
    vc.mean_edge_length(obj),
)
check(
    "espacamento medio acompanha a escala do objeto",
    abs(vc.mean_edge_length(scaled_obj) - 2.0) < 1e-9,
    vc.mean_edge_length(scaled_obj),
)

print()
if failures:
    print(f"{len(failures)} FALHA(S): {failures}")
    sys.exit(1)

print("todos os testes passaram")
