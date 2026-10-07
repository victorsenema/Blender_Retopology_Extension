import numpy as np


class ThinPlateSpline:

    #
    # Warp global suave (Thin Plate Spline, 3D) entre um
    # conjunto pequeno de pontos de controle (landmarks).
    #
    # Somar translações ponderadas por Gaussianas locais (cada
    # uma "puxando" pro seu lado, sem noçdão o que as outras
    # estão fazendo) facilmente dobra/cruza a malha nas regiões
    # entre landmarks distantes.
    #
    # TPS resolve o warp inteiro de uma vez, minimizando energia
    # de dobra sujeito a bater exatamente nos landmarks -- é a
    # interpolação mais suave possível pra esse tipo de
    # correspondência esparsa, e é a mesma ideia usada por
    # ferramentas de wrap profissionais (Wrap3/R3DS) pra colar
    # um template numa malha alvo a partir de poucos pontos.
    #

    def __init__(self, source_points, target_points, regularization=1e-6):

        self.source = np.array(
            [tuple(p) for p in source_points],
            dtype=np.float64
        )

        target = np.array(
            [tuple(p) for p in target_points],
            dtype=np.float64
        )

        self._solve(target, regularization)

    # -------------------------------------------------------------

    def _kernel(self, r):

        #
        # Solução fundamental do operador biharmônico em 3D
        # (dimensão ímpar) é phi(r) = r -- diferente do caso 2D
        # clássico (phi(r) = r² log r).
        #

        return r

    # -------------------------------------------------------------

    def _solve(self, target, regularization):

        n = len(self.source)

        diff = self.source[:, None, :] - self.source[None, :, :]

        dist = np.sqrt((diff ** 2).sum(-1))

        K = self._kernel(dist)

        ones_column = np.ones((n, 1))

        P = np.hstack([self.source, ones_column])

        L = np.zeros((n + 4, n + 4))

        L[:n, :n] = K
        L[:n, n:] = P
        L[n:, :n] = P.T

        #
        # Regularização pequena na diagonal do bloco K --
        # estabiliza numericamente sem distorcer o resultado
        # visivelmente, evita erro caso dois landmarks fiquem
        # muito perto um do outro.
        #

        L[:n, :n] += np.eye(n) * regularization

        Y = np.zeros((n + 4, 3))
        Y[:n, :] = target

        solution = np.linalg.solve(L, Y)

        self.w = solution[:n]
        self.a = solution[n:]

    # -------------------------------------------------------------

    def evaluate(self, points):

        pts = np.array(
            [tuple(p) for p in points],
            dtype=np.float64
        )

        diff = pts[:, None, :] - self.source[None, :, :]

        dist = np.sqrt((diff ** 2).sum(-1))

        U = self._kernel(dist)

        nonlinear = U @ self.w

        affine_input = np.hstack(
            [pts, np.ones((len(pts), 1))]
        )

        linear = affine_input @ self.a

        return nonlinear + linear
