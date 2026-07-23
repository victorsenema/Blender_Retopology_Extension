from .critical_point_placement_base import CriticalPointPlacementBase


class OPERATOR_create_refinement_points(CriticalPointPlacementBase):

    bl_idname = "retopo.create_refinement_points"
    bl_label = "Place Refinement Points"

    #
    # Nomes extraídos das coleções Refinement_Critical_Points_*
    # do Refined_Template.blend. OBS.: "Botton" (em vez de
    # "Bottom") está assim no arquivo original nos 4 pontos de
    # lábio -- mantido igual de propósito, pra bater exatamente
    # com os nomes usados em targets.py (que casa por nome).
    #

    POINT_NAMES = [
        "LeftEye_Top",
        "LeftEye_Bottom",
        "LeftEye_Inner_Side",
        "LeftEye_Outer_Side",
        "RightEye_Top",
        "RightEye_Bottom",
        "RightEye_Inner_Side",
        "RightEye_Outer_Side",
        "Left_Nose_Wing",
        "Right_Nose_Wing",
        "Left_Nose_InnerNostril",
        "Right_Nose_InnerNostril",
        "Nose_Middle",
        "Left_Temple",
        "Right_Temple",
        "Left_Submandibular",
        "Right_Submandibular",
        "Upper_Lip_Top",
        "Upper_Lip_Botton",
        "Lower_Lip_Top",
        "Lower_Lip_Botton",
        "Neck_Chin_Connection",
    ]

    SESSION_LIST = "refinement_points"
