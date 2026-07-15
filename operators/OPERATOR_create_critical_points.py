import bpy
from bpy_extras import view3d_utils
from ..core.fitting.critical_points import CriticalPoint
from ..core import session

CRITICAL_POINTS = [
    "LeftEye",
    "RightEye",
    "NoseRoot",
    "NoseTip",
    "MouthLeft",
    "MouthRight",
    "UpperLip",
    "LowerLip",
    "Chin",
    "ForeheadTop",
    "JawLeft",
    "JawRight",
]


class OPERATOR_create_critical_points(bpy.types.Operator):
    bl_idname = "retopo.create_critical_points"
    bl_label = "Place Critical Points"

    index: bpy.props.IntProperty(default=0)

    empty = None

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

    def modal(self, context, event):

        if event.type == 'MOUSEMOVE':
            self.update_empty_position(context, event)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':

            self.index += 1

            if self.index >= len(CRITICAL_POINTS):
                self.report({'INFO'}, "Todos os Critical Points foram posicionados.")
                return {'FINISHED'}

            self.create_empty(context)
            self.update_empty_position(context, event)

            return {'RUNNING_MODAL'}

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def create_empty(self, context):

        empty = bpy.data.objects.new(CRITICAL_POINTS[self.index], None)

        empty.empty_display_type = 'PLAIN_AXES'
        empty.empty_display_size = 0.8
        empty.show_name = True

        context.collection.objects.link(empty)

        self.empty = empty

        critical_point = CriticalPoint(empty)

        session.critical_points.append(critical_point)

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


def register():
    bpy.utils.register_class(OPERATOR_place_critical_points)


def unregister():
    bpy.utils.unregister_class(OPERATOR_place_critical_points)


if __name__ == "__main__":
    register()