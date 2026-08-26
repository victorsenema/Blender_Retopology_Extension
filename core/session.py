# Estado global da sessão do addon.
#
# Módulo simples (não uma classe) de propósito: precisa
# sobreviver entre cliques de operator diferentes, e módulos
# Python já funcionam como singleton naturalmente.
#
# Cuidado com Undo: referências a objetos do Blender guardadas
# aqui podem "morrer" depois de um Ctrl+Z. Ver core/blender_utils.is_valid().

critical_points = []

target_mesh = None
template = None

#
# Nome da malha do template, guardado à parte da referência.
#
# String sobrevive a Undo; referência pra objeto do Blender não
# (ver core/blender_utils.is_valid). Depois de um Ctrl+Z o
# datablock é recriado com o MESMO nome, então o nome é o que
# permite reencontrar o objeto e consertar a referência -- é a
# mesma ideia de reler os critical points da coleção, aplicada à
# malha.
#

template_mesh_name = None


def resolve_template_mesh():

    #
    # A malha do template, com a referência curada se ela morreu.
    #
    # Sem isso, um Ctrl+Z fazia os marcadores do ajuste fino
    # sumirem e o Nudge recusar rodar ("a malha foi removida da
    # cena") -- com a malha visivelmente ali na tela. Todo mundo
    # que precisa da malha deve passar por aqui, e não ler
    # session.template.mesh direto.
    #

    import bpy

    from .blender_utils import is_valid

    if template is not None and is_valid(template.mesh):
        return template.mesh

    if not template_mesh_name:
        return None

    recovered = bpy.data.objects.get(template_mesh_name)

    if recovered is None or recovered.type != 'MESH':
        return None

    if template is not None:
        template.mesh = recovered

    print(
        f"[session] referência da malha do template recuperada pelo "
        f"nome ('{template_mesh_name}') -- provavelmente depois de um "
        f"Undo."
    )

    return recovered
