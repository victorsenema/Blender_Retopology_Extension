def normalize_point_name(name):

    #
    # Tira o prefixo usado nos objetos da Template
    # ("CriticalPoint_") e qualquer sufixo ".001"/".002" que o
    # Blender adiciona quando dois objetos colidem de nome --
    # assim o nome bate com o Empty equivalente criado pelo
    # usuário no Landmarking, não importa de qual lado (template
    # ou usuário) ele vem.
    #
    # Usado em alignment.py (pra casar template x usuário na
    # hora de calcular escala/rotação) e em structure_warp.py
    # (pra casar template x usuário na hora do warp TPS).
    #

    name = name.replace("CriticalPoint_", "")

    if "." in name:
        name = name.split(".")[0]

    return name


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
