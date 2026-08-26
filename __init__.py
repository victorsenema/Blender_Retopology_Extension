import bpy

from .operators.OPERATOR_create_critical_points import OPERATOR_create_critical_points
from .operators.OPERATOR_test_inside_nose_and_nostrils import OPERATOR_test_inside_nose_and_nostrils
from .operators.OPERATOR_add_subdivision import OPERATOR_add_subdivision
from .operators.OPERATOR_relax_mesh import OPERATOR_relax_mesh
from .operators.OPERATOR_apply_modifiers import OPERATOR_apply_modifiers
from .operators.OPERATOR_nudge_vertex import OPERATOR_nudge_vertex
from .operators.OPERATOR_reset_scene import OPERATOR_reset_scene

from .core.fitting import symmetry_link
from .ui.panel import RETOPOLOGY_PT_panel
from .ui import vertex_highlight


bl_info = {
    "name": "Retopology",
    "author": "Victor Gava",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Retopology",
    "description": "Semi-automatic facial retopology.",
    "category": "Mesh",
}


classes = (
    OPERATOR_create_critical_points,
    OPERATOR_test_inside_nose_and_nostrils,
    OPERATOR_add_subdivision,
    OPERATOR_relax_mesh,
    OPERATOR_apply_modifiers,
    OPERATOR_nudge_vertex,
    OPERATOR_reset_scene,
    RETOPOLOGY_PT_panel,
)


def register():

    for cls in classes:
        bpy.utils.register_class(cls)

    #
    # Scene.retopo_target: dropper (PointerProperty nativo do
    # Blender, com o ícone de conta-gotas) pra escolher a malha
    # esculpida onde o template vai ser colado via Shrinkwrap.
    # Ver operators/OPERATOR_test_inside_nose_and_nostrils.py.
    #

    bpy.types.Scene.retopo_target = bpy.props.PointerProperty(
        name="Target Mesh",
        description=(
            "Malha esculpida onde o template será colado (Shrinkwrap)"
        ),
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH',
    )

    #
    # Simetria do Landmarking (ver core/fitting/symmetry.py e
    # operators/OPERATOR_create_critical_points.py). O plano de
    # espelhamento é o plano LOCAL do objeto alvo, no eixo
    # escolhido aqui -- a mesma referência que o sculpt simétrico
    # e o modifier Mirror do Blender usam.
    #

    bpy.types.Scene.retopo_symmetric = bpy.props.BoolProperty(
        name="Objeto Espelhado",
        description=(
            "A cabeça alvo é simétrica. Clique só um lado: o ponto "
            "do outro lado é criado junto, e os pontos do meio da "
            "face ficam travados no plano de simetria"
        ),
        default=False,
    )

    bpy.types.Scene.retopo_mirror_axis = bpy.props.EnumProperty(
        name="Mirror Axis",
        description=(
            "Eixo local do objeto alvo em que o rosto é espelhado"
        ),
        items=[
            (
                'X',
                "X",
                "Espelha em torno do plano local X=0 do objeto alvo",
            ),
            (
                'Y',
                "Y",
                "Espelha em torno do plano local Y=0 do objeto alvo",
            ),
        ],
        default='X',
    )

    #
    # Ajustes do Nudge Vertex (ver
    # operators/OPERATOR_nudge_vertex.py). Ficam na Scene, e não
    # como properties do operator, porque precisam aparecer no
    # painel e sobreviver entre uma execução e outra da
    # ferramenta modal.
    #

    bpy.types.Scene.retopo_nudge_radius = bpy.props.FloatProperty(
        name="Influence Radius",
        description=(
            "Raio de influência do Nudge Vertex, medido ao longo da "
            "superfície da malha. 0 = automático (8% do tamanho da "
            "cabeça). A roda do mouse ajusta durante o arraste"
        ),
        default=0.0,
        min=0.0,
        soft_max=1.0,
        subtype='DISTANCE',
    )

    bpy.types.Scene.retopo_nudge_affect_control = bpy.props.BoolProperty(
        name="Affect Control Points",
        description=(
            "Deixa um ponto de controle arrastar os outros pontos de "
            "controle vizinhos junto, como o Proportional Editing "
            "nativo. Desligado, só a malha livre em volta reage"
        ),
        default=False,
    )

    vertex_highlight.register()

    #
    # Link de simetria: mantém os pares esquerda/direita dos
    # critical points grudados um no outro DEPOIS que o
    # Landmarking termina (mover JawLeft move JawRight), e os
    # pontos do meio da face presos no plano. Ver
    # core/fitting/symmetry_link.py.
    #

    symmetry_link.register()


def unregister():

    symmetry_link.unregister()

    vertex_highlight.unregister()

    del bpy.types.Scene.retopo_nudge_affect_control
    del bpy.types.Scene.retopo_nudge_radius
    del bpy.types.Scene.retopo_mirror_axis
    del bpy.types.Scene.retopo_symmetric
    del bpy.types.Scene.retopo_target

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
