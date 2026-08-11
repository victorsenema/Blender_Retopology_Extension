import bpy


#
# Nomes dos modifiers que este addon gerencia, e a ordem final
# desejada entre eles no stack: Subdivision -> Shrinkwrap ->
# Relax (subdivide primeiro pra ter mais resolução antes de
# projetar na superfície esculpida, projeta, e só então relaxa
# o resultado já colado).
#
# Fonte única de verdade -- subdivision.py, projection.py e
# relax.py importam os nomes daqui em vez de cada um definir o
# próprio, e chamam enforce_order() depois de criar/alterar seu
# modifier. Assim a ordem nunca desalinha, não importa a
# sequência de cliques do usuário (ex.: adicionar Subdivision
# DEPOIS de já ter Shrinkwrap e Relax ativos, ou rodar
# "Apply Mesh" de novo em cima de um resultado que já tem os
# outros dois).
#

SUBDIVISION_MODIFIER_NAME = "RetopoSubdivision"
SHRINKWRAP_MODIFIER_NAME = "RetopoSurfaceProjection"
RELAX_MODIFIER_NAME = "RetopoRelax"

CANONICAL_ORDER = (
    SUBDIVISION_MODIFIER_NAME,
    SHRINKWRAP_MODIFIER_NAME,
    RELAX_MODIFIER_NAME,
)


def enforce_order(mesh_obj):

    modifiers = mesh_obj.modifiers

    target_index = 0

    for name in CANONICAL_ORDER:

        current_index = modifiers.find(name)

        if current_index == -1:
            continue

        if current_index != target_index:
            _move(mesh_obj, current_index, target_index)

        target_index += 1


# -------------------------------------------------------------

def _move(mesh_obj, from_index, to_index):

    modifiers = mesh_obj.modifiers

    #
    # modifiers.move() é a forma direta (Blender 2.90+), mas por
    # segurança -- caso não exista em alguma build específica --
    # cai pro operator nativo via context override.
    #

    try:

        modifiers.move(from_index, to_index)

        return

    except AttributeError:
        pass

    modifier = modifiers[from_index]

    view_layer = bpy.context.view_layer

    previous_active = view_layer.objects.active

    view_layer.objects.active = mesh_obj

    try:

        with bpy.context.temp_override(object=mesh_obj):

            bpy.ops.object.modifier_move_to_index(
                modifier=modifier.name,
                index=to_index,
            )

    finally:

        view_layer.objects.active = previous_active
