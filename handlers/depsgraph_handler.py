import bpy

from ..core.anchor import anchors

def anchor_handler(scene):

    for anchor in anchors:
        anchor.update()