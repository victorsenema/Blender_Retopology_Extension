class Template:

    def __init__(self):

        #
        # Todos os objetos importados do .blend (malha +
        # critical points), usados quando uma transformação
        # precisa mover tudo junto (ex.: Alignment).
        #

        self.objects = []

        #
        # Coleções importadas do .blend (Template_Mesh e
        # Strcuture_Critical_Points). Guardadas pra saber o que é
        # do addon nesta rodada. A limpeza NÃO acontece mais no
        # fim do Apply Mesh -- mexer em coleção dentro do pipeline
        # foi um dos suspeitos do crash no rebuild de parentesco
        # durante o undo. Ver o aviso no topo do Notes.txt e
        # operators/OPERATOR_reset_scene.py.
        #

        self.collections = []

        self.mesh = None

        self.critical_points = []
