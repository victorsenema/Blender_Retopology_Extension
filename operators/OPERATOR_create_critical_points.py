import bpy
from bpy_extras import view3d_utils

from ..core import scene_collections
from ..core.blender_utils import is_valid
from ..core.fitting import symmetry_link
from ..core.fitting.critical_points import CriticalPoint
from ..core.fitting.symmetry import (
    get_mirror_name,
    is_neutral,
    mirror_world_position,
    snap_world_position,
    transform,
    validate_point_names,
)
from ..core import session


class OPERATOR_create_critical_points(bpy.types.Operator):

    #
    # Posicionamento modal + ray cast: clique esquerdo em
    # qualquer malha visível cria/avança um Empty por vez, na
    # ordem de POINT_NAMES. Precisa bater EXATAMENTE (mesmo
    # texto, mesma capitalização) com os nomes dos Empties
    # dentro da coleção "Strcuture_Critical_Points" do
    # VG_Template.blend -- é por esse nome que
    # core/fitting/structure_warp.py casa cada ponto do template
    # com o ponto do usuário. Typos como "Rigth_Ear_Anchor" são
    # do arquivo original e foram mantidos de propósito.
    #
    # Não define mais session.target_mesh a partir do ray cast
    # -- a malha alvo do Shrinkwrap agora é escolhida
    # explicitamente pelo dropper no painel (Scene.retopo_target,
    # ver ui/panel.py).
    #
    # SIMETRIA (caixa "Objeto Espelhado" no painel): com ela
    # ligada, o trabalho cai de 27 cliques pra 18.
    #   - Ponto do meio da face (NoseTip, Chin, lábios...) fica
    #     TRAVADO no plano de simetria -- clicou por cima do
    #     nariz, o ponto cai exatamente no meio.
    #   - Ponto de um lado cria o gêmeo do outro lado na hora, e
    #     os dois seguem o mouse juntos enquanto o usuário move,
    #     então dá pra conferir os dois antes de clicar.
    #   - Quando chega a vez do gêmeo na lista, ele é pulado
    #     (já existe).
    # O plano é o plano LOCAL do objeto alvo, no eixo escolhido
    # no painel -- ver core/fitting/symmetry.py.
    #

    bl_idname = "retopo.create_critical_points"
    bl_label = "Place Critical Points"

    POINT_NAMES = [
        "ForeheadTop",
        "LeftEye_Top",
        "LeftEye_Bottom",
        "LeftEye_Inner_Side",
        "LeftEye_Outer_Side",
        "RightEye_Top",
        "RightEye_Bottom",
        "RightEye_Inner_Side",
        "RightEye_Outer_Side",
        "NoseRoot",
        "NoseTip",
        "Left_Nostril",
        "Right_Nostril",
        "Left_Nose_Inside",
        "Right_Nose_Inside",
        "MouthLeft",
        "MouthRight",
        "UpperLip_Inner_Side",
        "UpperLip_Outer_Side",
        "LowerLip_Inner_Side",
        "LowerLip_Outer_Side",
        "Chin",
        "Neck_Chin_Connection",
        "JawLeft",
        "JawRight",
        "Left_Ear_Anchor",
        "Rigth_Ear_Anchor",
    ]

    index: bpy.props.IntProperty(default=0)

    empty = None

    # -----------------------------------------------------------

    def invoke(self, context, event):

        if context.area.type != 'VIEW_3D':
            self.report({'ERROR'}, "Execute na View 3D")
            return {'CANCELLED'}

        self.symmetric = context.scene.retopo_symmetric
        self.mirror_axis = context.scene.retopo_mirror_axis

        self.target = None
        self.matrix_world = None
        self.matrix_world_inv = None
        self.reproject_limit = 0.0

        if self.symmetric:

            if not self.setup_symmetry(context):
                return {'CANCELLED'}

        session.critical_points.clear()

        #
        # Os Empties do usuário moram numa coleção própria do addon
        # (ver core/scene_collections.py), e não na coleção ativa
        # da cena. Dois motivos:
        #   - dá pra RECONSTRUIR a lista de critical points a
        #     partir da cena quando as referências Python morrem
        #     (Ctrl+Z) -- é o que o Apply Mesh faz agora;
        #   - a limpeza depois do fitting sabe exatamente o que é
        #     do addon e o que é do usuário.
        #
        # Limpar os pontos da rodada anterior é obrigatório: com um
        # "NoseTip" já na cena, o Blender nomeia o novo como
        # "NoseTip.001" e sobram dois Empties disputando o mesmo
        # landmark (os dois normalizam pro mesmo nome).
        #

        self.points_collection = scene_collections.get_user_points(context)

        scene_collections.clear_objects(self.points_collection)

        #
        # O link de simetria fica suspenso enquanto a ferramenta
        # roda: aqui os dois lados já são posicionados juntos, e o
        # gêmeo é reprojetado na malha. Deixar o handler agir em
        # paralelo desfaria essa reprojeção a cada movimento do
        # mouse. Ver core/fitting/symmetry_link.py.
        #

        symmetry_link.suspend()

        self.placed_names = set()
        self.mirror_empty = None

        #
        # history: um item por ponto CONFIRMADO, na ordem em que
        # foram confirmados -- é o que permite voltar um ponto sem
        # sair da ferramenta (Ctrl+Z / Backspace).
        # current_points: o ponto em andamento (e o gêmeo dele),
        # ainda não confirmado.
        #

        self.history = []
        self.current_points = []

        self.index = 0

        self.create_empty(context)
        self.update_empty_position(context, event)

        context.area.header_text_set(self.build_header())

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    # -----------------------------------------------------------

    def setup_symmetry(self, context):

        #
        # O plano de espelhamento é o plano local do objeto alvo,
        # então sem Target escolhido não há como espelhar.
        #

        target = context.scene.retopo_target

        if target is None:

            self.report(
                {'ERROR'},
                "Com 'Objeto Espelhado' ligado, escolha o Target no "
                "painel antes: o plano de espelhamento é o do objeto "
                "alvo."
            )

            return False

        #
        # Se alguém mexer em POINT_NAMES (ou nos nomes dentro do
        # template) sem atualizar as tabelas de symmetry.py, é
        # melhor parar aqui com uma mensagem clara do que espelhar
        # metade dos pontos em silêncio.
        #

        unclassified, missing = validate_point_names(self.POINT_NAMES)

        if unclassified or missing:

            print(
                f"[Symmetry] pontos sem classificação: {unclassified}\n"
                f"[Symmetry] classificados mas ausentes de POINT_NAMES: "
                f"{missing}"
            )

            self.report(
                {'ERROR'},
                "Tabelas de simetria desatualizadas em "
                "core/fitting/symmetry.py. Veja o System Console."
            )

            return False

        self.target = target

        self.matrix_world = target.matrix_world.copy()
        self.matrix_world_inv = target.matrix_world.inverted()

        #
        # Limite de busca da reprojeção: o ponto espelhado deveria
        # cair praticamente em cima da superfície (a assimetria de
        # uma cabeça esculpida à mão é pequena), então um limite
        # generoso mas finito evita que um caso estranho gruda o
        # ponto do outro lado da cabeça.
        #

        size = max(target.dimensions)

        self.reproject_limit = size * 0.1 if size > 0.0 else 0.1

        return True

    # -----------------------------------------------------------

    def build_header(self):

        name = self.POINT_NAMES[self.index]

        total = len(self.POINT_NAMES)

        placed = len(self.placed_names)

        if self.symmetric:

            return (
                f"Landmarking [{placed}/{total}]: {name}  |  "
                f"Simetria: {self.mirror_axis} ({self.target.name})  |  "
                f"Ctrl+Z: voltar um  |  ESC/direito: sair"
            )

        return (
            f"Landmarking [{placed}/{total}]: {name}  |  "
            f"Ctrl+Z: voltar um  |  ESC/direito: sair"
        )

    # -----------------------------------------------------------

    def modal(self, context, event):

        if event.type == 'MOUSEMOVE':
            self.update_empty_position(context, event)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':

            self.confirm_point()

            if not self.advance_index():

                self.report({'INFO'}, "Todos os pontos foram posicionados.")

                return self.finish(context, {'FINISHED'})

            self.create_empty(context)
            self.update_empty_position(context, event)

            context.area.header_text_set(self.build_header())

            return {'RUNNING_MODAL'}

        if event.value == 'PRESS' and (
            event.type == 'BACK_SPACE' or
            (event.type == 'Z' and event.ctrl)
        ):

            self.step_back(context, event)

            context.area.tag_redraw()

            return {'RUNNING_MODAL'}

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            return self.finish(context, {'CANCELLED'})

        return {'RUNNING_MODAL'}

    # -----------------------------------------------------------

    def finish(self, context, result):

        #
        # O ponto em andamento é o que está seguindo o mouse, ainda
        # não confirmado por clique. Saindo com ESC ele não deve
        # ficar largado na cena -- antes ficava, e no Apply Mesh
        # seguinte virava um landmark posicionado em qualquer
        # lugar.
        #

        if result == {'CANCELLED'}:

            self.remove_points(self.current_points)

            self.current_points = []

        symmetry_link.resume()

        if context.area is not None:

            context.area.header_text_set(None)

            context.area.tag_redraw()

        return result

    # -----------------------------------------------------------

    def confirm_point(self):

        #
        # Operator modal não registra passo de undo sozinho. Sem
        # este push, um Ctrl+Z depois do Landmarking voltava pra
        # ANTES dele inteiro: os Empties sumiam da cena e
        # session.critical_points ficava só com referência morta --
        # é essa a origem do erro "Faltam pontos obrigatórios no
        # lado do usuário" no Apply Mesh. Com um push por ponto, o
        # Ctrl+Z desfaz ponto a ponto.
        #

        self.history.append((self.index, list(self.current_points)))

        self.current_points = []

        bpy.ops.ed.undo_push(
            message=f"Landmark: {self.POINT_NAMES[self.index]}"
        )

    # -----------------------------------------------------------

    def step_back(self, context, event):

        #
        # Volta um landmark sem sair da ferramenta.
        #
        # Ctrl+Z "de verdade" não chega aqui: enquanto um operator
        # modal está rodando, o Blender entrega os eventos pra ele
        # e o undo global só valeria depois que a ferramenta
        # fechasse. Então a ferramenta implementa o próprio
        # desfazer, com a mesma tecla que o usuário já espera (e
        # Backspace também).
        #

        if not self.history:

            self.report({'INFO'}, "Nada pra desfazer.")

            return

        self.remove_points(self.current_points)

        previous_index, previous_points = self.history.pop()

        self.remove_points(previous_points)

        self.index = previous_index

        self.create_empty(context)
        self.update_empty_position(context, event)

        context.area.header_text_set(self.build_header())

    # -----------------------------------------------------------

    def remove_points(self, entries):

        #
        # Tira os Empties da cena E das listas. A ordem importa: a
        # lista da sessão é filtrada ANTES da remoção, porque
        # comparar uma referência já removida levanta
        # ReferenceError (ver core/blender_utils.is_valid).
        #

        if not entries:
            return

        empties = [empty for _, empty in entries if is_valid(empty)]

        session.critical_points[:] = [
            point for point in session.critical_points
            if is_valid(point.empty) and point.empty not in empties
        ]

        for name, empty in entries:

            self.placed_names.discard(name)

            if is_valid(empty):

                bpy.data.objects.remove(empty, do_unlink=True)

                continue

            #
            # Referência morreu (cada ponto confirmado empurra um
            # passo de undo, e isso pode invalidar StructRNA
            # guardada antes). Cai pra busca por nome pra não
            # deixar o Empty largado na cena.
            #

            fallback = bpy.data.objects.get(name)

            if fallback is not None:

                bpy.data.objects.remove(fallback, do_unlink=True)

    # -----------------------------------------------------------

    def advance_index(self):

        #
        # Avança pro próximo ponto que ainda não existe. Com a
        # simetria ligada, o gêmeo do outro lado já foi criado
        # junto com o ponto que o usuário clicou, então a vez dele
        # na lista é pulada.
        #

        self.index += 1

        while self.index < len(self.POINT_NAMES):

            if self.POINT_NAMES[self.index] not in self.placed_names:
                return True

            self.index += 1

        return False

    # -----------------------------------------------------------

    def new_empty(self, context, name):

        empty = bpy.data.objects.new(name, None)

        empty.empty_display_type = 'PLAIN_AXES'
        empty.empty_display_size = 0.8
        empty.show_name = True

        self.points_collection.objects.link(empty)

        self.placed_names.add(name)

        self.current_points.append((name, empty))

        session.critical_points.append(
            CriticalPoint(empty)
        )

        return empty

    # -----------------------------------------------------------

    def create_empty(self, context):

        name = self.POINT_NAMES[self.index]

        self.current_points = []

        self.empty = self.new_empty(context, name)

        self.mirror_empty = None

        if not self.symmetric:
            return

        mirror_name = get_mirror_name(name)

        if mirror_name is None:
            return

        if mirror_name in self.placed_names:
            return

        #
        # O gêmeo nasce junto e acompanha o mouse em tempo real --
        # a ideia é o usuário conferir os dois lados ANTES de
        # confirmar o clique.
        #

        self.mirror_empty = self.new_empty(context, mirror_name)

    # -----------------------------------------------------------

    def update_empty_position(self, context, event):

        region = context.region
        rv3d = context.space_data.region_3d

        coord = (event.mouse_region_x, event.mouse_region_y)

        origin = view3d_utils.region_2d_to_origin_3d(
            region,
            rv3d,
            coord
        )

        direction = view3d_utils.region_2d_to_vector_3d(
            region,
            rv3d,
            coord
        )

        depsgraph = context.evaluated_depsgraph_get()

        hit, location, normal, face_index, obj, matrix = context.scene.ray_cast(
            depsgraph,
            origin,
            direction
        )

        if not hit:
            return

        if not self.symmetric:

            self.empty.location = location

            return

        name = self.POINT_NAMES[self.index]

        if is_neutral(name):

            self.empty.location = self.place_neutral(context, location)

            return

        self.empty.location = location

        if self.mirror_empty is not None:

            mirrored = mirror_world_position(
                self.matrix_world,
                self.matrix_world_inv,
                location,
                self.mirror_axis
            )

            self.mirror_empty.location = self.reproject(context, mirrored)

    # -----------------------------------------------------------

    def place_neutral(self, context, world_co):

        #
        # Ponto do meio da face: gruda no plano, reprojeta na
        # malha (senão ele fica um pouco afundado/flutuando --
        # mover lateralmente até o plano não acompanha a
        # curvatura da superfície) e gruda no plano de novo, pra
        # garantir que a reprojeção não jogou ele pra fora do
        # plano numa cabeça só aproximadamente simétrica.
        #

        snapped = snap_world_position(
            self.matrix_world,
            self.matrix_world_inv,
            world_co,
            self.mirror_axis
        )

        reprojected = self.reproject(context, snapped)

        return snap_world_position(
            self.matrix_world,
            self.matrix_world_inv,
            reprojected,
            self.mirror_axis
        )

    # -----------------------------------------------------------

    def reproject(self, context, world_co):

        #
        # Gruda uma posição na superfície do alvo pelo ponto mais
        # próximo (não por ray cast): o ponto espelhado já nasce
        # praticamente em cima da malha, então não existe uma
        # direção de raio óbvia, e o ponto mais próximo não tem
        # como "errar" e passar reto.
        #
        # Se nada for encontrado dentro do limite, devolve a
        # posição original -- melhor um ponto espelhado puro que
        # ponto nenhum.
        #

        depsgraph = context.evaluated_depsgraph_get()

        evaluated = self.target.evaluated_get(depsgraph)

        local = self.to_local(world_co)

        result, location, normal, index = evaluated.closest_point_on_mesh(
            local,
            distance=self.reproject_limit
        )

        if not result:
            return world_co

        return self.to_world(location)

    # -----------------------------------------------------------

    def to_local(self, world_co):

        return transform(self.matrix_world_inv, world_co)

    # -----------------------------------------------------------

    def to_world(self, local_co):

        return transform(self.matrix_world, local_co)
