class Template:

    def __init__(self):

        #
        # Todos os objetos importados do .blend (malha +
        # critical points), usados quando uma transformação
        # precisa mover tudo junto (ex.: Alignment).
        #

        self.objects = []

        self.mesh = None

        self.critical_points = []
