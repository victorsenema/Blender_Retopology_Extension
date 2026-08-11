import bpy
from bpy_extras import view3d_utils

from ..core.fitting.critical_points import CriticalPoint
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

    bl_idname = "retopo.create_critical_points"
    bl_label = "Place Critical Points"

    POINT_NAMES = [
        "ForeheadTop",
        "LeftEye_Top",
        "LeftEye_Bottom",
        "LeftEye_Bottom_Inner_Side",
        "LeftEye_Bottom_Outer_Side",
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

        session.critical_points.clear()
        self.index = 0

        self.create_empty(context)
        self.update_empty_position(context, event)

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    # -----------------------------------------------------------

    def modal(self, context, event):

        if event.type == 'MOUSEMOVE':
            self.update_empty_position(context, event)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':

            self.index += 1

            if self.index >= len(self.POINT_NAMES):
                self.report({'INFO'}, "Todos os pontos foram posicionados.")
                return {'FINISHED'}

            self.create_empty(context)
            self.update_empty_position(context, event)

            return {'RUNNING_MODAL'}

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    # -----------------------------------------------------------

    def create_empty(self, context):

        empty = bpy.data.objects.new(
            self.POINT_NAMES[self.index],
            None
        )

        empty.empty_display_type = 'PLAIN_AXES'
        empty.empty_display_size = 0.8
        empty.show_name = True

        context.collection.objects.link(empty)

        self.empty = empty

        session.critical_points.append(
            CriticalPoint(empty)
        )

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

        if hit:
            self.empty.location = location
