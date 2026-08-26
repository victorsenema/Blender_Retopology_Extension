import bpy

from ..core import session
from ..core.blender_utils import is_valid
from ..core.fitting.modifier_stack import (
    SHRINKWRAP_MODIFIER_NAME,
    SUBDIVISION_MODIFIER_NAME,
)
from ..core.fitting.symmetry import points_to_place, total_points
from ..core.fitting.vertex_control import has_topology_changing_modifier


class RETOPOLOGY_PT_panel(bpy.types.Panel):
    bl_label = "Retopology"
    bl_idname = "RETOPOLOGY_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Retopology"

    def draw(self, context):

        layout = self.layout

        layout.label(text="Target")

        layout.prop(
            context.scene,
            "retopo_target",
            text=""
        )

        layout.separator()

        layout.label(text="Landmarking")

        self.draw_symmetry(context, layout)

        layout.operator(
            "retopo.create_critical_points",
            text="Create Critical Points",
            icon='EMPTY_AXIS'
        )

        layout.separator()

        layout.label(text="Template")

        layout.operator(
            "retopo.test_inside_nose_and_nostrils",
            text="Apply Mesh",
            icon='MESH_GRID'
        )

        layout.separator()

        self.draw_fine_tuning(context, layout)

        layout.separator()

        #
        # Ordem no painel espelha a ordem no modifier stack:
        # Subdivision -> Shrinkwrap (acima) -> Relax.
        #
        # OBS.: o botão/slider de Relax foi escondido do painel a
        # pedido (só visualmente -- core/fitting/relax.py e
        # operators/OPERATOR_relax_mesh.py continuam intactos,
        # registrados, e utilizáveis via busca de operator/F3).
        # Perguntar ao usuário o que fazer com o relaxamento
        # (trazer de volta pro painel, mudar de abordagem, ou
        # remover de vez) numa próxima sessão.
        #

        layout.label(text="Subdivision")

        layout.operator(
            "retopo.add_subdivision",
            text="Add Subdivision",
            icon='MOD_SUBSURF'
        )

        subdivision_modifier = self.get_modifier(SUBDIVISION_MODIFIER_NAME)

        if subdivision_modifier is not None:

            layout.prop(
                subdivision_modifier,
                "levels",
                text="Subdivision Level"
            )

        layout.separator()

        layout.operator(
            "retopo.apply_modifiers",
            text="Apply Modifiers",
            icon='CHECKMARK'
        )

        layout.separator()

        #
        # Limpeza da cena. Fica separado e em vermelho de propósito
        # -- é destrutivo, pede confirmação, e apaga a malha do
        # template junto (que é onde mora o resultado). Ver
        # operators/OPERATOR_reset_scene.py.
        #

        row = layout.row()

        row.alert = True

        row.operator(
            "retopo.reset_scene",
            text="Reset (limpar cena)",
            icon='TRASH'
        )

    # -----------------------------------------------------------

    def draw_symmetry(self, context, layout):

        #
        # Cabeça espelhada: o usuário clica só um lado e o ponto
        # do outro lado nasce junto, seguindo o mouse em tempo
        # real; os pontos do meio da face ficam travados no plano
        # de simetria. Ver core/fitting/symmetry.py e o operator
        # do Landmarking.
        #
        # O plano é o plano LOCAL do objeto alvo -- a mesma
        # referência do sculpt simétrico do Blender -- por isso o
        # Target precisa estar escolhido antes.
        #

        scene = context.scene

        layout.prop(scene, "retopo_symmetric", text="Objeto Espelhado")

        if not scene.retopo_symmetric:
            return

        row = layout.row(align=True)

        row.prop(scene, "retopo_mirror_axis", expand=True)

        if scene.retopo_target is None:

            box = layout.box()

            box.label(text="Escolha o Target antes:", icon='ERROR')
            box.label(text="o plano vem do objeto alvo.")

            return

        layout.label(
            text=f"{points_to_place()} cliques de {total_points()} pontos"
        )

    # -----------------------------------------------------------

    def draw_fine_tuning(self, context, layout):

        #
        # Ajuste fino: arrasta direto os vértices em destaque (ver
        # ui/vertex_highlight.py) dos vertex groups de controle
        # (Nose_VG/Face_VG/Eyes_VG/Mouth_VG), como um Proportional
        # Editing em Object Mode. Só faz sentido DEPOIS do Apply
        # Mesh (que traz a malha com esses grupos já pintados) e
        # ANTES do Apply Modifiers (que crava Shrinkwrap/
        # Subdivision e reconstrói a malha a partir do resultado
        # avaliado -- ver finalize.py -- perdendo a correspondência
        # de vertex group nesse processo).
        #

        layout.label(text="Fine-Tuning")

        template_mesh = self.get_template_mesh()

        #
        # A seção inteira fica desabilitada (cinza) enquanto não
        # existe malha de template -- é mais honesto que deixar
        # clicar pra receber um erro dizendo "rode o Apply Mesh
        # antes".
        #

        column = layout.column()

        column.enabled = template_mesh is not None

        if template_mesh is not None:

            #
            # Wireframe do template por cima da malha esculpida --
            # liga show_wire (desenha as arestas) + show_in_front
            # (ignora profundidade, aparece por cima de tudo)
            # direto no objeto. É a mesma dupla de properties que
            # o "In Front" do painel Object Properties > Viewport
            # Display usa -- só exposta aqui pra não precisar sair
            # do painel da Retopology.
            #

            row = column.row(align=True)

            row.prop(
                template_mesh,
                "show_wire",
                text="Wireframe",
                toggle=True
            )

            row.prop(
                template_mesh,
                "show_in_front",
                text="Show In Front",
                toggle=True
            )

        #
        # Liga/desliga o Shrinkwrap SEM removê-lo do stack.
        #
        # Por que isso fica aqui, junto do Nudge: o Shrinkwrap
        # (modo PROJECT) reprojeta cada vértice na malha alvo
        # depois de QUALQUER mudança. Arrastar um vértice pra
        # dentro ou pra fora da superfície não produz efeito
        # nenhum -- ele volta na hora. Só o deslizamento ao longo
        # da superfície "pega".
        #
        # Isso é o comportamento correto pro resultado final (a
        # malha tem que ficar colada no alvo), mas atrapalha na
        # hora de entender o que está acontecendo, e às vezes
        # atrapalha o próprio ajuste. Desligando aqui, você edita
        # a malha diretamente e vê o que está fazendo; religando,
        # o Shrinkwrap recola tudo no alvo. O modifier continua no
        # stack o tempo todo, então o Apply Modifiers no fim
        # produz o mesmo resultado.
        #

        shrinkwrap = self.get_modifier(SHRINKWRAP_MODIFIER_NAME)

        if shrinkwrap is not None:

            row = column.row(align=True)

            row.prop(
                shrinkwrap,
                "show_viewport",
                text="Shrinkwrap ativo",
                toggle=True
            )

        column.operator(
            "retopo.nudge_vertex",
            text="Nudge Vertex",
            icon='VIEW_PAN'
        )

        column.prop(
            context.scene,
            "retopo_nudge_radius",
            text="Influence Radius"
        )

        column.prop(
            context.scene,
            "retopo_nudge_affect_control",
            text="Affect Control Points"
        )

        #
        # Aviso: com Subdivision ativa a malha avaliada tem outra
        # contagem de vértices, então não dá pra saber onde cada
        # vértice de controle foi parar depois dos modifiers -- o
        # destaque cai pra posição da malha base e os pontos podem
        # aparecer afastados da superfície que se vê. Ver
        # vertex_control.get_display_positions().
        #

        if (
            template_mesh is not None and
            has_topology_changing_modifier(template_mesh)
        ):

            box = layout.box()

            box.label(text="Subdivision ativa:", icon='INFO')
            box.label(text="pontos na posicao da malha base.")

    # -----------------------------------------------------------

    def get_modifier(self, modifier_name):

        mesh = self.get_template_mesh()

        if mesh is None:
            return None

        return mesh.modifiers.get(modifier_name)

    # -----------------------------------------------------------

    def get_template_mesh(self):

        mesh = session.resolve_template_mesh()

        if not is_valid(mesh):
            return None

        return mesh
