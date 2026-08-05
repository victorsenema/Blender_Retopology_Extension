import bpy
import bmesh


def apply_all_modifiers(mesh_obj):

    #
    # Finaliza TUDO que estiver no modifier stack (Shrinkwrap,
    # Relax, ou qualquer outro) de uma vez: avalia via depsgraph
    # e crava o resultado final no mesh.data ORIGINAL via bmesh
    # -- preserva UVs, materiais e o nome do datablock, em vez
    # de trocar mesh.data inteiro por um novo.
    #
    # Só funciona porque todos os modifiers que este addon usa
    # (Shrinkwrap, Corrective Smooth) são "deform-only": não
    # mudam topologia nem contagem de vértices, então o índice
    # bate 1-pra-1 com o mesh original.
    #

    if mesh_obj is None:
        return False

    if not mesh_obj.modifiers:
        return False

    depsgraph = bpy.context.evaluated_depsgraph_get()

    evaluated_obj = mesh_obj.evaluated_get(depsgraph)

    evaluated_mesh = evaluated_obj.to_mesh()

    bm = bmesh.new()

    bm.from_mesh(mesh_obj.data)

    bm.verts.ensure_lookup_table()

    moved_vertices = 0

    for index, evaluated_vertex in enumerate(evaluated_mesh.vertices):

        bm.verts[index].co = evaluated_vertex.co.copy()

        moved_vertices += 1

    evaluated_obj.to_mesh_clear()

    mesh_obj.modifiers.clear()

    bm.to_mesh(mesh_obj.data)

    mesh_obj.data.update()

    bm.free()

    print(
        f"[Finalize] {moved_vertices} vertices finalizados, "
        f"modifiers removidos."
    )

    return True
