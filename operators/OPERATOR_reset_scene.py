import bpy

from ..core import scene_collections
from ..core import session
from ..ui import vertex_highlight


class OPERATOR_reset_scene(bpy.types.Operator):

    #
    # Limpeza explícita de tudo que o addon deixou na cena: os
    # critical points e as coleções importadas do template, todas
    # debaixo da raiz "Retopology" (ver core/scene_collections.py).
    #
    # POR QUE É UM BOTÃO, E NÃO AUTOMÁTICO:
    #
    #   (1) Segurança do arquivo. Remover coleção obriga o Blender
    #       a reconstruir as relações de parentesco; fazer isso
    #       dentro do pipeline, cercado de passos de undo, é um
    #       dos suspeitos do crash em
    #       collection_parents_rebuild_recursive que apareceu ao
    #       apertar Ctrl+Z. Aqui a limpeza acontece sozinha, num
    #       operator próprio, longe de qualquer modal.
    #
    #   (2) O resultado mora aqui dentro. A malha retopologizada
    #       é a Template_Mesh -- apagar automaticamente o que
    #       sobrou de uma rodada anterior significaria apagar o
    #       trabalho de alguém sem perguntar. Com botão +
    #       confirmação, a decisão é do usuário.
    #
    # Pra PRESERVAR uma cabeça já finalizada, arraste ela pra fora
    # da coleção "Retopology" na Outliner antes de resetar. E como
    # o operator é REGISTER/UNDO, um Ctrl+Z traz tudo de volta.
    #

    bl_idname = "retopo.reset_scene"
    bl_label = "Remove all Retopology objects?"
    bl_description = (
        "Removes the critical points and the template mesh from the "
        "scene (everything inside the 'Retopology' collection). Use "
        "it before running the addon again in the same file. To keep "
        "a finished head, move it out of that collection first"
    )

    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):

        #
        # Ação destrutiva -- sempre pergunta antes.
        #

        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):

        root = scene_collections.get_root(context, create=False)

        if root is None:

            self.report(
                {'INFO'},
                "Nada pra limpar: a coleção 'Retopology' não existe."
            )

            return {'CANCELLED'}

        removed = scene_collections.remove_collection(
            root,
            with_objects=True
        )

        #
        # O estado em memória tem que morrer junto, senão sobra
        # referência apontando pra objeto que não existe mais.
        #

        session.reset()

        vertex_highlight.mark_dirty()
        vertex_highlight.mark_groups_dirty()

        self.report(
            {'INFO'},
            f"{removed} objeto(s) removido(s). Cena limpa pra uma nova "
            f"rodada."
        )

        return {'FINISHED'}
