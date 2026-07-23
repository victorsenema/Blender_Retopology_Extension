from .critical_point_placement_base import CriticalPointPlacementBase


class OPERATOR_create_critical_points(CriticalPointPlacementBase):

    bl_idname = "retopo.create_critical_points"
    bl_label = "Place Critical Points"

    POINT_NAMES = [
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

    SESSION_LIST = "critical_points"
