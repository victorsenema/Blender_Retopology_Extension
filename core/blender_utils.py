def is_valid(obj):

    #
    # Referências Python pra objetos do Blender (bpy.types.Object,
    # etc.) podem ficar "mortas" sem aviso -- o gatilho mais comum
    # é um Ctrl+Z (undo), que troca o estado interno inteiro do
    # Blender e invalida qualquer referência guardada antes dele
    # (ex.: em core/session.py, que é um módulo global mantido
    # entre cliques de operator diferentes). Tentar acessar
    # qualquer atributo de uma referência morta levanta
    # ReferenceError: "StructRNA of type X has been removed".
    #
    # Esta função checa isso de forma segura, sem derrubar quem
    # chamou.
    #

    if obj is None:
        return False

    try:
        obj.name
        return True

    except ReferenceError:
        return False
