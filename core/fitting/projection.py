import bpy
import bmesh


class SurfaceProjection:

    #
    # Cola o template sobre a superfície esculpida (target_mesh)
    # usando o modifier Shrinkwrap nativo do Blender, no modo
    # PROJECT: cada vértice é projetado ao longo da própria
    # normal (não pelo ponto mais próximo em linha reta).
    #
    # Por que não nearest-point puro: nearest-point ignora
    # direção -- um vértice na bochecha esquerda pode grudar num
    # pedaço de superfície da bochecha direita, ou dentro da
    # boca, sempre que essas partes estiverem mais perto em
    # distância reta do que a pele "certa" na frente dele.
    # Projetar ao longo da normal, com um limite de distância de
    # busca, evita isso.
    #
    # O modifier fica só ADICIONADO/configurado (add_modifier),
    # sem ser aplicado -- assim o resultado é sempre uma preview
    # ao vivo, editável, e o usuário decide quando finalizar
    # (botão "Apply Modifiers", ver apply_modifier() e
    # operators/OPERATOR_apply_modifiers.py).
    #

    MODIFIER_NAME = "RetopoSurfaceProjection"

    def __init__(self, session):

        self.session = session

        self.template = session.template.mesh
        self.target = session.target_mesh

    # -------------------------------------------------------------

    def add_modifier(self):

        if self.template is None:
            return None

        if self.target is None:
            return None

        #
        # Roda de novo em cima de um resultado anterior (ex.:
        # "Apply Mesh" clicado duas vezes) não deve empilhar
        # modifiers -- substitui o anterior.
        #

        existing = self.template.modifiers.get(self.MODIFIER_NAME)

        if existing is not None:
            self.template.modifiers.remove(existing)

        modifier = self.template.modifiers.new(
            name=self.MODIFIER_NAME,
            type='SHRINKWRAP'
        )

        modifier.target = self.target
        modifier.wrap_method = 'PROJECT'

        #
        # Projeta pra dentro e pra fora ao longo da normal --
        # depois do warp TPS, o vértice pode estar tanto
        # "afundado" quanto "saltando" em relação à superfície
        # real, então precisamos buscar nas duas direções.
        #

        modifier.use_negative_direction = True
        modifier.use_positive_direction = True

        #
        # Limite de distância de busca, proporcional ao tamanho
        # da própria cabeça (evita colar num pedaço de superfície
        # muito distante / do lado errado, tipo o caso da bochecha
        # citado acima).
        #

        head_size = max(self.template.dimensions)

        modifier.project_limit = head_size * 0.08

        print(
            f"[SurfaceProjection] modifier Shrinkwrap adicionado "
            f"(project_limit={modifier.project_limit:.4f}) -- "
            f"ainda NÃO aplicado, use 'Apply Modifiers' pra finalizar."
        )

        return modifier

    # -------------------------------------------------------------

    @staticmethod
    def apply_modifier(mesh_obj, modifier_name=MODIFIER_NAME):

        #
        # Finaliza o modifier: avalia via depsgraph e copia o
        # resultado de volta pro mesh.data ORIGINAL via bmesh --
        # assim preservamos UVs, materiais e o nome do
        # datablock, em vez de trocar mesh.data inteiro por um
        # novo. Depois disso o Shrinkwrap deixa de existir como
        # modifier (virou geometria de verdade).
        #

        if mesh_obj is None:
            return False

        modifier = mesh_obj.modifiers.get(modifier_name)

        if modifier is None:
            return False

        depsgraph = bpy.context.evaluated_depsgraph_get()

        evaluated_obj = mesh_obj.evaluated_get(depsgraph)

        evaluated_mesh = evaluated_obj.to_mesh()

        bm = bmesh.new()

        bm.from_mesh(mesh_obj.data)

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

        mesh_obj.modifiers.remove(modifier)

        bm.to_mesh(mesh_obj.data)

        mesh_obj.data.update()

        bm.free()

        print(
            f"[SurfaceProjection] modifier aplicado -- "
            f"{moved_vertices} vertices finalizados"
        )

        return True
