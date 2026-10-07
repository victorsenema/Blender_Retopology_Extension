import bpy
import bmesh


def apply_all_modifiers(mesh_obj):

    #
    # Finaliza TUDO que estiver no modifier stack (Subdivision,
    # Shrinkwrap, ou qualquer outro) de uma vez: avalia
    # via depsgraph e substitui o CONTEÚDO do mesh.data original
    # pelo resultado avaliado inteiro (vértices, faces, UVs).
    #
    # Não dá pra só copiar posição de vértice pra dentro de um
    # bmesh construído a partir da malha original (técnica válida
    # só quando todo modifier é "deform-only", tipo Shrinkwrap e
    # Corrective Smooth): Subdivision Surface muda a topologia
    # (adiciona vértice/face), então o índice já não bate 1-pra-1
    # com a malha original -- por isso reconstruímos o bmesh a
    # partir do resultado AVALIADO, não do original.
    #
    # O nome do datablock (mesh_obj.data) é preservado porque
    # continuamos escrevendo NELE via bm.to_mesh(), só o conteúdo
    # é trocado.
    #

    if mesh_obj is None:
        return False

    if not mesh_obj.modifiers:
        return False

    depsgraph = bpy.context.evaluated_depsgraph_get()

    evaluated_obj = mesh_obj.evaluated_get(depsgraph)

    evaluated_mesh = evaluated_obj.to_mesh()

    bm = bmesh.new()

    bm.from_mesh(evaluated_mesh)

    evaluated_obj.to_mesh_clear()

    mesh_obj.modifiers.clear()

    bm.to_mesh(mesh_obj.data)

    mesh_obj.data.update()

    vertex_count = len(bm.verts)

    bm.free()

    print(
        f"[Finalize] malha finalizada com {vertex_count} vertices, "
        f"modifiers removidos."
    )

    return True
