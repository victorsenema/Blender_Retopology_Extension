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
        # Strcuture_Critical_Points). Guardadas pra que a limpeza
        # depois do Apply Mesh saiba exatamente quais coleções são
        # do addon -- ver Fitting.destroy_critical_points() e
        # core/scene_collections.purge_if_empty().
        #

        self.collections = []

        self.mesh = None

        self.critical_points = []
