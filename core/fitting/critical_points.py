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


def collect_from_collection(collection):

    #
    # Reconstrói a lista de critical points a partir da CENA, e
    # não da lista guardada em core/session.py.
    #
    # Referência Python pra objeto do Blender morre em silêncio
    # depois de um Ctrl+Z (ver core/blender_utils.is_valid), e era
    # exatamente isso que produzia o erro "Faltam pontos
    # obrigatórios no lado do usuário" no Apply Mesh: os Empties
    # continuavam na cena, mas a lista em memória apontava pra
    # referências mortas. Relendo a coleção
    # (core/scene_collections.USER_POINTS_NAME) na hora de usar, a cena
    # vira a fonte da verdade e o problema deixa de existir.
    #

    if collection is None:
        return []

    return [
        CriticalPoint(obj)
        for obj in collection.objects
        if obj.type == 'EMPTY'
    ]
