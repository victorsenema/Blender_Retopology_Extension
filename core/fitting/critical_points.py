class CriticalPoint:

    #
    # Wrapper fino em volta de um Empty do Blender -- só guarda
    # nome e referência. Usado tanto pros pontos do template
    # (vindos do VG_Template.blend, ver template_manager.py)
    # quanto pros pontos que o usuário posiciona (Landmarking,
    # ver operators/OPERATOR_create_critical_points.py). O
    # casamento entre os dois lados acontece por nome
    # normalizado (core/blender_utils.normalize_point_name),
    # usado em alignment.py e structure_warp.py.
    #

    def __init__(self, empty):

        self.name = empty.name

        self.empty = empty
