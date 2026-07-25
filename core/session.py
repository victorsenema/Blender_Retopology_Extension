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
