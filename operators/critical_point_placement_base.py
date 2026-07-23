import bpy
from bpy_extras import view3d_utils
from ..core.fitting.critical_points import CriticalPoint
from ..core import session


class CriticalPointPlacementBase(bpy.types.Operator):

    #
    # Lógica compartilhada de posicionamento de pontos via modal
    # + ray cast, usada tanto pelos Structure Critical Points
    # quanto pelos Refinement Critical Points. Subclasses
    # concretas definem:
    #
    #   POINT_NAMES  -> lista de nomes, na ordem de posicionamento
    #   SESSION_LIST -> nome do atributo em core/session.py onde
    #                    os pontos posicionados são guardados
    #
    # Esta classe base NÃO é registrada no Blender (não tem
    # bl_idname); só as subclasses concretas são.
    #

    POINT_NAMES = []

    SESSION_LIST = "critical_points"

    index: bpy.props.IntProperty(default=0)

    empty = None

    def get_session_list(self):

        return getattr(session, self.SESSION_LIST)

    def invoke(self, context, event):

        if context.area.type != 'VIEW_3D':
            self.report({'ERROR'}, "Execute na View 3D")
            return {'CANCELLED'}

        if not self.POINT_NAMES:
            self.report({'ERROR'}, "Nenhum ponto configurado.")
            return {'CANCELLED'}

        self.get_session_list().clear()
        self.index = 0

        self.create_empty(context)
        self.update_empty_position(context, event)

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

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

        critical_point = CriticalPoint(empty)

        self.get_session_list().append(critical_point)

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

            if obj is not None:
                session.target_mesh = obj
