import bpy
import bmesh


class SurfaceProjection:

    #
    # Cola o template sobre a superfície esculpida (target_mesh)
    # usando o modifier Shrinkwrap nativo do Blender, no modo
    # PROJECT: cada vértice é projetado ao longo da própria
    # normal (não pelo ponto mais próximo em linha reta).
    #
    # Por que não nearest-point puro (versão antiga, via BVH):
    # nearest-point ignora direção -- um vértice na bochecha
    # esquerda pode grudar num pedaço de superfície da bochecha
    # direita, ou dentro da boca, sempre que essas partes
    # estiverem mais perto em distância reta do que a pele
    # "certa" na frente dele. Projetar ao longo da normal, com
    # um limite de distância de busca, evita isso -- é
    # exatamente o que ferramentas de wrap profissionais fazem.
    #

    def __init__(self, session):

        self.session = session

        self.template = session.template.mesh
        self.target = session.target_mesh

    # -------------------------------------------------------------

    def project(self):

        if self.template is None:
            return

        if self.target is None:
            return

        modifier = self.template.modifiers.new(
            name="RetopoSurfaceProjection",
            type='SHRINKWRAP'
        )

        modifier.target = self.target
        modifier.wrap_method = 'PROJECT'

        #
        # Projeta pra dentro e pra fora ao longo da normal --
        # depois do fit (Structure + Refinement), o vértice pode
        # estar tanto "afundado" quanto "saltando" em relação à
        # superfície real, então precisamos buscar nas duas
        # direções.
        #

        modifier.use_negative_direction = True
        modifier.use_positive_direction = True

        #
        # Limite de distância de busca, proporcional ao tamanho
        # da própria cabeça (evita colar num pedaço de superfície
        # muito distante / do lado errado, tipo o caso da bochecha
        # citado acima). 15% da maior dimensão é um ponto de
        # partida razoável -- ajustável se precisar.
        #

        head_size = max(self.template.dimensions)

        modifier.project_limit = head_size * 0.15

        project_limit = modifier.project_limit

        #
        # Avalia o modifier (via depsgraph) e copia o resultado
        # de volta pro mesh.data ORIGINAL via bmesh -- assim
        # preservamos UVs, materiais e o nome do datablock, em
        # vez de trocar mesh.data inteiro por um novo.
        #

        depsgraph = bpy.context.evaluated_depsgraph_get()

        evaluated_obj = self.template.evaluated_get(depsgraph)

        evaluated_mesh = evaluated_obj.to_mesh()

        bm = bmesh.new()

        bm.from_mesh(self.template.data)

        bm.verts.ensure_lookup_table()

        moved_vertices = 0

        for index, evaluated_vertex in enumerate(evaluated_mesh.vertices):

            #
            # Shrinkwrap é um modifier "deform-only": não muda
            # topologia nem contagem de vértices, então o índice
            # bate 1-pra-1 com o mesh original.
            #

            bm.verts[index].co = evaluated_vertex.co.copy()

            moved_vertices += 1

        evaluated_obj.to_mesh_clear()

        self.template.modifiers.remove(modifier)

        bm.to_mesh(self.template.data)

        self.template.data.update()

        bm.free()

        print(
            f"[SurfaceProjection] {moved_vertices} vertices "
            f"projetados (project_limit={project_limit:.4f})"
        )
