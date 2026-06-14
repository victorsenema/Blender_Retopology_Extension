import bpy

class CriticalPoint:
    # The template will have all the critical points
    # Every critical point its only a Empty with a name
    # Critical point will be used in the class Anchor to anchor the empty with a vertex

    def __init__(self, empty_obj):
        self.empty = empty_obj
        self.name = empty_obj.name

    # Get every critical point from the template
    def get_all():
        template_critical_points = []
        for obj in bpy.data.objects:

                if obj.type == 'EMPTY':
                    template_critical_points.append(
                        CriticalPoint(obj)
                    )

        return template_critical_points