class CriticalPoint:

    def __init__(self, empty):

        self.name = empty.name
        self.empty = empty
        self.template_position = empty.matrix_world.translation.copy()